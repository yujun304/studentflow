import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, current_user, require_roles
from app.models.entities import (
    ApplicationStatus,
    Event,
    EventParticipant,
    Notice,
    NoticeApplication,
    NoticeRecipient,
    NoticeType,
    RequestStatus,
    Role,
    ScheduleChangeRequest,
    User,
)
from app.schemas import NoticeIn, NoticeOut, NoticeUpdate, ScheduleRequestIn, ScheduleReviewIn
from app.services.notifications import create_notifications

router = APIRouter(tags=["notices"], dependencies=[Depends(csrf_protect)])
manager = require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)


def can_edit_notice(notice: Notice, user: User) -> bool:
    return user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER} or (
        user.role == Role.DEPARTMENT_HEAD and notice.author_id == user.id
    )


def notice_out(notice: Notice, user: User, recipient_ids: set[uuid.UUID]) -> NoticeOut:
    return NoticeOut.model_validate(notice).model_copy(
        update={
            "recipient_ids": list(recipient_ids) if can_edit_notice(notice, user) else [],
            "can_edit": can_edit_notice(notice, user),
        }
    )


async def notice_recipients(
    db: AsyncSession, notice_ids: list[uuid.UUID]
) -> dict[uuid.UUID, set[uuid.UUID]]:
    result: dict[uuid.UUID, set[uuid.UUID]] = {notice_id: set() for notice_id in notice_ids}
    if not notice_ids:
        return result
    rows = (
        await db.execute(
            select(NoticeRecipient.notice_id, NoticeRecipient.user_id).where(
                NoticeRecipient.notice_id.in_(notice_ids)
            )
        )
    ).all()
    for notice_id, user_id in rows:
        result[notice_id].add(user_id)
    return result


async def validate_recipients(
    db: AsyncSession, actor: User, recipient_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    requested = set(recipient_ids)
    if not requested:
        raise AppError(422, "recipients_required", "공지 수신자를 한 명 이상 선택해 주세요.")
    statement = select(User.id).where(
        User.id.in_(requested), User.term_id == actor.term_id, User.is_active.is_(True)
    )
    if actor.role == Role.DEPARTMENT_HEAD:
        statement = statement.where(User.department_id == actor.department_id)
    allowed = set((await db.scalars(statement)).all())
    if allowed != requested:
        raise AppError(
            403, "recipient_scope", "현재 기수의 관리 가능한 사용자에게만 공지할 수 있습니다."
        )
    return requested


@router.get("/notices", response_model=list[NoticeOut])
async def list_notices(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    received = select(NoticeRecipient.notice_id).where(NoticeRecipient.user_id == user.id)
    stmt = select(Notice).where(Notice.term_id == user.term_id)
    if user.role == Role.MEMBER:
        stmt = stmt.where(Notice.id.in_(received))
    elif user.role == Role.DEPARTMENT_HEAD:
        stmt = stmt.where(or_(Notice.id.in_(received), Notice.author_id == user.id))
    notices = list(
        (await db.scalars(stmt.order_by(Notice.pinned.desc(), Notice.created_at.desc()))).all()
    )
    recipients = await notice_recipients(db, [notice.id for notice in notices])
    return [notice_out(notice, user, recipients[notice.id]) for notice in notices]


@router.post("/notices", response_model=NoticeOut, status_code=201)
async def create_notice(
    data: NoticeIn, actor: User = Depends(manager), db: AsyncSession = Depends(get_db)
):
    if data.type == NoticeType.FIRST_COME and not data.capacity:
        raise AppError(422, "capacity_required", "선착순 공지에는 정원이 필요합니다.")
    recipient_ids = await validate_recipients(db, actor, data.recipient_ids)
    notice = Notice(
        **data.model_dump(exclude={"recipient_ids"}), term_id=actor.term_id, author_id=actor.id
    )
    db.add(notice)
    await db.flush()
    db.add_all([NoticeRecipient(notice_id=notice.id, user_id=value) for value in recipient_ids])
    await db.commit()
    await db.refresh(notice)
    recipients = recipient_ids - {actor.id}
    if recipients:
        await create_notifications(
            db,
            recipients,
            notification_type="NOTICE_PUBLISHED",
            title="새 공지가 게시되었습니다",
            content=notice.title,
            target_type="notice",
            target_id=notice.id,
        )
    return notice_out(notice, actor, recipient_ids)


@router.patch("/notices/{notice_id}", response_model=NoticeOut)
async def update_notice(
    notice_id: uuid.UUID,
    data: NoticeUpdate,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    notice = await db.get(Notice, notice_id)
    if not notice or notice.term_id != actor.term_id:
        raise AppError(404, "notice_not_found", "공지를 찾을 수 없습니다.")
    if not can_edit_notice(notice, actor):
        raise AppError(403, "notice_edit_forbidden", "직접 등록한 공지만 수정할 수 있습니다.")
    values = data.model_dump(exclude_unset=True, exclude={"recipient_ids"})
    if values.get("title") is None and "title" in values:
        raise AppError(422, "title_required", "공지 제목이 필요합니다.")
    if values.get("content") is None and "content" in values:
        raise AppError(422, "content_required", "공지 내용이 필요합니다.")
    resulting_type = data.type if data.type is not None else notice.type
    resulting_capacity = data.capacity if "capacity" in values else notice.capacity
    if resulting_type == NoticeType.FIRST_COME and not resulting_capacity:
        raise AppError(422, "capacity_required", "선착순 공지에는 정원이 필요합니다.")
    for key, value in values.items():
        if key == "type" and value is None:
            raise AppError(422, "type_required", "공지 유형이 필요합니다.")
        setattr(notice, key, value)
    recipient_ids = (await notice_recipients(db, [notice.id]))[notice.id]
    if data.recipient_ids is not None:
        updated_ids = await validate_recipients(db, actor, data.recipient_ids)
        removed_ids = recipient_ids - updated_ids
        if removed_ids:
            await db.execute(
                delete(NoticeApplication).where(
                    NoticeApplication.notice_id == notice.id,
                    NoticeApplication.user_id.in_(removed_ids),
                )
            )
            await db.execute(
                delete(NoticeRecipient).where(
                    NoticeRecipient.notice_id == notice.id,
                    NoticeRecipient.user_id.in_(removed_ids),
                )
            )
        db.add_all(
            [
                NoticeRecipient(notice_id=notice.id, user_id=user_id)
                for user_id in updated_ids - recipient_ids
            ]
        )
        recipient_ids = updated_ids
    await db.commit()
    return notice_out(notice, actor, recipient_ids)


@router.post("/notices/{notice_id}/read", status_code=204)
async def mark_read(
    notice_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    recipient = await db.scalar(
        select(NoticeRecipient).where(
            NoticeRecipient.notice_id == notice_id, NoticeRecipient.user_id == user.id
        )
    )
    if not recipient:
        raise AppError(404, "notice_not_found", "공지를 찾을 수 없습니다.")
    recipient.read_at = datetime.now(UTC)
    await db.commit()


@router.post("/notices/{notice_id}/apply", status_code=201)
async def apply(
    notice_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    notice = await db.scalar(select(Notice).where(Notice.id == notice_id).with_for_update())
    recipient = await db.scalar(
        select(NoticeRecipient.id).where(
            NoticeRecipient.notice_id == notice_id, NoticeRecipient.user_id == user.id
        )
    )
    if not notice or not recipient or notice.type != NoticeType.FIRST_COME:
        raise AppError(404, "notice_not_found", "신청 가능한 공지를 찾을 수 없습니다.")
    existing = await db.scalar(
        select(NoticeApplication).where(
            NoticeApplication.notice_id == notice_id, NoticeApplication.user_id == user.id
        )
    )
    if existing and existing.status != ApplicationStatus.CANCELLED:
        raise AppError(409, "already_applied", "이미 신청했습니다.")
    accepted = await db.scalar(
        select(func.count())
        .select_from(NoticeApplication)
        .where(
            NoticeApplication.notice_id == notice_id,
            NoticeApplication.status == ApplicationStatus.ACCEPTED,
        )
    )
    status = ApplicationStatus.ACCEPTED if accepted < notice.capacity else ApplicationStatus.WAITING
    if status == ApplicationStatus.WAITING and not notice.waiting_enabled:
        raise AppError(409, "capacity_full", "신청 정원이 마감되었습니다.")
    sequence = (
        await db.scalar(
            select(func.max(NoticeApplication.sequence)).where(
                NoticeApplication.notice_id == notice_id
            )
        )
        or 0
    ) + 1
    if existing:
        existing.status, existing.sequence, existing.created_at = (
            status,
            sequence,
            datetime.now(UTC),
        )
        application = existing
    else:
        application = NoticeApplication(
            notice_id=notice_id, user_id=user.id, status=status, sequence=sequence
        )
        db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


@router.post("/notices/{notice_id}/cancel", status_code=204)
async def cancel(
    notice_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    await db.scalar(select(Notice).where(Notice.id == notice_id).with_for_update())
    application = await db.scalar(
        select(NoticeApplication).where(
            NoticeApplication.notice_id == notice_id, NoticeApplication.user_id == user.id
        )
    )
    if not application or application.status == ApplicationStatus.CANCELLED:
        raise AppError(404, "application_not_found", "신청 내역을 찾을 수 없습니다.")
    promote = application.status == ApplicationStatus.ACCEPTED
    application.status = ApplicationStatus.CANCELLED
    if promote:
        waiting = await db.scalar(
            select(NoticeApplication)
            .where(
                NoticeApplication.notice_id == notice_id,
                NoticeApplication.status == ApplicationStatus.WAITING,
            )
            .order_by(NoticeApplication.sequence)
            .with_for_update()
            .limit(1)
        )
        if waiting:
            waiting.status = ApplicationStatus.ACCEPTED
    await db.commit()


@router.post("/schedule-change-requests", status_code=201)
async def request_change(
    data: ScheduleRequestIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    event = await db.get(Event, data.event_id)
    participant = event and await db.scalar(
        select(EventParticipant.id).where(
            EventParticipant.event_id == event.id, EventParticipant.user_id == user.id
        )
    )
    if not event or not participant:
        raise AppError(403, "not_participant", "참여 행사에 대해서만 변경을 요청할 수 있습니다.")
    item = ScheduleChangeRequest(**data.model_dump(), user_id=user.id, status=RequestStatus.PENDING)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/schedule-change-requests/{request_id}/review")
async def review_change(
    request_id: uuid.UUID,
    data: ScheduleReviewIn,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ScheduleChangeRequest, request_id)
    if not item or item.status != RequestStatus.PENDING:
        raise AppError(404, "request_not_found", "처리할 요청을 찾을 수 없습니다.")
    event = await db.get(Event, item.event_id)
    if actor.role == Role.DEPARTMENT_HEAD and event.department_id != actor.department_id:
        raise AppError(403, "department_scope", "자신의 부서 행사 요청만 처리할 수 있습니다.")
    if data.status not in {RequestStatus.APPROVED, RequestStatus.REJECTED}:
        raise AppError(422, "invalid_status", "승인 또는 반려 상태를 선택해 주세요.")
    if data.status == RequestStatus.REJECTED and not data.reason:
        raise AppError(422, "reason_required", "반려 사유가 필요합니다.")
    item.status = data.status
    item.rejection_reason = data.reason
    item.reviewed_by = actor.id
    await db.commit()
    return item
