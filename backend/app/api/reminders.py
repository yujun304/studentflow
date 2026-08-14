from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pending import feature_not_ready
from app.core.database import get_db
from app.core.security import current_user
from app.models.entities import Reminder, User
from app.schemas import (
    QuickMemoIn,
    QuickMemoOut,
    ReminderIn,
    ReminderOut,
    SavedItemIn,
    SavedItemOut,
)
from app.services.team_calendar import validate_calendar_color

router = APIRouter(tags=["personal-tools"])


@router.get("/memos", response_model=list[QuickMemoOut])
async def list_memos(_: User = Depends(current_user)):
    feature_not_ready()


@router.post("/memos", response_model=QuickMemoOut)
async def create_memo(_: QuickMemoIn, __: User = Depends(current_user)):
    feature_not_ready()


@router.get("/reminders", response_model=list[ReminderOut])
async def list_reminders(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return list(
        (
            await db.scalars(
                select(Reminder)
                .where(Reminder.user_id == user.id, Reminder.term_id == user.term_id)
                .order_by(Reminder.remind_at)
            )
        ).all()
    )


@router.post("/reminders", response_model=ReminderOut)
async def create_reminder(
    data: ReminderIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    reminder = Reminder(
        **data.model_dump(exclude={"color"}),
        color=validate_calendar_color(data.color),
        user_id=user.id,
        term_id=user.term_id,
        category="PERSONAL",
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.get("/saved-items", response_model=list[SavedItemOut])
async def list_saved_items(_: User = Depends(current_user)):
    feature_not_ready()


@router.post("/saved-items", response_model=SavedItemOut)
async def save_item(_: SavedItemIn, __: User = Depends(current_user)):
    feature_not_ready()
