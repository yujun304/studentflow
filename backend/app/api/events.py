import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, current_user, require_roles
from app.models.entities import Event, EventParticipant, Role, User
from app.schemas import EventIn, EventOut

router = APIRouter(prefix="/events", tags=["events"], dependencies=[Depends(csrf_protect)])
manager = require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)


def can_manage(user: User, event: Event | None = None) -> bool:
    if user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER}:
        return True
    return user.role == Role.DEPARTMENT_HEAD and (
        event is None or event.department_id == user.department_id
    )


async def event_out(db: AsyncSession, event: Event) -> EventOut:
    participant_ids = list(
        (
            await db.scalars(
                select(EventParticipant.user_id).where(EventParticipant.event_id == event.id)
            )
        ).all()
    )
    return EventOut.model_validate(event).model_copy(update={"participant_ids": participant_ids})


@router.get("", response_model=list[EventOut])
async def list_events(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    participant = select(EventParticipant.event_id).where(EventParticipant.user_id == user.id)
    stmt = select(Event).where(Event.term_id == user.term_id)
    if user.role == Role.MEMBER:
        stmt = stmt.where(Event.id.in_(participant))
    elif user.role == Role.DEPARTMENT_HEAD:
        stmt = stmt.where(or_(Event.department_id == user.department_id, Event.id.in_(participant)))
    events = list((await db.scalars(stmt.order_by(Event.event_date))).all())
    return [await event_out(db, event) for event in events]


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
    return await event_out(db, event)


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
        or (not can_manage(user, event) and not participant)
    ):
        raise AppError(404, "event_not_found", "행사를 찾을 수 없습니다.")
    return await event_out(db, event)


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
