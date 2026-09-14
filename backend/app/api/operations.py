import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, current_user, require_roles
from app.core.storage import storage
from app.models.entities import (
    DecisionCard,
    DecisionStatus,
    Event,
    EventCompletionRecord,
    EventParticipant,
    EventRunItem,
    HandoverGuide,
    MapAssignment,
    MeetingRecord,
    Role,
    SchoolMap,
    StoredFile,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    Term,
    User,
)
from app.schemas import (
    DecisionCardIn,
    DecisionCardOut,
    DecisionCardStatusIn,
    EventCompletionRecordIn,
    EventCompletionRecordOut,
    EventRunItemIn,
    EventRunItemOut,
    EventRunItemStatusIn,
    EventRunItemsReorderIn,
    HandoverGuideIn,
    HandoverGuideOut,
    MapAssignmentIn,
    MapAssignmentOut,
    MapAssignmentPositionIn,
    SchoolMapOut,
)
from app.services.notifications import create_notifications

router = APIRouter(prefix="/operations", tags=["operations"], dependencies=[Depends(csrf_protect)])
manager = require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


def can_manage_event(user: User, event: Event) -> bool:
    return user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER} or (
        user.role == Role.DEPARTMENT_HEAD and event.department_id == user.department_id
    )


async def event_for_manager(db: AsyncSession, event_id: uuid.UUID, user: User) -> Event:
    event = await db.get(Event, event_id)
    if not event or event.term_id != user.term_id or not can_manage_event(user, event):
        raise AppError(403, "event_scope", "이 행사를 관리할 권한이 없습니다.")
    return event


async def event_visible(db: AsyncSession, event: Event, user: User) -> bool:
    if event.term_id != user.term_id:
        return False
    if can_manage_event(user, event):
        return True
    return bool(
        await db.scalar(
            select(EventParticipant.id).where(
                EventParticipant.event_id == event.id, EventParticipant.user_id == user.id
            )
        )
    )


async def decision_out(db: AsyncSession, item: DecisionCard, user: User) -> DecisionCardOut:
    owner_name = await db.scalar(select(User.name).where(User.id == item.owner_id)) or "알 수 없음"
    return DecisionCardOut.model_validate(item).model_copy(
        update={
            "owner_name": owner_name,
            "can_manage": user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER}
            or item.created_by == user.id,
        }
    )


@router.get("/decisions", response_model=list[DecisionCardOut])
async def list_decisions(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    statement = select(DecisionCard).where(DecisionCard.term_id == user.term_id)
    if user.role == Role.MEMBER:
        statement = statement.where(DecisionCard.owner_id == user.id)
    elif user.role == Role.DEPARTMENT_HEAD:
        department_users = select(User.id).where(
            User.term_id == user.term_id, User.department_id == user.department_id
        )
        statement = statement.where(
            or_(DecisionCard.owner_id.in_(department_users), DecisionCard.created_by == user.id)
        )
    cards = list((await db.scalars(statement.order_by(DecisionCard.created_at.desc()))).all())
    return [await decision_out(db, card, user) for card in cards]


@router.post("/decisions", response_model=DecisionCardOut, status_code=201)
async def create_decision(
    data: DecisionCardIn, actor: User = Depends(manager), db: AsyncSession = Depends(get_db)
):
    owner = await db.get(User, data.owner_id)
    if not owner or owner.term_id != actor.term_id or not owner.is_active:
        raise AppError(422, "invalid_owner", "현재 기수의 활성 담당자를 선택해 주세요.")
    if actor.role == Role.DEPARTMENT_HEAD and owner.department_id != actor.department_id:
        raise AppError(403, "owner_scope", "자신의 부서 구성원만 담당자로 지정할 수 있습니다.")
    if data.event_id:
        await event_for_manager(db, data.event_id, actor)
    if data.meeting_record_id:
        meeting = await db.get(MeetingRecord, data.meeting_record_id)
        if not meeting or meeting.term_id != actor.term_id:
            raise AppError(422, "invalid_meeting", "현재 기수의 회의록을 선택해 주세요.")
    task = None
    if data.create_task:
        task = Task(
            term_id=actor.term_id,
            event_id=data.event_id,
            title=data.title,
            description=data.detail,
            type=TaskType.SIMPLE,
            status=TaskStatus.TODO,
            due_at=data.due_at,
            created_by=actor.id,
        )
        db.add(task)
        await db.flush()
        db.add(TaskAssignee(task_id=task.id, user_id=owner.id))
    card = DecisionCard(
        **data.model_dump(exclude={"create_task"}),
        term_id=actor.term_id,
        task_id=task.id if task else None,
        created_by=actor.id,
        status=DecisionStatus.OPEN,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    if owner.id != actor.id:
        await create_notifications(
            db,
            {owner.id},
            notification_type="DECISION_ASSIGNED",
            title="회의 결정사항이 배정되었습니다",
            content=card.title,
            target_type="task" if task else "decision",
            target_id=task.id if task else card.id,
        )
    return await decision_out(db, card, actor)


@router.patch("/decisions/{decision_id}/status", response_model=DecisionCardOut)
async def update_decision_status(
    decision_id: uuid.UUID,
    data: DecisionCardStatusIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    card = await db.get(DecisionCard, decision_id)
    if not card or card.term_id != user.term_id:
        raise AppError(404, "decision_not_found", "결정 카드를 찾을 수 없습니다.")
    can_update = card.owner_id == user.id or card.created_by == user.id or user.role in {
        Role.EXECUTIVE_BOARD,
        Role.TEACHER,
    }
    if not can_update:
        raise AppError(403, "decision_forbidden", "이 결정 상태를 변경할 권한이 없습니다.")
    card.status = data.status
    card.completed_at = datetime.now(UTC) if data.status == DecisionStatus.DONE else None
    task = await db.get(Task, card.task_id) if card.task_id else None
    if task:
        task.status = (
            TaskStatus.DONE
            if data.status == DecisionStatus.DONE
            else TaskStatus.REJECTED
            if data.status == DecisionStatus.CANCELLED
            else TaskStatus.TODO
        )
    await db.commit()
    return await decision_out(db, card, user)


async def handover_out(db: AsyncSession, guide: HandoverGuide, user: User) -> HandoverGuideOut:
    term_name = await db.scalar(select(Term.name).where(Term.id == guide.term_id)) or "이전 기수"
    return HandoverGuideOut.model_validate(guide).model_copy(
        update={
            "term_name": term_name,
            "can_manage": guide.term_id == user.term_id
            and (guide.created_by == user.id or user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER}),
        }
    )


@router.get("/handovers", response_model=list[HandoverGuideOut])
async def list_handovers(
    term_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    can_view_drafts = user.role in {Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER}
    statement = select(HandoverGuide)
    if term_id:
        statement = statement.where(HandoverGuide.term_id == term_id)
    if can_view_drafts:
        statement = statement.where(
            or_(HandoverGuide.published_at.is_not(None), HandoverGuide.term_id == user.term_id)
        )
    else:
        statement = statement.where(HandoverGuide.published_at.is_not(None))
    guides = list((await db.scalars(statement.order_by(HandoverGuide.created_at.desc()))).all())
    return [await handover_out(db, guide, user) for guide in guides]


@router.post("/handovers", response_model=HandoverGuideOut, status_code=201)
async def create_handover(
    data: HandoverGuideIn, actor: User = Depends(manager), db: AsyncSession = Depends(get_db)
):
    if data.event_id:
        await event_for_manager(db, data.event_id, actor)
    guide = HandoverGuide(
        **data.model_dump(exclude={"publish"}),
        term_id=actor.term_id,
        created_by=actor.id,
        published_at=datetime.now(UTC) if data.publish else None,
    )
    db.add(guide)
    await db.commit()
    await db.refresh(guide)
    return await handover_out(db, guide, actor)


@router.post("/handovers/{guide_id}/publish", response_model=HandoverGuideOut)
async def publish_handover(
    guide_id: uuid.UUID, actor: User = Depends(manager), db: AsyncSession = Depends(get_db)
):
    guide = await db.get(HandoverGuide, guide_id)
    if not guide or guide.term_id != actor.term_id:
        raise AppError(404, "handover_not_found", "인수인계 문서를 찾을 수 없습니다.")
    if actor.role == Role.DEPARTMENT_HEAD and guide.created_by != actor.id:
        raise AppError(403, "handover_forbidden", "직접 작성한 문서만 공개할 수 있습니다.")
    guide.published_at = datetime.now(UTC)
    await db.commit()
    return await handover_out(db, guide, actor)


async def run_item_out(db: AsyncSession, item: EventRunItem, user: User) -> EventRunItemOut:
    assignee_name = (
        await db.scalar(select(User.name).where(User.id == item.assignee_id))
        if item.assignee_id
        else None
    )
    event = await db.get(Event, item.event_id)
    return EventRunItemOut.model_validate(item).model_copy(
        update={"assignee_name": assignee_name, "can_manage": bool(event and can_manage_event(user, event))}
    )


@router.get("/events/{event_id}/run-items", response_model=list[EventRunItemOut])
async def list_run_items(
    event_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    event = await db.get(Event, event_id)
    if not event or not await event_visible(db, event, user):
        raise AppError(404, "event_not_found", "행사를 찾을 수 없습니다.")
    items = list(
        (
            await db.scalars(
                select(EventRunItem)
                .where(EventRunItem.event_id == event_id)
                .order_by(EventRunItem.sequence, EventRunItem.planned_at)
            )
        ).all()
    )
    return [await run_item_out(db, item, user) for item in items]


@router.post("/events/{event_id}/run-items", response_model=EventRunItemOut, status_code=201)
async def create_run_item(
    event_id: uuid.UUID,
    data: EventRunItemIn,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    await event_for_manager(db, event_id, actor)
    if data.assignee_id:
        assignee = await db.get(User, data.assignee_id)
        if not assignee or assignee.term_id != actor.term_id or not assignee.is_active:
            raise AppError(422, "invalid_assignee", "현재 기수의 활성 담당자를 선택해 주세요.")
    values = data.model_dump(exclude={"sequence"})
    next_sequence = (
        await db.scalar(
            select(func.max(EventRunItem.sequence)).where(EventRunItem.event_id == event_id)
        )
        or 0
    ) + 1
    item = EventRunItem(
        **values,
        sequence=data.sequence if data.sequence > 0 else next_sequence,
        event_id=event_id,
        created_by=actor.id,
        updated_by=actor.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    if item.assignee_id and item.assignee_id != actor.id:
        await create_notifications(
            db,
            {item.assignee_id},
            notification_type="EVENT_RUN_ASSIGNED",
            title="행사 당일 역할이 배정되었습니다",
            content=item.title,
            target_type="event",
            target_id=event_id,
        )
    return await run_item_out(db, item, actor)


@router.patch("/run-items/{item_id}/status", response_model=EventRunItemOut)
async def update_run_item_status(
    item_id: uuid.UUID,
    data: EventRunItemStatusIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(EventRunItem, item_id)
    event = item and await db.get(Event, item.event_id)
    if not item or not event or event.term_id != user.term_id:
        raise AppError(404, "run_item_not_found", "운영 항목을 찾을 수 없습니다.")
    if item.assignee_id != user.id and not can_manage_event(user, event):
        raise AppError(403, "run_item_forbidden", "이 운영 항목을 변경할 권한이 없습니다.")
    item.status = data.status
    if data.note is not None:
        item.note = data.note
    item.updated_by = user.id
    await db.commit()
    return await run_item_out(db, item, user)


@router.put("/events/{event_id}/run-items/reorder", response_model=list[EventRunItemOut])
async def reorder_run_items(
    event_id: uuid.UUID,
    data: EventRunItemsReorderIn,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    await event_for_manager(db, event_id, actor)
    items = list(
        (
            await db.scalars(
                select(EventRunItem).where(EventRunItem.event_id == event_id)
            )
        ).all()
    )
    existing = {item.id: item for item in items}
    if len(data.item_ids) != len(set(data.item_ids)) or set(data.item_ids) != set(existing):
        raise AppError(
            422,
            "invalid_run_item_order",
            "현재 행사의 모든 운영 항목을 중복 없이 포함해야 합니다.",
        )
    for sequence, item_id in enumerate(data.item_ids, start=1):
        existing[item_id].sequence = sequence
        existing[item_id].updated_by = actor.id
    await db.commit()
    ordered = [existing[item_id] for item_id in data.item_ids]
    return [await run_item_out(db, item, actor) for item in ordered]


async def completion_out(
    db: AsyncSession, record: EventCompletionRecord, user: User
) -> EventCompletionRecordOut:
    event = await db.get(Event, record.event_id)
    return EventCompletionRecordOut.model_validate(record).model_copy(
        update={
            "event_title": event.title if event else "삭제된 행사",
            "can_manage": bool(event and can_manage_event(user, event)),
        }
    )


@router.get("/completion-records", response_model=list[EventCompletionRecordOut])
async def list_completion_records(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    event_ids = select(Event.id).where(Event.term_id == user.term_id)
    if user.role == Role.MEMBER:
        event_ids = event_ids.where(
            Event.id.in_(
                select(EventParticipant.event_id).where(
                    EventParticipant.user_id == user.id
                )
            )
        )
    elif user.role == Role.DEPARTMENT_HEAD:
        event_ids = event_ids.where(Event.department_id == user.department_id)
    records = list(
        (
            await db.scalars(
                select(EventCompletionRecord)
                .where(EventCompletionRecord.event_id.in_(event_ids))
                .order_by(EventCompletionRecord.completed_at.desc())
            )
        ).all()
    )
    return [await completion_out(db, record, user) for record in records]


@router.get(
    "/events/{event_id}/completion", response_model=EventCompletionRecordOut
)
async def get_event_completion(
    event_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if not event or not await event_visible(db, event, user):
        raise AppError(404, "event_not_found", "행사를 찾을 수 없습니다.")
    record = await db.scalar(
        select(EventCompletionRecord).where(EventCompletionRecord.event_id == event_id)
    )
    if not record:
        raise AppError(404, "completion_not_found", "완료 기록이 아직 없습니다.")
    return await completion_out(db, record, user)


@router.put(
    "/events/{event_id}/completion", response_model=EventCompletionRecordOut
)
async def save_event_completion(
    event_id: uuid.UUID,
    data: EventCompletionRecordIn,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    event = await event_for_manager(db, event_id, actor)
    record = await db.scalar(
        select(EventCompletionRecord).where(EventCompletionRecord.event_id == event_id)
    )
    values = data.model_dump(exclude={"create_handover_draft"})
    if record:
        for key, value in values.items():
            setattr(record, key, value)
    else:
        record = EventCompletionRecord(
            **values, event_id=event_id, created_by=actor.id
        )
        db.add(record)
        await db.flush()

    if data.create_handover_draft:
        guide = (
            await db.get(HandoverGuide, record.handover_guide_id)
            if record.handover_guide_id
            else None
        )
        if not guide:
            guide = HandoverGuide(
                term_id=actor.term_id,
                event_id=event.id,
                title=f"{event.title} 인수인계",
                summary=data.summary,
                what_worked=data.outcomes,
                pitfalls=data.incidents,
                checklist=data.recommendations,
                created_by=actor.id,
            )
            db.add(guide)
            await db.flush()
            record.handover_guide_id = guide.id
        elif guide.published_at is None:
            guide.summary = data.summary
            guide.what_worked = data.outcomes
            guide.pitfalls = data.incidents
            guide.checklist = data.recommendations

    event.status = "COMPLETED"
    await db.commit()
    await db.refresh(record)
    return await completion_out(db, record, actor)


async def school_map_out(item: SchoolMap, user: User, event: Event | None) -> SchoolMapOut:
    return SchoolMapOut.model_validate(item).model_copy(
        update={
            "image_url": f"/api/v1/operations/maps/{item.id}/image",
            "can_manage": bool(event and can_manage_event(user, event))
            or (event is None and user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER}),
        }
    )


@router.get("/maps", response_model=list[SchoolMapOut])
async def list_maps(
    event_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    statement = select(SchoolMap).where(SchoolMap.term_id == user.term_id)
    if event_id:
        statement = statement.where(SchoolMap.event_id == event_id)
    if user.role == Role.MEMBER:
        statement = statement.where(
            SchoolMap.id.in_(
                select(MapAssignment.map_id).where(MapAssignment.user_id == user.id)
            )
        )
    maps = list(
        (
            await db.scalars(
                statement.order_by(
                    SchoolMap.event_id, SchoolMap.floor_order, SchoolMap.created_at
                )
            )
        ).all()
    )
    output = []
    for item in maps:
        event = await db.get(Event, item.event_id) if item.event_id else None
        output.append(await school_map_out(item, user, event))
    return output


@router.post("/maps", response_model=SchoolMapOut, status_code=201)
async def upload_map(
    title: str = Form(..., min_length=1, max_length=200),
    floor_label: str = Form("1층", min_length=1, max_length=80),
    floor_order: int = Form(0, ge=0),
    event_id: uuid.UUID = Form(...),
    upload: UploadFile = File(...),
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    event = await event_for_manager(db, event_id, actor)
    if upload.content_type not in IMAGE_TYPES:
        raise AppError(422, "invalid_map_image", "PNG, JPG 또는 WEBP 지도 이미지만 업로드할 수 있습니다.")
    key, size = await storage.save(upload)
    stored = StoredFile(
        original_name=upload.filename or "school-map",
        storage_key=key,
        mime_type=upload.content_type,
        size=size,
        uploaded_by=actor.id,
    )
    db.add(stored)
    await db.flush()
    item = SchoolMap(
        term_id=actor.term_id,
        event_id=event_id,
        title=title,
        floor_label=floor_label,
        floor_order=floor_order,
        file_id=stored.id,
        created_by=actor.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return await school_map_out(item, actor, event)


async def map_access(db: AsyncSession, map_id: uuid.UUID, user: User) -> tuple[SchoolMap, Event | None, bool]:
    item = await db.get(SchoolMap, map_id)
    if not item or item.term_id != user.term_id:
        raise AppError(404, "map_not_found", "학교 지도를 찾을 수 없습니다.")
    event = await db.get(Event, item.event_id) if item.event_id else None
    manage = bool(event and can_manage_event(user, event)) or (
        event is None and user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER}
    )
    assigned = await db.scalar(
        select(MapAssignment.id).where(
            MapAssignment.map_id == item.id, MapAssignment.user_id == user.id
        )
    )
    if not manage and not assigned:
        raise AppError(404, "map_not_found", "학교 지도를 찾을 수 없습니다.")
    return item, event, manage


@router.get("/maps/{map_id}/image")
async def map_image(
    map_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    item, _, _ = await map_access(db, map_id, user)
    stored = await db.get(StoredFile, item.file_id)
    if not stored:
        raise AppError(404, "map_image_not_found", "지도 이미지를 찾을 수 없습니다.")
    return FileResponse(storage.path(stored.storage_key), media_type=stored.mime_type)


async def assignment_out(
    db: AsyncSession, assignment: MapAssignment, user: User, manage: bool
) -> MapAssignmentOut:
    user_name = await db.scalar(select(User.name).where(User.id == assignment.user_id)) or "알 수 없음"
    return MapAssignmentOut.model_validate(assignment).model_copy(
        update={"user_name": user_name, "can_manage": manage}
    )


@router.get("/maps/{map_id}/assignments", response_model=list[MapAssignmentOut])
async def list_map_assignments(
    map_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    _, _, manage = await map_access(db, map_id, user)
    statement = select(MapAssignment).where(MapAssignment.map_id == map_id)
    if not manage:
        statement = statement.where(MapAssignment.user_id == user.id)
    assignments = list((await db.scalars(statement.order_by(MapAssignment.starts_at))).all())
    return [await assignment_out(db, item, user, manage) for item in assignments]


@router.post("/maps/{map_id}/assignments", response_model=MapAssignmentOut, status_code=201)
async def create_map_assignment(
    map_id: uuid.UUID,
    data: MapAssignmentIn,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    _, event, manage = await map_access(db, map_id, actor)
    if not manage:
        raise AppError(403, "map_forbidden", "지도 위치를 배정할 권한이 없습니다.")
    assignee = await db.get(User, data.user_id)
    if not assignee or assignee.term_id != actor.term_id or not assignee.is_active:
        raise AppError(422, "invalid_assignee", "현재 기수의 활성 학생을 선택해 주세요.")
    if data.ends_at and data.starts_at and data.ends_at < data.starts_at:
        raise AppError(422, "invalid_assignment_period", "종료 시간은 시작 시간 이후여야 합니다.")
    assignment = MapAssignment(**data.model_dump(), map_id=map_id, created_by=actor.id)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    if assignee.id != actor.id:
        await create_notifications(
            db,
            {assignee.id},
            notification_type="MAP_ASSIGNMENT_CREATED",
            title="행사 활동 위치가 배정되었습니다",
            content=f"{assignment.label} · {assignment.activity}",
            target_type="event" if event else "map",
            target_id=event.id if event else map_id,
        )
    return await assignment_out(db, assignment, actor, True)


@router.patch(
    "/map-assignments/{assignment_id}/position", response_model=MapAssignmentOut
)
async def update_map_assignment_position(
    assignment_id: uuid.UUID,
    data: MapAssignmentPositionIn,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    assignment = await db.get(MapAssignment, assignment_id)
    if not assignment:
        raise AppError(404, "assignment_not_found", "위치 배정을 찾을 수 없습니다.")
    _, _, manage = await map_access(db, assignment.map_id, actor)
    if not manage:
        raise AppError(403, "map_forbidden", "지도 위치를 수정할 권한이 없습니다.")
    assignment.x_ratio = data.x_ratio
    assignment.y_ratio = data.y_ratio
    await db.commit()
    return await assignment_out(db, assignment, actor, True)


@router.delete("/map-assignments/{assignment_id}", status_code=204)
async def delete_map_assignment(
    assignment_id: uuid.UUID,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    assignment = await db.get(MapAssignment, assignment_id)
    if not assignment:
        raise AppError(404, "assignment_not_found", "위치 배정을 찾을 수 없습니다.")
    _, _, manage = await map_access(db, assignment.map_id, actor)
    if not manage:
        raise AppError(403, "map_forbidden", "지도 위치를 삭제할 권한이 없습니다.")
    await db.delete(assignment)
    await db.commit()
