import uuid
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, current_user, require_roles
from app.models.entities import (
    Event,
    EventParticipant,
    Role,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    User,
)
from app.schemas import (
    EventIn,
    EventOut,
    EventUpdate,
    TeacherEventCreateIn,
    TeacherEventCreateOut,
)
from app.services.notifications import create_notifications
from app.services.team_formation_draft import build_team_formation_draft

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(csrf_protect)])
manager = require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)


def can_manage(user: User, event: Event | None = None) -> bool:
    if user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER}:
        return True
    return user.role == Role.DEPARTMENT_HEAD and (
        event is None or event.department_id == user.department_id
    )


async def event_out(db: AsyncSession, event: Event, user: User) -> EventOut:
    participant_ids = list(
        (
            await db.scalars(
                select(EventParticipant.user_id).where(EventParticipant.event_id == event.id)
            )
        ).all()
    )
    return EventOut.model_validate(event).model_copy(
        update={"participant_ids": participant_ids, "can_manage": can_manage(user, event)}
    )


@router.get("", response_model=list[EventOut])
async def list_events(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    participant = select(EventParticipant.event_id).where(EventParticipant.user_id == user.id)
    stmt = select(Event).where(Event.term_id == user.term_id, Event.status != "DELETED")
    if user.role == Role.MEMBER:
        stmt = stmt.where(Event.id.in_(participant))
    elif user.role == Role.DEPARTMENT_HEAD:
        stmt = stmt.where(or_(Event.department_id == user.department_id, Event.id.in_(participant)))
    events = list((await db.scalars(stmt.order_by(Event.event_date))).all())
    return [await event_out(db, event, user) for event in events]


@router.post("", response_model=EventOut, status_code=201)
async def create_event(
    data: EventIn, actor: User = Depends(manager), db: AsyncSession = Depends(get_db)
):
    if actor.role == Role.DEPARTMENT_HEAD and data.department_id != actor.department_id:
        raise AppError(403, "department_scope", "자신의 부서 행사만 만들 수 있습니다.")
    participant_ids = set(data.participant_ids)
    valid_participant_ids = set(
        (
            await db.scalars(
                select(User.id).where(
                    User.id.in_(participant_ids),
                    User.term_id == actor.term_id,
                    User.is_active.is_(True),
                )
            )
        ).all()
    )
    if valid_participant_ids != participant_ids:
        raise AppError(422, "invalid_participants", "현재 기수의 활성 사용자만 참여할 수 있습니다.")
    event = Event(
        **data.model_dump(exclude={"manager_id", "participant_ids"}),
        term_id=actor.term_id,
        manager_id=data.manager_id or actor.id,
    )
    db.add(event)
    await db.flush()
    db.add_all(
        [EventParticipant(event_id=event.id, user_id=user_id) for user_id in participant_ids]
    )
    await db.commit()
    await db.refresh(event)
    return await event_out(db, event, actor)


def teacher_event_description(data: TeacherEventCreateIn) -> str:
    sections = [
        ("행사 목적", data.purpose),
        ("참여 대상", data.target_participants),
        ("진행 일정", data.schedule_plan),
        ("세부 프로그램", data.program_plan),
        ("예산과 준비물", data.preparation_plan),
        ("안전 계획", data.safety_plan),
    ]
    return "\n\n".join(f"{title}\n{content.strip()}" for title, content in sections if content)


@router.post("/teacher-create", response_model=TeacherEventCreateOut, status_code=201)
async def create_teacher_event(
    data: TeacherEventCreateIn,
    teacher: User = Depends(require_roles(Role.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    if data.starts_at and data.ends_at and data.ends_at <= data.starts_at:
        raise AppError(422, "invalid_event_time", "종료 시간은 시작 시간보다 늦어야 합니다.")
    operation_dates = sorted(set(data.operation_dates))
    if data.event_date not in operation_dates:
        raise AppError(422, "event_date_not_in_operation_dates", "행사 날짜를 활동 날짜에 포함해 주세요.")
    requirement_names = [item.name.strip() for item in data.team_requirements]
    if any(not name for name in requirement_names):
        raise AppError(422, "team_name_required", "모든 조의 이름을 적어 주세요.")
    if len(set(requirement_names)) != len(requirement_names):
        raise AppError(422, "duplicate_team_name", "조 이름은 서로 달라야 합니다.")

    requested_participant_ids = set(data.participant_ids)
    valid_participant_ids = set(
        (
            await db.scalars(
                select(User.id).where(
                    User.id.in_(requested_participant_ids),
                    User.term_id == teacher.term_id,
                    User.is_active.is_(True),
                    User.role != Role.TEACHER,
                )
            )
        ).all()
    )
    if valid_participant_ids != requested_participant_ids:
        raise AppError(422, "invalid_participants", "현재 기수의 활성 학생만 참여자로 선택할 수 있습니다.")
    required_people_per_day = sum(item.people_count for item in data.team_requirements)
    if required_people_per_day != len(valid_participant_ids):
        raise AppError(
            422,
            "team_capacity_mismatch",
            "조별 필요 인원 합계와 선택한 참여 학생 수를 같게 맞춰 주세요.",
        )
    if data.team_manager_id not in valid_participant_ids:
        raise AppError(
            422,
            "team_manager_must_participate",
            "조 편성 담당 학생을 행사 참여자에 포함해 주세요.",
        )

    manager = await db.scalar(
        select(User).where(
            User.id == data.team_manager_id,
            User.term_id == teacher.term_id,
            User.is_active.is_(True),
            User.role != Role.TEACHER,
        )
    )
    if not manager:
        raise AppError(422, "invalid_team_manager", "현재 기수의 활성 학생을 조 편성 담당자로 선택해 주세요.")

    description = teacher_event_description(data)
    event = Event(
        term_id=teacher.term_id,
        title=data.title.strip(),
        type=data.type,
        description=description,
        location=data.location.strip(),
        event_date=data.event_date,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        department_id=None,
        manager_id=teacher.id,
        status="PLANNED",
    )
    db.add(event)
    await db.flush()
    db.add_all(
        EventParticipant(event_id=event.id, user_id=user_id)
        for user_id in valid_participant_ids
    )

    local_zone = ZoneInfo(settings.default_timezone)
    due_at = data.formation_due_at or datetime.combine(
        operation_dates[0] - timedelta(days=7), time(18, 0), tzinfo=local_zone
    )
    normalized_requirements = [
        {
            "name": name,
            "people_count": item.people_count,
            "role_description": item.role_description.strip(),
        }
        for name, item in zip(requirement_names, data.team_requirements, strict=True)
    ]
    task = Task(
        term_id=teacher.term_id,
        event_id=event.id,
        title=f"{event.title} 조 편성",
        description=(
            "담당 선생님이 작성한 행사 계획에 맞춰 참여 학생을 조로 편성해 주세요.\n\n"
            f"{description}"
        ),
        type=TaskType.TEAM_FORMATION,
        status=TaskStatus.TODO,
        due_at=due_at,
        operation_days=len(operation_dates),
        teams_per_day=len(normalized_requirements),
        people_per_team=max(item["people_count"] for item in normalized_requirements),
        team_role_description=" / ".join(
            item["role_description"] for item in normalized_requirements
        )[:500],
        team_requirements=normalized_requirements,
        operation_dates=[value.isoformat() for value in operation_dates],
        created_by=teacher.id,
    )
    db.add(task)
    await db.flush()
    task.formation_draft = await build_team_formation_draft(db, task)
    db.add(TaskAssignee(task_id=task.id, user_id=manager.id))
    await db.commit()

    await create_notifications(
        db,
        {manager.id},
        notification_type="TEAM_FORMATION_ASSIGNED",
        title="행사 조 편성을 맡아 주세요",
        content=f"{event.title} 계획을 확인하고 {len(operation_dates)}일의 조 편성을 완료해 주세요.",
        target_type="task",
        target_id=task.id,
    )
    return TeacherEventCreateOut(event_id=event.id, task_id=task.id)


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    event = await db.get(Event, event_id)
    participant = event and await db.scalar(
        select(EventParticipant.id).where(
            EventParticipant.event_id == event_id, EventParticipant.user_id == user.id
        )
    )
    if (
        not event
        or event.term_id != user.term_id
        or event.status == "DELETED"
        or (not can_manage(user, event) and not participant)
    ):
        raise AppError(404, "event_not_found", "행사를 찾을 수 없습니다.")
    return await event_out(db, event, user)


@router.patch("/{event_id}", response_model=EventOut)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if not event or event.term_id != actor.term_id or event.status == "DELETED":
        raise AppError(404, "event_not_found", "행사를 찾을 수 없습니다.")
    if not can_manage(actor, event):
        raise AppError(403, "forbidden", "행사를 수정할 권한이 없습니다.")
    if data.starts_at and data.ends_at and data.ends_at <= data.starts_at:
        raise AppError(422, "invalid_event_time", "종료 시간은 시작 시간보다 늦어야 합니다.")
    for key, value in data.model_dump().items():
        setattr(event, key, value)
    await db.commit()
    await db.refresh(event)
    return await event_out(db, event, actor)


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: uuid.UUID,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
) -> None:
    event = await db.get(Event, event_id)
    if not event or event.term_id != actor.term_id or event.status == "DELETED":
        raise AppError(404, "event_not_found", "행사를 찾을 수 없습니다.")
    if not can_manage(actor, event):
        raise AppError(403, "forbidden", "행사를 삭제할 권한이 없습니다.")
    event.status = "DELETED"
    await db.execute(
        update(Task)
        .where(Task.event_id == event.id, Task.status != TaskStatus.DONE)
        .values(status=TaskStatus.DONE)
    )
    await db.commit()


@router.put("/{event_id}/participants", status_code=204)
async def replace_participants(
    event_id: uuid.UUID,
    ids: list[uuid.UUID],
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if not event or not can_manage(actor, event):
        raise AppError(403, "forbidden", "참여자를 변경할 권한이 없습니다.")
    await db.execute(delete(EventParticipant).where(EventParticipant.event_id == event_id))
    db.add_all([EventParticipant(event_id=event_id, user_id=value) for value in set(ids)])
    await db.commit()
