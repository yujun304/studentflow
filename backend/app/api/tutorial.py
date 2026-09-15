import uuid
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import current_user
from app.models.entities import (
    ApplicationStatus,
    CommunityPost,
    Event,
    EventParticipant,
    EventType,
    Notice,
    NoticeApplication,
    NoticeRecipient,
    NoticeType,
    Notification,
    StoredFile,
    Submission,
    SubmissionVersion,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    Team,
    TutorialWorkspace,
    User,
)
from app.schemas import TutorialStatusOut, TutorialStepOut
from app.services.notifications import create_notifications

router = APIRouter(prefix="/tutorial", tags=["tutorial"])


async def workspace_for(db: AsyncSession, user_id: uuid.UUID) -> TutorialWorkspace | None:
    return await db.scalar(
        select(TutorialWorkspace).where(TutorialWorkspace.user_id == user_id)
    )


async def build_status(
    db: AsyncSession, user: User, workspace: TutorialWorkspace | None
) -> TutorialStatusOut:
    if not workspace:
        return TutorialStatusOut(
            started=False,
            completed=user.onboarding_completed_at is not None,
            completed_count=0,
            total_count=6,
            steps=[],
        )

    proposal_done = bool(
        await db.scalar(
            select(CommunityPost.id).where(
                CommunityPost.author_id == user.id,
                CommunityPost.created_at >= workspace.created_at,
            )
        )
    )
    recipient = await db.scalar(
        select(NoticeRecipient).where(
            NoticeRecipient.notice_id == workspace.notice_id,
            NoticeRecipient.user_id == user.id,
        )
    )
    application_done = bool(
        await db.scalar(
            select(NoticeApplication.id).where(
                NoticeApplication.notice_id == workspace.notice_id,
                NoticeApplication.user_id == user.id,
                NoticeApplication.status.in_([ApplicationStatus.ACCEPTED, ApplicationStatus.WAITING]),
            )
        )
    )
    simple_done = (
        await db.scalar(select(Task.status).where(Task.id == workspace.simple_task_id))
        == TaskStatus.DONE
    )
    formation_done = bool(
        await db.scalar(select(Team.id).where(Team.task_id == workspace.formation_task_id))
    )
    submission_done = bool(
        await db.scalar(
            select(StoredFile.id)
            .join(SubmissionVersion, StoredFile.submission_version_id == SubmissionVersion.id)
            .join(Submission, SubmissionVersion.submission_id == Submission.id)
            .where(
                Submission.task_id == workspace.submission_task_id,
                Submission.submitted_by == user.id,
            )
        )
    )
    notification_done = not bool(
        await db.scalar(
            select(Notification.id).where(
                Notification.user_id == user.id,
                Notification.type == "TUTORIAL_STARTED",
                Notification.target_id == workspace.notice_id,
                Notification.read_at.is_(None),
            )
        )
    )
    steps = [
        TutorialStepOut(
            key="proposal",
            title="제안 작성하기",
            description="학교생활에서 바꾸고 싶은 점을 제안으로 등록해 의견 수렴을 시작합니다.",
            href="/proposals?create=tutorial",
            action_label="제안 작성",
            done=proposal_done,
        ),
        TutorialStepOut(
            key="notice",
            title="공지 읽고 신청하기",
            description="체험 공지를 열어 읽음 처리한 뒤 선착순 신청까지 완료합니다.",
            href=f"/announcements/{workspace.notice_id}",
            action_label="체험 공지 열기",
            done=bool(recipient and recipient.read_at) and application_done,
        ),
        TutorialStepOut(
            key="task",
            title="일반 업무 완료하기",
            description="배정된 준비 업무의 설명을 확인하고 완료 상태로 바꿉니다.",
            href=f"/tasks/{workspace.simple_task_id}",
            action_label="업무 처리",
            done=simple_done,
        ),
        TutorialStepOut(
            key="formation",
            title="조 편성 저장하기",
            description="실제 참여자와 날짜를 확인하고 편성 미리보기를 저장합니다.",
            href=f"/tasks/{workspace.formation_task_id}",
            action_label="조 편성",
            done=formation_done,
        ),
        TutorialStepOut(
            key="submission",
            title="파일 제출하기",
            description="제출 업무에 파일을 올리고 저장된 제출 이력을 확인합니다.",
            href=f"/tasks/{workspace.submission_task_id}",
            action_label="파일 제출",
            done=submission_done,
        ),
        TutorialStepOut(
            key="notification",
            title="알림 확인하기",
            description="체험 중 생성된 알림을 열어 읽음 상태로 바꿉니다.",
            href="/notifications",
            action_label="알림함 열기",
            done=notification_done,
        ),
    ]
    return TutorialStatusOut(
        started=True,
        completed=user.onboarding_completed_at is not None,
        completed_count=sum(step.done for step in steps),
        total_count=len(steps),
        steps=steps,
    )


@router.get("", response_model=TutorialStatusOut)
async def tutorial_status(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> TutorialStatusOut:
    return await build_status(db, user, await workspace_for(db, user.id))


@router.post("/start", response_model=TutorialStatusOut, status_code=201)
async def start_tutorial(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> TutorialStatusOut:
    existing = await workspace_for(db, user.id)
    if existing:
        return await build_status(db, user, existing)

    activity_date = date.today() + timedelta(days=7)
    due_at = datetime.combine(date.today() + timedelta(days=5), time(18), tzinfo=UTC)
    event = Event(
        term_id=user.term_id,
        title=f"[체험] {user.name}의 학생회 운영 연습",
        type=EventType.EVENT,
        description="신규 계정 튜토리얼에서 실제 일정·업무·조 편성 흐름을 연습하는 행사입니다.",
        location="학생회실",
        event_date=activity_date,
        starts_at=time(15),
        ends_at=time(16),
        manager_id=user.id,
        status="PLANNED",
    )
    db.add(event)
    await db.flush()
    db.add(EventParticipant(event_id=event.id, user_id=user.id))

    simple_task = Task(
        term_id=user.term_id,
        event_id=event.id,
        title="[체험] 행사 준비 확인",
        description="업무를 진행 중으로 바꾼 뒤 완료해 보세요. 댓글과 북마크도 함께 시험할 수 있습니다.",
        type=TaskType.SIMPLE,
        status=TaskStatus.TODO,
        due_at=due_at,
        created_by=user.id,
    )
    formation_task = Task(
        term_id=user.term_id,
        event_id=event.id,
        title="[체험] 행사 조 편성",
        description="참여자 1명을 운영조에 배정하고 결과를 저장해 보세요.",
        type=TaskType.TEAM_FORMATION,
        status=TaskStatus.TODO,
        due_at=due_at,
        operation_days=1,
        teams_per_day=1,
        people_per_team=1,
        team_role_description="행사 안내",
        team_requirements=[
            {"name": "운영조", "people_count": 1, "role_description": "행사 안내"}
        ],
        operation_dates=[activity_date.isoformat()],
        created_by=user.id,
    )
    submission_task = Task(
        term_id=user.term_id,
        event_id=event.id,
        title="[체험] 행사 안내 파일 제출",
        description="연습용 문서나 이미지를 한 개 올리면 제출 이력과 완료 상태가 함께 저장됩니다.",
        type=TaskType.SUBMISSION,
        status=TaskStatus.TODO,
        due_at=due_at,
        created_by=user.id,
    )
    db.add_all([simple_task, formation_task, submission_task])
    await db.flush()
    db.add_all(
        TaskAssignee(task_id=task.id, user_id=user.id)
        for task in (simple_task, formation_task, submission_task)
    )

    notice = Notice(
        term_id=user.term_id,
        title="[체험] 학생회 운영 안내 신청",
        content="공지 읽음과 선착순 신청 흐름을 확인하기 위한 개인 체험 공지입니다.",
        type=NoticeType.FIRST_COME,
        author_id=user.id,
        pinned=False,
        capacity=1,
        waiting_enabled=False,
    )
    db.add(notice)
    await db.flush()
    db.add(NoticeRecipient(notice_id=notice.id, user_id=user.id))
    workspace = TutorialWorkspace(
        user_id=user.id,
        event_id=event.id,
        simple_task_id=simple_task.id,
        formation_task_id=formation_task.id,
        submission_task_id=submission_task.id,
        notice_id=notice.id,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    await create_notifications(
        db,
        {user.id},
        notification_type="TUTORIAL_STARTED",
        title="StudentFlow 체험이 준비되었습니다",
        content="제안, 공지, 업무, 조 편성, 제출을 실제 화면에서 순서대로 진행해 보세요.",
        target_type="notice",
        target_id=notice.id,
    )
    return await build_status(db, user, workspace)


@router.post("/complete", response_model=TutorialStatusOut)
async def complete_tutorial(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> TutorialStatusOut:
    workspace = await workspace_for(db, user.id)
    status = await build_status(db, user, workspace)
    if not workspace or status.completed_count != status.total_count:
        raise AppError(409, "tutorial_incomplete", "아직 완료하지 않은 체험 단계가 있습니다.")
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.now(UTC)
        await db.commit()
    return await build_status(db, user, workspace)
