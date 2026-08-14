import json
import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import current_user, require_roles
from app.models.entities import (
    Attendance,
    AttendanceStatus,
    AuditLog,
    Department,
    Event,
    EventParticipant,
    Role,
    User,
)
from app.schemas import (
    AttendanceChecklistItemOut,
    AttendanceChecklistOut,
    AttendanceIn,
    AttendanceSummary,
)

router = APIRouter(prefix="/events/{event_id}/attendance", tags=["attendance"])
attendance_manager = require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)


def can_manage_attendance(actor: User, event: Event) -> bool:
    if actor.role in {Role.EXECUTIVE_BOARD, Role.TEACHER}:
        return True
    return actor.role == Role.DEPARTMENT_HEAD and (
        event.manager_id == actor.id or event.department_id == actor.department_id
    )


async def accessible_event(
    db: AsyncSession, event_id: uuid.UUID, actor: User, *, require_manage: bool = False
) -> tuple[Event, bool]:
    event = await db.get(Event, event_id)
    if not event or event.term_id != actor.term_id:
        raise AppError(404, "event_not_found", "행사를 찾을 수 없습니다.")
    manageable = can_manage_attendance(actor, event)
    if require_manage and not manageable:
        raise AppError(403, "attendance_forbidden", "이 행사의 출석을 기록할 권한이 없습니다.")
    if not manageable:
        participant = await db.scalar(
            select(EventParticipant.id).where(
                EventParticipant.event_id == event.id,
                EventParticipant.user_id == actor.id,
            )
        )
        if not participant:
            raise AppError(404, "event_not_found", "행사를 찾을 수 없습니다.")
    return event, manageable


def event_window(event: Event) -> tuple[bool, bool]:
    timezone = ZoneInfo(settings.default_timezone)
    now = datetime.now(UTC).astimezone(timezone)
    starts_at = datetime.combine(event.event_date, event.starts_at or time.min, tzinfo=timezone)
    ends_at = datetime.combine(event.event_date, event.ends_at or time.max, tzinfo=timezone)
    if event.starts_at and event.ends_at and event.ends_at < event.starts_at:
        ends_at += timedelta(days=1)
    return now.date() == event.event_date, starts_at <= now <= ends_at


async def build_checklist(
    db: AsyncSession, event: Event, actor: User, can_edit: bool
) -> AttendanceChecklistOut:
    participant_ids = select(EventParticipant.user_id).where(EventParticipant.event_id == event.id)
    user_statement = (
        select(User, Department.name)
        .outerjoin(Department, Department.id == User.department_id)
        .where(User.id.in_(participant_ids))
        .order_by(User.grade, User.name)
    )
    if not can_edit:
        user_statement = user_statement.where(User.id == actor.id)
    user_rows = (await db.execute(user_statement)).all()
    user_ids = [user.id for user, _ in user_rows]
    attendance_records = list(
        (
            await db.scalars(
                select(Attendance).where(
                    Attendance.event_id == event.id, Attendance.user_id.in_(user_ids)
                )
            )
        ).all()
    )
    attendance_by_user = {record.user_id: record for record in attendance_records}
    recorder_ids = {record.recorded_by for record in attendance_records if record.recorded_by}
    recorder_names = {
        recorder.id: recorder.name
        for recorder in (await db.scalars(select(User).where(User.id.in_(recorder_ids)))).all()
    }
    items: list[AttendanceChecklistItemOut] = []
    for user, department_name in user_rows:
        record = attendance_by_user.get(user.id)
        items.append(
            AttendanceChecklistItemOut(
                attendance_id=record.id if record else None,
                user_id=user.id,
                user_name=user.name,
                grade=user.grade,
                department_id=user.department_id,
                department_name=department_name,
                status=record.status if record else AttendanceStatus.PENDING,
                note=record.note if record else None,
                recorded_by=record.recorded_by if record else None,
                recorded_by_name=(recorder_names.get(record.recorded_by) if record else None),
                updated_at=record.updated_at if record else None,
            )
        )
    counts = {status: 0 for status in AttendanceStatus}
    for item in items:
        counts[item.status] += 1
    is_event_day, is_during_event = event_window(event)
    return AttendanceChecklistOut(
        event_id=event.id,
        event_title=event.title,
        event_date=event.event_date,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        is_event_day=is_event_day,
        is_during_event=is_during_event,
        can_edit=can_edit,
        summary=AttendanceSummary(
            total=len(items),
            pending=counts[AttendanceStatus.PENDING],
            present=counts[AttendanceStatus.PRESENT],
            absent=counts[AttendanceStatus.ABSENT],
            late=counts[AttendanceStatus.LATE],
            left_early=counts[AttendanceStatus.LEFT_EARLY],
        ),
        items=items,
    )


async def store_attendance(
    db: AsyncSession,
    event: Event,
    actor: User,
    records: list[AttendanceIn],
) -> None:
    requested_ids = [record.user_id for record in records]
    if len(set(requested_ids)) != len(requested_ids):
        raise AppError(
            422, "duplicate_attendance_user", "한 사용자의 출석 상태는 한 번만 보내 주세요."
        )
    participant_ids = set(
        (
            await db.scalars(
                select(EventParticipant.user_id).where(
                    EventParticipant.event_id == event.id,
                    EventParticipant.user_id.in_(requested_ids),
                )
            )
        ).all()
    )
    if participant_ids != set(requested_ids):
        raise AppError(422, "invalid_attendance_user", "행사 참여자만 출석 처리할 수 있습니다.")
    existing = {
        attendance.user_id: attendance
        for attendance in (
            await db.scalars(
                select(Attendance).where(
                    Attendance.event_id == event.id,
                    Attendance.user_id.in_(requested_ids),
                )
            )
        ).all()
    }
    now = datetime.now(UTC)
    for data in records:
        attendance = existing.get(data.user_id)
        previous_status = attendance.status.value if attendance else AttendanceStatus.PENDING.value
        previous_note = attendance.note if attendance else None
        if attendance:
            attendance.status = data.status
            attendance.note = data.note
            attendance.recorded_by = actor.id
            attendance.updated_at = now
        else:
            attendance = Attendance(
                id=uuid.uuid4(),
                event_id=event.id,
                user_id=data.user_id,
                status=data.status,
                note=data.note,
                recorded_by=actor.id,
            )
            db.add(attendance)
        if previous_status != data.status.value or previous_note != data.note:
            db.add(
                AuditLog(
                    actor_id=actor.id,
                    action="ATTENDANCE_UPDATED",
                    entity_type="attendance",
                    entity_id=attendance.id,
                    detail=json.dumps(
                        {
                            "event_id": str(event.id),
                            "user_id": str(data.user_id),
                            "previous_status": previous_status,
                            "status": data.status.value,
                            "previous_note": previous_note,
                            "note": data.note,
                        },
                        ensure_ascii=False,
                    ),
                )
            )
    await db.commit()


@router.get("", response_model=AttendanceChecklistOut)
async def list_attendance(
    event_id: uuid.UUID,
    actor: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    event, manageable = await accessible_event(db, event_id, actor)
    return await build_checklist(db, event, actor, manageable)


@router.put("", response_model=AttendanceChecklistOut)
async def save_attendance(
    event_id: uuid.UUID,
    records: list[AttendanceIn],
    actor: User = Depends(attendance_manager),
    db: AsyncSession = Depends(get_db),
):
    event, _ = await accessible_event(db, event_id, actor, require_manage=True)
    await store_attendance(db, event, actor, records)
    return await build_checklist(db, event, actor, True)


@router.post("/mark-all-present", response_model=AttendanceChecklistOut)
async def mark_all_present(
    event_id: uuid.UUID,
    actor: User = Depends(attendance_manager),
    db: AsyncSession = Depends(get_db),
):
    event, _ = await accessible_event(db, event_id, actor, require_manage=True)
    participant_ids = list(
        (
            await db.scalars(
                select(EventParticipant.user_id).where(EventParticipant.event_id == event.id)
            )
        ).all()
    )
    await store_attendance(
        db,
        event,
        actor,
        [
            AttendanceIn(user_id=user_id, status=AttendanceStatus.PRESENT)
            for user_id in participant_ids
        ],
    )
    return await build_checklist(db, event, actor, True)
