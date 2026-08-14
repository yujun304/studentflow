import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import csrf_protect, current_user, require_roles
from app.core.storage import storage
from app.models.entities import (
    DecisionCard,
    DecisionStatus,
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
    ReviewIn,
    StatusIn,
    SubmissionFileOut,
    SubmissionIn,
    SubmissionReviewOut,
    TeamFormationIn,
    TeamReviewOut,
    TaskIn,
    TaskOut,
    TaskUpdate,
)
from app.services.team_calendar import (
    approve_submission_teams,
    current_term_users,
    replace_team_members,
    team_member_ids,
)
from app.services.notifications import create_notifications

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
    if (
        user.role == Role.MEMBER
        and data.status in {TaskStatus.REVIEW, TaskStatus.DONE, TaskStatus.REJECTED}
        and task.type in {TaskType.SUBMISSION, TaskType.TEAM_FORMATION}
    ):
        raise AppError(403, "review_required", "제출 업무의 검토 상태는 관리자가 변경합니다.")
    task.status = data.status
    decision = await db.scalar(select(DecisionCard).where(DecisionCard.task_id == task.id))
    if decision:
        decision.status = DecisionStatus.DONE if data.status == TaskStatus.DONE else DecisionStatus.OPEN
        decision.completed_at = datetime.now(UTC) if data.status == TaskStatus.DONE else None
    await db.commit()
    assignee_ids = (await task_assignees(db, [task.id]))[task.id]
    return task_out(task, user, assignee_ids)


@router.get("/submissions/pending", response_model=list[SubmissionReviewOut])
async def pending_submissions(actor: User = Depends(manager), db: AsyncSession = Depends(get_db)):
    latest_versions = (
        select(
            SubmissionVersion.submission_id,
            func.max(SubmissionVersion.version).label("latest_version"),
        )
        .group_by(SubmissionVersion.submission_id)
        .subquery()
    )
    statement = (
        select(Submission, Task, User, SubmissionVersion)
        .join(Task, Task.id == Submission.task_id)
        .join(User, User.id == Submission.submitted_by)
        .join(latest_versions, latest_versions.c.submission_id == Submission.id)
        .join(
            SubmissionVersion,
            and_(
                SubmissionVersion.submission_id == Submission.id,
                SubmissionVersion.version == latest_versions.c.latest_version,
            ),
        )
        .where(
            Submission.status == SubmissionStatus.SUBMITTED,
            Task.term_id == actor.term_id,
        )
    )
    if actor.role == Role.DEPARTMENT_HEAD:
        statement = statement.where(Task.created_by == actor.id)
    rows = (await db.execute(statement.order_by(Submission.updated_at))).all()
    version_ids = [version.id for _, _, _, version in rows]
    files_by_version: dict[uuid.UUID, list[SubmissionFileOut]] = {}
    if version_ids:
        files = (
            await db.scalars(
                select(StoredFile)
                .where(StoredFile.submission_version_id.in_(version_ids))
                .order_by(StoredFile.created_at)
            )
        ).all()
        for item in files:
            files_by_version.setdefault(item.submission_version_id, []).append(
                SubmissionFileOut.model_validate(item)
            )
    submission_ids = [submission.id for submission, _, _, _ in rows]
    draft_teams = (
        list(
            (
                await db.scalars(
                    select(Team).where(Team.submission_id.in_(submission_ids)).order_by(Team.name)
                )
            ).all()
        )
        if submission_ids
        else []
    )
    members = await team_member_ids(db, [team.id for team in draft_teams])
    related_user_ids = {user_id for values in members.values() for user_id in values} | {
        team.leader_id for team in draft_teams if team.leader_id
    }
    related_users = {
        related_user.id: related_user
        for related_user in (
            await db.scalars(select(User).where(User.id.in_(related_user_ids)))
        ).all()
    }
    teams_by_submission: dict[uuid.UUID, list[TeamReviewOut]] = {}
    for team in draft_teams:
        if not team.schedule_at:
            continue
        member_ids = members[team.id]
        teams_by_submission.setdefault(team.submission_id, []).append(
            TeamReviewOut(
                id=team.id,
                name=team.name,
                description=team.description,
                role_description=team.role_description,
                leader_id=team.leader_id,
                leader_name=(
                    related_users[team.leader_id].name if team.leader_id in related_users else None
                ),
                member_ids=list(member_ids),
                member_names=sorted(
                    related_users[user_id].name
                    for user_id in member_ids
                    if user_id in related_users
                ),
                schedule_at=team.schedule_at,
            )
        )
    return [
        SubmissionReviewOut(
            id=submission.id,
            task_id=task.id,
            task_title=task.title,
            submitted_by=submitter.id,
            submitted_by_name=submitter.name,
            status=submission.status,
            version_id=version.id,
            version=version.version,
            content=version.content,
            submitted_at=version.created_at,
            files=files_by_version.get(version.id, []),
            teams=teams_by_submission.get(submission.id, []),
        )
        for submission, task, submitter, version in rows
    ]


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
    normalized_members: list[set[uuid.UUID]] = []
    for draft in data.teams:
        member_ids = set(draft.member_ids)
        if draft.leader_id:
            member_ids.add(draft.leader_id)
        if all_member_ids & member_ids:
            raise AppError(
                422, "duplicate_team_member", "한 사용자를 여러 조에 중복 배정할 수 없습니다."
            )
        all_member_ids.update(member_ids)
        normalized_members.append(member_ids)
    await current_term_users(db, task.term_id, all_member_ids)
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
    submission.status = SubmissionStatus.SUBMITTED
    submission.rejection_reason = None
    task.status = TaskStatus.REVIEW
    await db.commit()
    await db.refresh(version)
    if task.created_by != user.id:
        await create_notifications(
            db,
            {task.created_by},
            notification_type="SUBMISSION_RECEIVED",
            title="검토할 제출물이 도착했습니다",
            content=task.title,
            target_type="submission",
            target_id=submission.id,
        )
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
    task.status = TaskStatus.REVIEW
    await db.commit()
    await db.refresh(version)
    if task.created_by != user.id:
        await create_notifications(
            db,
            {task.created_by},
            notification_type="SUBMISSION_RECEIVED",
            title="검토할 제출물이 도착했습니다",
            content=task.title,
            target_type="submission",
            target_id=submission.id,
        )
    return version


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
        or submission.status != SubmissionStatus.SUBMITTED
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
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/submissions/{submission_id}/review")
async def review(
    submission_id: uuid.UUID,
    data: ReviewIn,
    actor: User = Depends(manager),
    db: AsyncSession = Depends(get_db),
):
    if data.status not in {SubmissionStatus.APPROVED, SubmissionStatus.REJECTED}:
        raise AppError(422, "invalid_review", "승인 또는 반려 상태를 선택해 주세요.")
    if data.status == SubmissionStatus.REJECTED and not data.reason:
        raise AppError(422, "reason_required", "반려 사유가 필요합니다.")
    submission = await db.get(Submission, submission_id)
    if not submission:
        raise AppError(404, "submission_not_found", "제출물을 찾을 수 없습니다.")
    task = await db.get(Task, submission.task_id)
    if actor.role == Role.DEPARTMENT_HEAD and task.created_by != actor.id:
        raise AppError(403, "department_scope", "직접 생성한 업무만 검토할 수 있습니다.")
    submission.status = data.status
    submission.rejection_reason = data.reason
    submission.reviewed_by = actor.id
    task.status = (
        TaskStatus.DONE if data.status == SubmissionStatus.APPROVED else TaskStatus.REJECTED
    )
    decision = await db.scalar(select(DecisionCard).where(DecisionCard.task_id == task.id))
    if decision:
        decision.status = (
            DecisionStatus.DONE
            if data.status == SubmissionStatus.APPROVED
            else DecisionStatus.OPEN
        )
        decision.completed_at = (
            datetime.now(UTC) if data.status == SubmissionStatus.APPROVED else None
        )
    if task.type == TaskType.TEAM_FORMATION and data.status == SubmissionStatus.APPROVED:
        teams = await approve_submission_teams(db, submission.id)
        if not teams:
            raise AppError(422, "team_formation_missing", "승인할 조 편성 데이터가 없습니다.")
    await db.commit()
    await create_notifications(
        db,
        {submission.submitted_by},
        notification_type="SUBMISSION_REVIEWED",
        title="제출물 검토가 완료되었습니다",
        content=(
            f"{task.title} · 승인"
            if data.status == SubmissionStatus.APPROVED
            else f"{task.title} · 반려: {data.reason}"
        ),
        target_type="task",
        target_id=task.id,
    )
    return submission


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
