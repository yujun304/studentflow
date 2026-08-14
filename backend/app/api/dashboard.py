from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import current_user
from app.models.entities import (
    Event,
    EventParticipant,
    Notice,
    NoticeRecipient,
    Submission,
    SubmissionStatus,
    Task,
    TaskAssignee,
    TaskStatus,
    User,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    now = datetime.now(UTC)
    upcoming_events = list(
        (
            await db.scalars(
                select(Event)
                .join(EventParticipant)
                .where(
                    EventParticipant.user_id == user.id,
                    Event.term_id == user.term_id,
                    Event.event_date >= now.date(),
                )
                .order_by(Event.event_date)
                .limit(5)
            )
        ).all()
    )
    due_tasks = list(
        (
            await db.scalars(
                select(Task)
                .join(TaskAssignee)
                .where(
                    TaskAssignee.user_id == user.id,
                    Task.term_id == user.term_id,
                    Task.status.not_in([TaskStatus.DONE]),
                    Task.due_at <= now + timedelta(days=7),
                )
                .order_by(Task.due_at)
                .limit(8)
            )
        ).all()
    )
    unread_notices = list(
        (
            await db.scalars(
                select(Notice)
                .join(NoticeRecipient)
                .where(
                    NoticeRecipient.user_id == user.id,
                    NoticeRecipient.read_at.is_(None),
                    Notice.term_id == user.term_id,
                )
                .order_by(Notice.pinned.desc(), Notice.created_at.desc())
                .limit(5)
            )
        ).all()
    )
    review_count = 0
    if user.role.value != "MEMBER":
        review_count = (
            await db.scalar(
                select(func.count())
                .select_from(Submission)
                .where(Submission.status == SubmissionStatus.SUBMITTED)
            )
            or 0
        )
    return {
        "upcoming_events": upcoming_events,
        "due_tasks": due_tasks,
        "unread_notices": unread_notices,
        "review_count": review_count,
    }
