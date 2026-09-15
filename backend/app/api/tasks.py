import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, current_user, require_roles
from app.core.storage import storage
from app.models.entities import (
    DecisionCard,
    DecisionStatus,
    Event,
    Notification,
    Role,
    StoredFile,
    Submission,
    SubmissionStatus,
    SubmissionVersion,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    Team,
    TeamMember,
    User,
)
from app.schemas import (
    StatusIn,
    SubmissionFileOut,
    SubmissionIn,
    TaskIn,
    TaskOut,
    TaskSubmissionOut,
    TaskUpdate,
    TeamFormationIn,
)
from app.services.notifications import create_notifications
from app.services.team_calendar import (
    approve_submission_teams,
    current_term_users,
    replace_team_members,
)

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(csrf_protect)])
manager = require_roles(Role.DEPARTMENT_HEAD, Role.EXECUTIVE_BOARD, Role.TEACHER)


async def assigned(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return bool(
        await db.scalar(
            select(TaskAssignee.id).where(
                TaskAssignee.task_id == task_id, TaskAssignee.user_id == user_id
            )
        )
    )


def can_edit_task(task: Task, user: User) -> bool:
    return user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER} or (
        user.role == Role.DEPARTMENT_HEAD and task.created_by == user.id
    )


def task_out(task: Task, user: User, assignee_ids: set[uuid.UUID]) -> TaskOut:
    return TaskOut.model_validate(task).model_copy(
        update={
            "assigned_to_me": user.id in assignee_ids,
            "assignee_ids": list(assignee_ids) if can_edit_task(task, user) else [],
            "can_edit": can_edit_task(task, user),
        }
    )


async def task_assignees(
    db: AsyncSession, task_ids: list[uuid.UUID]
) -> dict[uuid.UUID, set[uuid.UUID]]:
    result: dict[uuid.UUID, set[uuid.UUID]] = {task_id: set() for task_id in task_ids}
    if not task_ids:
        return result
    rows = (
        await db.execute(
            select(TaskAssignee.task_id, TaskAssignee.user_id).where(
                TaskAssignee.task_id.in_(task_ids)
            )
        )
    ).all()
    for task_id, user_id in rows:
        result[task_id].add(user_id)
    return result


async def validate_assignees(
    db: AsyncSession, actor: User, assignee_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    requested = set(assignee_ids)
    if not requested:
        return requested
    statement = select(User.id).where(
        User.id.in_(requested), User.term_id == actor.term_id, User.is_active.is_(True)
    )
    if actor.role == Role.DEPARTMENT_HEAD:
        statement = statement.where(User.department_id == actor.department_id)
    allowed = set((await db.scalars(statement)).all())
    if allowed != requested:
        raise AppError(
            403, "assignee_scope", "현재 기수의 관리 가능한 사용자만 배정할 수 있습니다."
        )
    return requested


@router.get("", response_model=list[TaskOut])
async def list_tasks(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Task).where(Task.term_id == user.term_id)
    if user.role == Role.MEMBER:
        stmt = stmt.where(
            Task.id.in_(select(TaskAssignee.task_id).where(TaskAssignee.user_id == user.id))
        )
    elif user.role == Role.DEPARTMENT_HEAD:
        department_users = select(User.id).where(
            User.department_id == user.department_id, User.term_id == user.term_id
        )
        department_tasks = select(TaskAssignee.task_id).where(
            TaskAssignee.user_id.in_(department_users)
        )
        stmt = stmt.where((Task.created_by == user.id) | Task.id.in_(department_tasks))
    tasks = list((await db.scalars(stmt.order_by(Task.due_at.asc().nullslast()))).all())
    assignees = await task_assignees(db, [task.id for task in tasks])
    return [task_out(task, user, assignees[task.id]) for task in tasks]


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    data: TaskIn, actor: User = Depends(manager), db: AsyncSession = Depends(get_db)
):
    assignee_ids = await validate_assignees(db, actor, data.assignee_ids)
    task = Task(
        **data.model_dump(exclude={"assignee_ids"}), term_id=actor.term_id, created_by=actor.id
    )
    db.add(task)
    await db.flush()
    db.add_all([TaskAssignee(task_id=task.id, user_id=value) for value in assignee_ids])
    await db.commit()
    await db.refresh(task)
    recipients = assignee_ids - {actor.id}
    if recipients:
        await create_notifications(
            db,
            recipients,
            notification_type="TASK_ASSIGNED",
            title="새 업무가 배정되었습니다",
            content=task.title,
            target_type="task",
            target_id=task.id,
        )
    return task_out(task, actor, assignee_ids)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task or task.term_id != actor.term_id:
        raise AppError(404, "task_not_found", "업무를 찾을 수 없습니다.")
    if not can_edit_task(task, actor):
        raise AppError(403, "task_edit_forbidden", "직접 등록한 업무만 수정할 수 있습니다.")
    values = data.model_dump(exclude_unset=True, exclude={"assignee_ids"})
    if values.get("title") is None and "title" in values:
        raise AppError(422, "title_required", "업무 제목이 필요합니다.")
    if values.get("type") is None and "type" in values:
        raise AppError(422, "type_required", "업무 유형이 필요합니다.")
    if data.type is not None and data.type != task.type:
        has_submission = await db.scalar(select(Submission.id).where(Submission.task_id == task.id))
        if has_submission:
            raise AppError(
                409, "submission_exists", "제출 내역이 있는 업무는 유형을 바꿀 수 없습니다."
            )
    for key, value in values.items():
        setattr(task, key, value)
    previous_assignee_ids = (await task_assignees(db, [task.id]))[task.id]
    assignee_ids = previous_assignee_ids
    if data.assignee_ids is not None:
        assignee_ids = await validate_assignees(db, actor, data.assignee_ids)
        await db.execute(delete(TaskAssignee).where(TaskAssignee.task_id == task.id))
        db.add_all([TaskAssignee(task_id=task.id, user_id=value) for value in assignee_ids])
    await db.commit()
    new_recipients = assignee_ids - previous_assignee_ids - {actor.id}
    if new_recipients:
        await create_notifications(
            db,
            new_recipients,
            notification_type="TASK_ASSIGNED",
            title="새 업무가 배정되었습니다",
            content=task.title,
            target_type="task",
            target_id=task.id,
        )
    return task_out(task, actor, assignee_ids)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await db.get(Task, task_id)
    if not task or task.term_id != actor.term_id:
        raise AppError(404, "task_not_found", "업무를 찾을 수 없습니다.")
    if not can_edit_task(task, actor):
        raise AppError(403, "task_delete_forbidden", "직접 등록한 업무만 삭제할 수 있습니다.")
    has_submission = await db.scalar(select(Submission.id).where(Submission.task_id == task.id))
    has_team = await db.scalar(select(Team.id).where(Team.task_id == task.id))
    if has_submission or has_team:
        raise AppError(
            409,
            "task_has_records",
            "제출물이나 조 편성 기록이 있는 업무는 삭제할 수 없습니다.",
        )
    await db.delete(task)
    await db.commit()


@router.patch("/{task_id}/status", response_model=TaskOut)
async def change_status(
    task_id: uuid.UUID,
    data: StatusIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if (
        not task
        or task.term_id != user.term_id
        or (user.role == Role.MEMBER and not await assigned(db, task_id, user.id))
    ):
        raise AppError(404, "task_not_found", "업무를 찾을 수 없습니다.")
    if data.status in {TaskStatus.REVIEW, TaskStatus.REJECTED}:
        raise AppError(422, "status_removed", "검토와 반려 상태는 더 이상 사용하지 않습니다.")
    if data.status == TaskStatus.DONE and task.type in {
        TaskType.SUBMISSION,
        TaskType.TEAM_FORMATION,
    }:
        raise AppError(403, "submit_to_complete", "결과를 제출하면 업무가 바로 완료됩니다.")
    task.status = data.status
    decision = await db.scalar(select(DecisionCard).where(DecisionCard.task_id == task.id))
    if decision:
        decision.status = DecisionStatus.DONE if data.status == TaskStatus.DONE else DecisionStatus.OPEN
        decision.completed_at = datetime.now(UTC) if data.status == TaskStatus.DONE else None
    await db.commit()
    assignee_ids = (await task_assignees(db, [task.id]))[task.id]
    return task_out(task, user, assignee_ids)


@router.post("/{task_id}/team-formation", status_code=201)
async def submit_team_formation(
    task_id: uuid.UUID,
    data: TeamFormationIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task or task.type != TaskType.TEAM_FORMATION or not await assigned(db, task_id, user.id):
        raise AppError(403, "not_assigned", "이 조 편성 업무를 제출할 수 없습니다.")
    names = [team.name.strip() for team in data.teams]
    if len(set(names)) != len(names):
        raise AppError(422, "duplicate_team_name", "조 이름은 서로 달라야 합니다.")
    all_member_ids: set[uuid.UUID] = set()
    repeatable_member_ids = set(data.repeatable_member_ids)
    normalized_members: list[set[uuid.UUID]] = []
    for draft in data.teams:
        member_ids = set(draft.member_ids)
        if draft.leader_id:
            member_ids.add(draft.leader_id)
        duplicated_ids = all_member_ids & member_ids
        if duplicated_ids - repeatable_member_ids:
            raise AppError(
                422,
                "duplicate_team_member",
                "중복 허용으로 지정한 사용자만 여러 조에 배정할 수 있습니다.",
            )
        all_member_ids.update(member_ids)
        normalized_members.append(member_ids)
    if task.team_requirements and task.operation_days:
        teams_by_day: dict[str, int] = {}
        for draft, member_ids in zip(data.teams, normalized_members, strict=True):
            if not draft.schedule_at:
                raise AppError(422, "team_schedule_required", "모든 조의 활동 날짜를 정해 주세요.")
            day_key = draft.schedule_at.astimezone(ZoneInfo(settings.default_timezone)).date().isoformat()
            teams_by_day[day_key] = teams_by_day.get(day_key, 0) + 1
            requirement = next(
                (
                    item
                    for item in task.team_requirements
                    if (draft.name == item["name"] or draft.name.endswith(f" {item['name']}"))
                    and (
                        "operation_dates" not in item
                        or day_key in (item.get("operation_dates") or [])
                    )
                ),
                None,
            )
            if not requirement:
                raise AppError(
                    422,
                    "unknown_team",
                    f"{draft.name}은 해당 날짜의 기획서에 없는 조입니다.",
                )
            if len(member_ids) != requirement["people_count"]:
                raise AppError(
                    422,
                    "invalid_team_size",
                    f"{requirement['name']}에 {requirement['people_count']}명을 배정해 주세요.",
                )
            if (draft.role_description or "").strip() != requirement["role_description"].strip():
                raise AppError(422, "invalid_team_role", "기획서에 적힌 조 역할은 변경할 수 없습니다.")
        expected_by_day = {
            day: sum(
                1
                for item in task.team_requirements
                if "operation_dates" not in item
                or day in (item.get("operation_dates") or [])
            )
            for day in (task.operation_dates or teams_by_day)
        }
        if teams_by_day != expected_by_day:
            raise AppError(
                422,
                "invalid_team_schedule",
                "기획서에서 날짜별로 선택한 조를 모두 편성해 주세요.",
            )
        if task.operation_dates and set(teams_by_day) != set(task.operation_dates):
            raise AppError(422, "invalid_operation_dates", "기획서에서 선택한 날짜에 맞춰 편성해 주세요.")
    await current_term_users(db, task.term_id, all_member_ids | repeatable_member_ids)
    submission = await db.scalar(
        select(Submission).where(Submission.task_id == task.id, Submission.submitted_by == user.id)
    )
    if not submission:
        submission = Submission(
            task_id=task.id, submitted_by=user.id, status=SubmissionStatus.SUBMITTED
        )
        db.add(submission)
        await db.flush()
    existing_teams = list(
        (await db.scalars(select(Team).where(Team.submission_id == submission.id))).all()
    )
    if any(team.approved_at for team in existing_teams):
        raise AppError(409, "team_already_approved", "승인된 조 편성은 다시 제출할 수 없습니다.")
    if existing_teams:
        existing_ids = [team.id for team in existing_teams]
        await db.execute(delete(TeamMember).where(TeamMember.team_id.in_(existing_ids)))
        await db.execute(delete(Team).where(Team.id.in_(existing_ids)))
    version_number = (
        await db.scalar(
            select(func.max(SubmissionVersion.version)).where(
                SubmissionVersion.submission_id == submission.id
            )
        )
        or 0
    ) + 1
    version = SubmissionVersion(
        submission_id=submission.id, version=version_number, content=data.content
    )
    db.add(version)
    for draft, member_ids in zip(data.teams, normalized_members, strict=True):
        team = Team(
            term_id=task.term_id,
            event_id=task.event_id,
            task_id=task.id,
            submission_id=submission.id,
            created_by=task.created_by,
            name=draft.name.strip(),
            description=draft.description,
            role_description=draft.role_description,
            leader_id=draft.leader_id,
            schedule_at=draft.schedule_at,
        )
        db.add(team)
        await db.flush()
        await replace_team_members(db, team, member_ids)
    submission.status = SubmissionStatus.APPROVED
    submission.rejection_reason = None
    task.status = TaskStatus.DONE
    approved_teams = await approve_submission_teams(db, submission.id)
    approved_members = {
        team.id: set(
            (
                await db.scalars(
                    select(TeamMember.user_id).where(TeamMember.team_id == team.id)
                )
            ).all()
        )
        for team in approved_teams
    }
    event = await db.get(Event, task.event_id) if task.event_id else None
    for team in approved_teams:
        schedule_text = (
            team.schedule_at.astimezone(ZoneInfo(settings.default_timezone)).strftime("%Y-%m-%d %H:%M")
            if team.schedule_at
            else "일정 미정"
        )
        role_text = team.role_description or "공동 활동"
        detail_parts = [
            f"행사: {event.title}" if event else None,
            f"행사 설명: {event.description}" if event and event.description else None,
            f"시간: {schedule_text}",
            f"집합 위치: {event.location}" if event and event.location else None,
            f"조: {team.name}",
            f"역할: {role_text}",
            f"준비 사항: {team.description}" if team.description else None,
        ]
        db.add_all(
            Notification(
                user_id=member_id,
                type="TEAM_ASSIGNED",
                title=f"{team.name}에 배정되었습니다",
                content="\n".join(value for value in detail_parts if value),
                target_type="task",
                target_id=task.id,
            )
            for member_id in approved_members[team.id]
        )
    await db.commit()
    await db.refresh(version)
    return version


@router.post("/{task_id}/submissions", status_code=201)
async def submit(
    task_id: uuid.UUID,
    data: SubmissionIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task or task.type != TaskType.SUBMISSION or not await assigned(db, task_id, user.id):
        raise AppError(403, "not_assigned", "이 업무를 제출할 수 없습니다.")
    submission = await db.scalar(
        select(Submission).where(Submission.task_id == task_id, Submission.submitted_by == user.id)
    )
    if not submission:
        submission = Submission(
            task_id=task_id, submitted_by=user.id, status=SubmissionStatus.SUBMITTED
        )
        db.add(submission)
        await db.flush()
    version_number = (
        await db.scalar(
            select(func.max(SubmissionVersion.version)).where(
                SubmissionVersion.submission_id == submission.id
            )
        )
        or 0
    ) + 1
    version = SubmissionVersion(
        submission_id=submission.id, version=version_number, content=data.content
    )
    db.add(version)
    submission.status = SubmissionStatus.SUBMITTED
    submission.rejection_reason = None
    task.status = TaskStatus.IN_PROGRESS
    decision = await db.scalar(select(DecisionCard).where(DecisionCard.task_id == task.id))
    if decision:
        decision.status = DecisionStatus.OPEN
        decision.completed_at = None
    await db.commit()
    await db.refresh(version)
    return version


@router.get("/{task_id}/submissions", response_model=list[TaskSubmissionOut])
async def list_task_submissions(
    task_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    allowed = task and task.term_id == user.term_id and (
        user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER}
        or task.created_by == user.id
        or await assigned(db, task.id, user.id)
    )
    if not allowed:
        raise AppError(404, "task_not_found", "업무를 찾을 수 없습니다.")

    submissions = list(
        (
            await db.scalars(
                select(Submission)
                .where(Submission.task_id == task.id)
                .order_by(Submission.created_at.desc())
            )
        ).all()
    )
    result: list[TaskSubmissionOut] = []
    for submission in submissions:
        version = await db.scalar(
            select(SubmissionVersion)
            .where(SubmissionVersion.submission_id == submission.id)
            .order_by(SubmissionVersion.version.desc())
            .limit(1)
        )
        if not version:
            continue
        submitter = await db.get(User, submission.submitted_by)
        files = list(
            (
                await db.scalars(
                    select(StoredFile)
                    .where(StoredFile.submission_version_id == version.id)
                    .order_by(StoredFile.created_at, StoredFile.id)
                )
            ).all()
        )
        result.append(
            TaskSubmissionOut(
                id=submission.id,
                submitted_by=submission.submitted_by,
                submitter_name=submitter.name if submitter else "알 수 없음",
                version=version.version,
                content=version.content,
                created_at=version.created_at,
                files=[
                    SubmissionFileOut(
                        id=item.id,
                        original_name=item.original_name,
                        mime_type=item.mime_type,
                        size=item.size,
                        created_at=item.created_at,
                        download_path=f"/api/v1/tasks/files/{item.id}",
                    )
                    for item in files
                ],
            )
        )
    return result


@router.post("/submission-versions/{version_id}/files", status_code=201)
async def upload_file(
    version_id: uuid.UUID,
    upload: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    version = await db.get(SubmissionVersion, version_id)
    submission = version and await db.get(Submission, version.submission_id)
    latest_version = submission and await db.scalar(
        select(func.max(SubmissionVersion.version)).where(
            SubmissionVersion.submission_id == submission.id
        )
    )
    if (
        not submission
        or submission.submitted_by != user.id
        or submission.status not in {SubmissionStatus.SUBMITTED, SubmissionStatus.APPROVED}
        or version.version != latest_version
    ):
        raise AppError(403, "file_forbidden", "이 제출물에 파일을 추가할 수 없습니다.")
    key, size = await storage.save(upload)
    item = StoredFile(
        submission_version_id=version_id,
        original_name=upload.filename or "file",
        storage_key=key,
        mime_type=upload.content_type or "application/octet-stream",
        size=size,
        uploaded_by=user.id,
    )
    db.add(item)
    task = await db.get(Task, submission.task_id)
    submission.status = SubmissionStatus.APPROVED
    submission.rejection_reason = None
    if task:
        task.status = TaskStatus.DONE
        decision = await db.scalar(select(DecisionCard).where(DecisionCard.task_id == task.id))
        if decision:
            decision.status = DecisionStatus.DONE
            decision.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(item)
    if task and task.event_id:
        teacher_ids = set(
            (
                await db.scalars(
                    select(User.id).where(
                        User.term_id == task.term_id,
                        User.role == Role.TEACHER,
                        User.is_active.is_(True),
                    )
                )
            ).all()
        )
        if teacher_ids:
            await create_notifications(
                db,
                teacher_ids,
                notification_type="POSTER_SUBMITTED",
                title="행사 포스터가 제출되었습니다",
                content=f"{user.name}님이 {task.title} 파일을 제출했습니다.",
                target_type="task",
                target_id=task.id,
            )
    return item


@router.get("/files/{file_id}")
async def download(
    file_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    item = await db.get(StoredFile, file_id)
    version = item and await db.get(SubmissionVersion, item.submission_version_id)
    submission = version and await db.get(Submission, version.submission_id)
    task = submission and await db.get(Task, submission.task_id)
    allowed = (
        task
        and task.term_id == user.term_id
        and (
            user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER}
            or submission.submitted_by == user.id
            or task.created_by == user.id
            or await assigned(db, task.id, user.id)
        )
    )
    if not allowed:
        raise AppError(404, "file_not_found", "파일을 찾을 수 없습니다.")
    return FileResponse(
        storage.path(item.storage_key), filename=item.original_name, media_type=item.mime_type
    )
