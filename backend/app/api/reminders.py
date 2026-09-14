import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.comments import visible_task
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import current_user
from app.models.entities import QuickMemo, Reminder, SavedItem, User
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
async def list_memos(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    return list(
        (
            await db.scalars(
                select(QuickMemo)
                .where(QuickMemo.user_id == user.id, QuickMemo.term_id == user.term_id)
                .order_by(QuickMemo.created_at.desc())
            )
        ).all()
    )


@router.post("/memos", response_model=QuickMemoOut)
async def create_memo(
    data: QuickMemoIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    content = data.content.strip()
    if not content:
        raise AppError(422, "memo_content_required", "메모 내용을 입력해 주세요.")
    memo = QuickMemo(user_id=user.id, term_id=user.term_id, content=content)
    db.add(memo)
    await db.commit()
    await db.refresh(memo)
    return memo


@router.delete("/memos/{memo_id}", status_code=204)
async def delete_memo(
    memo_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    memo = await db.get(QuickMemo, memo_id)
    if not memo or memo.user_id != user.id or memo.term_id != user.term_id:
        raise AppError(404, "memo_not_found", "메모를 찾을 수 없습니다.")
    await db.delete(memo)
    await db.commit()
    return Response(status_code=204)


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
async def list_saved_items(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    items = list(
        (
            await db.scalars(
                select(SavedItem)
                .where(SavedItem.user_id == user.id)
                .order_by(SavedItem.created_at.desc())
            )
        ).all()
    )
    visible: list[SavedItem] = []
    for item in items:
        if item.target_type != "task":
            continue
        try:
            await visible_task(db, item.target_id, user)
        except AppError:
            continue
        visible.append(item)
    return visible


@router.post("/saved-items", response_model=SavedItemOut)
async def save_item(
    data: SavedItemIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.target_type != "task":
        raise AppError(422, "saved_target_invalid", "현재는 업무 저장만 지원합니다.")
    await visible_task(db, data.target_id, user)
    existing = await db.scalar(
        select(SavedItem).where(
            SavedItem.user_id == user.id,
            SavedItem.target_type == data.target_type,
            SavedItem.target_id == data.target_id,
        )
    )
    if existing:
        return existing
    item = SavedItem(user_id=user.id, **data.model_dump())
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            select(SavedItem).where(
                SavedItem.user_id == user.id,
                SavedItem.target_type == data.target_type,
                SavedItem.target_id == data.target_id,
            )
        )
        if existing:
            return existing
        raise
    await db.refresh(item)
    return item


@router.delete("/saved-items/{item_id}", status_code=204)
async def delete_saved_item(
    item_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(SavedItem, item_id)
    if not item or item.user_id != user.id:
        raise AppError(404, "saved_item_not_found", "저장한 항목을 찾을 수 없습니다.")
    await db.delete(item)
    await db.commit()
    return Response(status_code=204)
