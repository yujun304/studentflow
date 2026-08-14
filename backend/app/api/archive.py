import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import current_user
from app.models.entities import Event, HandoverGuide, MeetingRecord, Task, Term, User

router = APIRouter(prefix="/archive", tags=["archive"])


def term_out(term: Term) -> dict:
    return {
        "id": term.id,
        "name": term.name,
        "starts_on": term.starts_on,
        "ends_on": term.ends_on,
        "is_current": term.is_current,
    }


@router.get("/terms")
async def archived_terms(
    _: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    terms = list(
        (
            await db.scalars(
                select(Term).where(Term.is_current.is_(False)).order_by(Term.starts_on.desc())
            )
        ).all()
    )
    return [term_out(term) for term in terms]


@router.get("/terms/{term_id}")
async def archived_term(
    term_id: uuid.UUID,
    _: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    term = await db.get(Term, term_id)
    if not term or term.is_current:
        raise AppError(404, "archive_not_found", "보관된 기수를 찾을 수 없습니다.")
    event_count, task_count, meeting_count, handover_count = (
        await db.scalar(select(func.count()).select_from(Event).where(Event.term_id == term.id)),
        await db.scalar(select(func.count()).select_from(Task).where(Task.term_id == term.id)),
        await db.scalar(
            select(func.count()).select_from(MeetingRecord).where(MeetingRecord.term_id == term.id)
        ),
        await db.scalar(
            select(func.count())
            .select_from(HandoverGuide)
            .where(
                HandoverGuide.term_id == term.id,
                HandoverGuide.published_at.is_not(None),
            )
        ),
    )
    return {
        **term_out(term),
        "summary": {
            "events": event_count,
            "tasks": task_count,
            "meeting_records": meeting_count,
            "published_handovers": handover_count,
        },
    }
