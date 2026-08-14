import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import current_user, require_roles
from app.models.entities import Event, MeetingAttendee, MeetingRecord, Role, User
from app.schemas import MeetingRecordIn, MeetingRecordOut

router = APIRouter(prefix="/meeting-records", tags=["meeting-records"])


@router.get("", response_model=list[MeetingRecordOut])
async def list_records(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    records = list(
        (
            await db.scalars(
                select(MeetingRecord)
                .where(MeetingRecord.term_id == user.term_id)
                .order_by(MeetingRecord.held_at.desc())
            )
        ).all()
    )
    return [await record_out(db, record) for record in records]


@router.post("", response_model=MeetingRecordOut)
async def create_record(
    data: MeetingRecordIn,
    actor: User = Depends(require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)),
    db: AsyncSession = Depends(get_db),
):
    attendee_ids = set(data.attendee_ids)
    valid_ids = set(
        (
            await db.scalars(
                select(User.id).where(
                    User.id.in_(attendee_ids),
                    User.term_id == actor.term_id,
                    User.is_active.is_(True),
                )
            )
        ).all()
    )
    if valid_ids != attendee_ids:
        raise AppError(422, "invalid_attendees", "현재 기수의 활성 사용자만 참석자로 지정할 수 있습니다.")
    if data.event_id:
        event = await db.get(Event, data.event_id)
        if not event or event.term_id != actor.term_id:
            raise AppError(422, "invalid_event", "현재 기수의 행사를 선택해 주세요.")
    record = MeetingRecord(
        **data.model_dump(exclude={"attendee_ids"}), term_id=actor.term_id, author_id=actor.id
    )
    db.add(record)
    await db.flush()
    db.add_all(
        [MeetingAttendee(meeting_record_id=record.id, user_id=user_id) for user_id in attendee_ids]
    )
    await db.commit()
    await db.refresh(record)
    return await record_out(db, record)


@router.get("/{record_id}", response_model=MeetingRecordOut)
async def get_record(
    record_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(MeetingRecord, record_id)
    if not record or record.term_id != user.term_id:
        raise AppError(404, "meeting_not_found", "회의록을 찾을 수 없습니다.")
    return await record_out(db, record)


async def record_out(db: AsyncSession, record: MeetingRecord) -> MeetingRecordOut:
    attendee_ids = list(
        (
            await db.scalars(
                select(MeetingAttendee.user_id).where(
                    MeetingAttendee.meeting_record_id == record.id
                )
            )
        ).all()
    )
    return MeetingRecordOut.model_validate(record).model_copy(update={"attendee_ids": attendee_ids})
