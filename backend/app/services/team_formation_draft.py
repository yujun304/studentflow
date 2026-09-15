from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import EventParticipant, Role, Task, User


def _date_label(value: str) -> str:
    _, month, day = value.split("-")
    return f"{int(month)}월 {int(day)}일"


async def build_team_formation_draft(db: AsyncSession, task: Task) -> list[dict]:
    """Create a deterministic, editable draft without approving any teams."""
    if not task.event_id or not task.operation_dates:
        return []

    people = list(
        (
            await db.scalars(
                select(User)
                .join(EventParticipant, EventParticipant.user_id == User.id)
                .where(
                    EventParticipant.event_id == task.event_id,
                    User.term_id == task.term_id,
                    User.is_active.is_(True),
                    User.role != Role.TEACHER,
                )
                .order_by(User.grade.asc().nulls_last(), User.name.asc(), User.id.asc())
            )
        ).all()
    )
    if not people:
        return []

    dates = sorted(set(task.operation_dates))
    requirements = task.team_requirements or []
    draft: list[dict] = []
    for date_index, operation_date in enumerate(dates):
        day_requirements = [
            item
            for item in requirements
            if "operation_dates" not in item
            or operation_date in (item.get("operation_dates") or [])
        ]
        if not day_requirements:
            day_requirements = [
                {
                    "name": f"{index + 1}조",
                    "people_count": task.people_per_team or 1,
                    "role_description": task.team_role_description or "",
                }
                for index in range(task.teams_per_day or 1)
            ]

        rotated = people[date_index % len(people) :] + people[: date_index % len(people)]
        person_index = 0
        for requirement in day_requirements:
            capacity = int(requirement.get("people_count") or 1)
            members = rotated[person_index : person_index + capacity]
            person_index += capacity
            base_name = str(requirement.get("name") or f"{len(draft) + 1}조").strip()
            name = f"{_date_label(operation_date)} {base_name}" if len(dates) > 1 else base_name
            start_time = requirement.get("start_time") or "09:00"
            draft.append(
                {
                    "name": name,
                    "schedule_at": f"{operation_date}T{start_time}",
                    "leader_id": str(members[0].id) if members else None,
                    "member_ids": [str(person.id) for person in members],
                    "required_people": capacity,
                    "role_description": requirement.get("role_description") or "",
                }
            )
    return draft
