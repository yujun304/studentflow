import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, current_user
from app.models.entities import (
    CommunityPost,
    Event,
    EventParticipant,
    EventType,
    Reminder,
    Role,
    Task,
    TaskAssignee,
    TaskType,
    User,
)
from app.schemas import CalendarItemIn, CalendarItemOut, CalendarItemUpdate
from app.services.team_calendar import validate_calendar_color

router = APIRouter(prefix="/calendar", tags=["calendar"], dependencies=[Depends(csrf_protect)])

EVENT_COLORS = {EventType.EVENT: "#356ae6", EventType.CAMPAIGN: "#7c3aed"}
TASK_COLORS = {
    TaskType.SIMPLE: "#d97706",
    TaskType.SUBMISSION: "#dc2626",
    TaskType.TEAM_FORMATION: "#0891b2",
}
TASK_SOURCES = {
    TaskType.SIMPLE: "TASK_DEADLINE",
    TaskType.SUBMISSION: "SUBMISSION_DEADLINE",
    TaskType.TEAM_FORMATION: "TEAM_FORMATION_DEADLINE",
}
COMMUNITY_MEETING_COLOR = "#7c3aed"
COMMUNITY_MEETING_DEFAULT_TIMES = {
    "MORNING": time(8, 0),
    "LUNCH": time(12, 30),
    "AFTER_SCHOOL": time(16, 0),
}
COMMUNITY_MEETING_SLOT_NAMES = {
    "MORNING": "아침시간",
    "LUNCH": "점심시간",
    "AFTER_SCHOOL": "방과후",
}


def local_datetime(day: date, value: time | None = None) -> datetime:
    return datetime.combine(day, value or time.min, tzinfo=ZoneInfo(settings.default_timezone))


def utc_sort_key(item: CalendarItemOut) -> datetime:
    value = item.starts_at
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@router.get("", response_model=list[CalendarItemOut])
async def calendar_items(
    start: date = Query(...),
    end: date = Query(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if end < start or (end - start).days > 92:
        raise AppError(422, "invalid_calendar_range", "달력 조회 기간은 최대 93일입니다.")
    end_exclusive = end + timedelta(days=1)
    start_at = local_datetime(start).astimezone(UTC)
    end_at = local_datetime(end_exclusive).astimezone(UTC)

    participant_events = select(EventParticipant.event_id).where(
        EventParticipant.user_id == user.id
    )
    event_statement = select(Event).where(
        Event.term_id == user.term_id,
        Event.event_date >= start,
        Event.event_date <= end,
    )
    if user.role == Role.MEMBER:
        event_statement = event_statement.where(Event.id.in_(participant_events))
    elif user.role == Role.DEPARTMENT_HEAD:
        event_statement = event_statement.where(
            or_(
                Event.department_id == user.department_id,
                Event.id.in_(participant_events),
                Event.manager_id == user.id,
            )
        )
    events = list((await db.scalars(event_statement)).all())

    assigned_tasks = select(TaskAssignee.task_id).where(TaskAssignee.user_id == user.id)
    tasks = list(
        (
            await db.scalars(
                select(Task).where(
                    Task.term_id == user.term_id,
                    Task.id.in_(assigned_tasks),
                    Task.due_at.is_not(None),
                    Task.due_at >= start_at,
                    Task.due_at < end_at,
                )
            )
        ).all()
    )
    reminders = list(
        (
            await db.scalars(
                select(Reminder).where(
                    Reminder.user_id == user.id,
                    Reminder.term_id == user.term_id,
                    Reminder.remind_at >= start_at,
                    Reminder.remind_at < end_at,
                )
            )
        ).all()
    )
    community_meetings: list[CommunityPost] = []
    if user.role in {Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD}:
        community_meetings = list(
            (
                await db.scalars(
                    select(CommunityPost).where(
                        CommunityPost.term_id == user.term_id,
                        CommunityPost.agenda_at.is_not(None),
                        CommunityPost.meeting_date >= start,
                        CommunityPost.meeting_date <= end,
                    )
                )
            ).all()
        )

    result: list[CalendarItemOut] = []
    for event in events:
        starts_at = local_datetime(event.event_date, event.starts_at)
        ends_at = local_datetime(event.event_date, event.ends_at) if event.ends_at else None
        result.append(
            CalendarItemOut(
                id=f"event:{event.id}",
                source=event.type.value,
                title=event.title,
                description=event.location,
                starts_at=starts_at,
                ends_at=ends_at,
                color=EVENT_COLORS[event.type],
            )
        )
    result.extend(
        CalendarItemOut(
            id=f"task:{task.id}",
            source=TASK_SOURCES[task.type],
            title=task.title,
            description="업무 마감",
            starts_at=task.due_at,
            color=TASK_COLORS[task.type],
        )
        for task in tasks
    )
    result.extend(
        CalendarItemOut(
            id=str(reminder.id),
            source="TEAM_REMINDER" if reminder.category == "TEAM" else "PERSONAL",
            title=reminder.title,
            description=reminder.content,
            starts_at=reminder.remind_at,
            color=reminder.color,
            editable=reminder.category == "PERSONAL",
        )
        for reminder in reminders
    )
    result.extend(
        CalendarItemOut(
            id=f"community-meeting:{meeting.id}",
            source="COMMUNITY_MEETING",
            title=f"부장회의 · {meeting.title}",
            description=(
                f"{COMMUNITY_MEETING_SLOT_NAMES.get(meeting.meeting_time_slot or '', '시간 미정')}"
                + (f" · {meeting.meeting_time.strftime('%H:%M')}" if meeting.meeting_time else "")
            ),
            starts_at=local_datetime(
                meeting.meeting_date,
                meeting.meeting_time
                or COMMUNITY_MEETING_DEFAULT_TIMES.get(meeting.meeting_time_slot or ""),
            ),
            color=COMMUNITY_MEETING_COLOR,
        )
        for meeting in community_meetings
        if meeting.meeting_date is not None
    )
    return sorted(result, key=utc_sort_key)


@router.post("/items", response_model=CalendarItemOut, status_code=201)
async def create_calendar_item(
    data: CalendarItemIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    reminder = Reminder(
        user_id=user.id,
        term_id=user.term_id,
        title=data.title,
        content=data.content,
        remind_at=data.starts_at,
        color=validate_calendar_color(data.color),
        category="PERSONAL",
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return CalendarItemOut(
        id=str(reminder.id),
        source="PERSONAL",
        title=reminder.title,
        description=reminder.content,
        starts_at=reminder.remind_at,
        color=reminder.color,
        editable=True,
    )


@router.patch("/items/{item_id}", response_model=CalendarItemOut)
async def update_calendar_item(
    item_id: uuid.UUID,
    data: CalendarItemUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    reminder = await db.get(Reminder, item_id)
    if not reminder or reminder.user_id != user.id or reminder.category != "PERSONAL":
        raise AppError(404, "calendar_item_not_found", "개인 일정을 찾을 수 없습니다.")
    values = data.model_dump(exclude_unset=True)
    if "starts_at" in values:
        starts_at = values.pop("starts_at")
        if starts_at is None:
            raise AppError(422, "starts_at_required", "일정 시간이 필요합니다.")
        reminder.remind_at = starts_at
    if values.get("title") is None and "title" in values:
        raise AppError(422, "title_required", "일정 제목이 필요합니다.")
    if values.get("color") is None and "color" in values:
        raise AppError(422, "color_required", "일정 색상이 필요합니다.")
    if values.get("color"):
        values["color"] = validate_calendar_color(values["color"])
    for key, value in values.items():
        setattr(reminder, key, value)
    await db.commit()
    return CalendarItemOut(
        id=str(reminder.id),
        source="PERSONAL",
        title=reminder.title,
        description=reminder.content,
        starts_at=reminder.remind_at,
        color=reminder.color,
        editable=True,
    )


@router.delete("/items/{item_id}", status_code=204)
async def delete_calendar_item(
    item_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    reminder = await db.get(Reminder, item_id)
    if not reminder or reminder.user_id != user.id or reminder.category != "PERSONAL":
        raise AppError(404, "calendar_item_not_found", "개인 일정을 찾을 수 없습니다.")
    await db.delete(reminder)
    await db.commit()
