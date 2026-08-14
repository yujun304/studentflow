import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, current_user, require_roles
from app.models.entities import Role, Team, TeamMember, User
from app.schemas import TeamIn, TeamOut
from app.services.team_calendar import (
    current_term_users,
    replace_team_members,
    sync_team_reminders,
    team_member_ids,
)

router = APIRouter(prefix="/teams", tags=["teams"], dependencies=[Depends(csrf_protect)])
manager = require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)


def can_manage(team: Team, user: User) -> bool:
    return user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER} or (
        user.role == Role.DEPARTMENT_HEAD and team.created_by == user.id
    )


def team_out(team: Team, member_ids: set[uuid.UUID]) -> TeamOut:
    return TeamOut.model_validate(team).model_copy(update={"member_ids": list(member_ids)})


@router.get("", response_model=list[TeamOut])
async def list_teams(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    member_team_ids = select(TeamMember.team_id).where(TeamMember.user_id == user.id)
    statement = select(Team).where(Team.term_id == user.term_id, Team.approved_at.is_not(None))
    if user.role == Role.MEMBER:
        statement = statement.where(Team.id.in_(member_team_ids))
    elif user.role == Role.DEPARTMENT_HEAD:
        statement = statement.where(or_(Team.created_by == user.id, Team.id.in_(member_team_ids)))
    teams = list((await db.scalars(statement.order_by(Team.schedule_at, Team.name))).all())
    members = await team_member_ids(db, [team.id for team in teams])
    return [team_out(team, members[team.id]) for team in teams]


@router.post("", response_model=TeamOut, status_code=201)
async def create_team(
    data: TeamIn, actor: User = Depends(manager), db: AsyncSession = Depends(get_db)
):
    member_ids = set(data.member_ids)
    if data.leader_id:
        member_ids.add(data.leader_id)
    await current_term_users(db, actor.term_id, member_ids)
    team = Team(
        **data.model_dump(exclude={"member_ids"}),
        term_id=actor.term_id,
        created_by=actor.id,
        approved_at=datetime.now(UTC),
    )
    db.add(team)
    await db.flush()
    await replace_team_members(db, team, member_ids)
    await sync_team_reminders(db, team, member_ids)
    await db.commit()
    await db.refresh(team)
    return team_out(team, member_ids)


@router.patch("/{team_id}", response_model=TeamOut)
async def update_team(
    team_id: uuid.UUID,
    data: TeamIn,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    team = await db.get(Team, team_id)
    if not team or team.term_id != actor.term_id:
        raise AppError(404, "team_not_found", "조 편성을 찾을 수 없습니다.")
    if not can_manage(team, actor):
        raise AppError(403, "team_edit_forbidden", "직접 생성한 조 편성만 수정할 수 있습니다.")
    member_ids = set(data.member_ids)
    if data.leader_id:
        member_ids.add(data.leader_id)
    await current_term_users(db, actor.term_id, member_ids)
    for key, value in data.model_dump(exclude={"member_ids", "task_id"}).items():
        setattr(team, key, value)
    await replace_team_members(db, team, member_ids)
    await sync_team_reminders(db, team, member_ids)
    await db.commit()
    return team_out(team, member_ids)
