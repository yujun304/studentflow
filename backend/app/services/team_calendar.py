import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.entities import Event, EventParticipant, Reminder, Team, TeamMember, User

TEAM_REMINDER_COLOR = "#059669"
ALLOWED_CALENDAR_COLORS = {
    "#356ae6",
    "#7c3aed",
    "#db2777",
    "#d97706",
    "#059669",
    "#0891b2",
}


async def current_term_users(
    db: AsyncSession, term_id: uuid.UUID, user_ids: set[uuid.UUID]
) -> dict[uuid.UUID, User]:
    if not user_ids:
        return {}
    users = (
        await db.scalars(
            select(User).where(
                User.id.in_(user_ids), User.term_id == term_id, User.is_active.is_(True)
            )
        )
    ).all()
    result = {user.id: user for user in users}
    if set(result) != user_ids:
        raise AppError(
            422, "invalid_team_members", "현재 기수의 활성 사용자만 조에 포함할 수 있습니다."
        )
    return result


async def team_member_ids(
    db: AsyncSession, team_ids: list[uuid.UUID]
) -> dict[uuid.UUID, set[uuid.UUID]]:
    result = {team_id: set() for team_id in team_ids}
    if not team_ids:
        return result
    rows = (
        await db.execute(
            select(TeamMember.team_id, TeamMember.user_id).where(TeamMember.team_id.in_(team_ids))
        )
    ).all()
    for team_id, user_id in rows:
        result[team_id].add(user_id)
    return result


async def replace_team_members(db: AsyncSession, team: Team, member_ids: set[uuid.UUID]) -> None:
    await db.execute(delete(TeamMember).where(TeamMember.team_id == team.id))
    db.add_all([TeamMember(team_id=team.id, user_id=user_id) for user_id in member_ids])


async def sync_team_reminders(db: AsyncSession, team: Team, member_ids: set[uuid.UUID]) -> None:
    await db.execute(
        delete(Reminder).where(Reminder.source_type == "TEAM", Reminder.source_id == team.id)
    )
    await db.flush()
    if not team.schedule_at:
        return
    event = await db.get(Event, team.event_id) if team.event_id else None
    detail_parts = [
        f"행사: {event.title}" if event else None,
        f"행사 설명: {event.description}" if event and event.description else None,
        f"집합 위치: {event.location}" if event and event.location else None,
        f"역할: {team.role_description}" if team.role_description else None,
        f"준비 사항: {team.description}" if team.description else None,
    ]
    detail = "\n".join(value for value in detail_parts if value)
    db.add_all(
        [
            Reminder(
                user_id=user_id,
                term_id=team.term_id,
                title=f"[조 일정] {team.name}",
                content=detail or None,
                remind_at=team.schedule_at,
                category="TEAM",
                color=TEAM_REMINDER_COLOR,
                source_type="TEAM",
                source_id=team.id,
            )
            for user_id in member_ids
        ]
    )


async def approve_submission_teams(db: AsyncSession, submission_id: uuid.UUID) -> list[Team]:
    teams = list(
        (
            await db.scalars(
                select(Team).where(Team.submission_id == submission_id).order_by(Team.name)
            )
        ).all()
    )
    members = await team_member_ids(db, [team.id for team in teams])
    approved_at = datetime.now(UTC)
    for team in teams:
        team.approved_at = approved_at
        await sync_team_reminders(db, team, members[team.id])
        if team.event_id and members[team.id]:
            existing_participants = set(
                (
                    await db.scalars(
                        select(EventParticipant.user_id).where(
                            EventParticipant.event_id == team.event_id,
                            EventParticipant.user_id.in_(members[team.id]),
                        )
                    )
                ).all()
            )
            db.add_all(
                EventParticipant(event_id=team.event_id, user_id=user_id)
                for user_id in members[team.id] - existing_participants
            )
    return teams


def validate_calendar_color(color: str) -> str:
    if color not in ALLOWED_CALENDAR_COLORS:
        raise AppError(422, "invalid_calendar_color", "지원하는 일정 색상을 선택해 주세요.")
    return color
