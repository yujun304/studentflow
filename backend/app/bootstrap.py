import argparse
import asyncio
from datetime import UTC, date, datetime, time, timedelta

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.core.database import SessionFactory
from app.core.security import hash_password
from app.models.entities import (
    CommunityEventPlan,
    CommunityPost,
    Department,
    Event,
    EventParticipant,
    EventType,
    Notice,
    NoticeRecipient,
    NoticeType,
    ProposalVersion,
    Role,
    Task,
    TaskAssignee,
    TaskStatus,
    TaskType,
    Term,
    User,
)

DEMO_PASSWORD = "studentflow-demo"


async def current_term(db) -> Term:
    term = await db.scalar(select(Term).where(Term.is_current.is_(True)))
    if term:
        return term
    year = date.today().year
    term = Term(
        name=f"{year}학년도 학생회",
        starts_on=date(year, 1, 1),
        ends_on=date(year, 12, 31),
        is_current=True,
    )
    db.add(term)
    await db.flush()
    return term


async def seed_demo_data() -> None:
    """기존 데이터는 건드리지 않고 실제 기능 검사에 필요한 한 묶음을 보강한다."""
    async with SessionFactory() as db:
        term = await current_term(db)
        departments: dict[str, Department] = {}
        for name in ["회장단", "기획부", "홍보부"]:
            department = await db.scalar(select(Department).where(Department.name == name))
            if not department:
                department = Department(name=name, description=f"기술 시연용 {name}")
                db.add(department)
                await db.flush()
            departments[name] = department

        account_specs = [
            ("demo-teacher@studentflow.example.com", "시연 담당 선생님", Role.TEACHER, None, None),
            ("demo-president@studentflow.example.com", "전체 총괄 임원", Role.EXECUTIVE_BOARD, "회장단", 3),
            ("demo-planning@studentflow.example.com", "기획부 부장", Role.DEPARTMENT_HEAD, "기획부", 3),
            ("demo-poster@studentflow.example.com", "포스터 담당", Role.MEMBER, "홍보부", 2),
            ("demo-member01@studentflow.example.com", "김하늘", Role.MEMBER, "기획부", 1),
            ("demo-member02@studentflow.example.com", "이서준", Role.MEMBER, "기획부", 1),
            ("demo-member03@studentflow.example.com", "박지우", Role.MEMBER, "홍보부", 2),
            ("demo-member04@studentflow.example.com", "최민서", Role.MEMBER, "홍보부", 2),
            ("demo-member05@studentflow.example.com", "정도윤", Role.MEMBER, "기획부", 3),
            ("demo-member06@studentflow.example.com", "한유나", Role.MEMBER, "홍보부", 3),
            ("demo-member07@studentflow.example.com", "윤시우", Role.MEMBER, "기획부", 1),
            ("demo-member08@studentflow.example.com", "임채원", Role.MEMBER, "홍보부", 2),
        ]
        users: dict[str, User] = {}
        demo_password_hash = hash_password(DEMO_PASSWORD)
        for email, name, role, department_name, grade in account_specs:
            user = await db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(
                    email=email,
                    name=name,
                    password_hash=demo_password_hash,
                    role=role,
                    department_id=departments[department_name].id if department_name else None,
                    term_id=term.id,
                    grade=grade,
                    is_active=True,
                    onboarding_completed_at=datetime.now(UTC),
                )
                db.add(user)
                await db.flush()
            users[email] = user

        teacher = users[account_specs[0][0]]
        manager = users[account_specs[1][0]]
        poster_manager = users[account_specs[3][0]]
        participants = [users[item[0]] for item in account_specs[1:]]
        first_day = date.today() + timedelta(days=14)
        second_day = first_day + timedelta(days=1)

        event_title = "[기술 시연] 가을 학교 축제"
        event = await db.scalar(
            select(Event).where(Event.term_id == term.id, Event.title == event_title)
        )
        if not event:
            event = Event(
                term_id=term.id,
                title=event_title,
                type=EventType.EVENT,
                description="학생 제안이 교사 승인과 실제 업무로 이어지는 기능 검사 행사입니다.",
                location="본관 1층과 운동장",
                event_date=first_day,
                starts_at=time(9, 0),
                ends_at=time(16, 0),
                department_id=departments["기획부"].id,
                manager_id=manager.id,
                status="PLANNED",
            )
            db.add(event)
            await db.flush()
        existing_participants = set(
            (await db.scalars(select(EventParticipant.user_id).where(EventParticipant.event_id == event.id))).all()
        )
        db.add_all(
            EventParticipant(event_id=event.id, user_id=user.id)
            for user in participants
            if user.id not in existing_participants
        )

        async def ensure_task(title: str, task_type: TaskType, assignee: User, **values) -> Task:
            task = await db.scalar(select(Task).where(Task.term_id == term.id, Task.title == title))
            if not task:
                task = Task(
                    term_id=term.id,
                    event_id=event.id,
                    title=title,
                    type=task_type,
                    status=TaskStatus.TODO,
                    created_by=teacher.id,
                    **values,
                )
                db.add(task)
                await db.flush()
            assigned = await db.scalar(
                select(TaskAssignee.id).where(TaskAssignee.task_id == task.id, TaskAssignee.user_id == assignee.id)
            )
            if not assigned:
                db.add(TaskAssignee(task_id=task.id, user_id=assignee.id))
            return task

        formation_task = await ensure_task(
            "[기술 시연] 가을 학교 축제 조 편성",
            TaskType.TEAM_FORMATION,
            manager,
            description="이틀 동안 안내조와 운영조를 편성합니다. 각 조 2명, 총 8명을 배정해 주세요.",
            due_at=datetime.combine(first_day - timedelta(days=4), time(18, 0), tzinfo=UTC),
            operation_days=2,
            teams_per_day=2,
            people_per_team=2,
            team_role_description="행사 안내와 부스 운영",
            team_requirements=[
                {"name": "안내조", "people_count": 2, "role_description": "입구 안내와 동선 관리"},
                {"name": "운영조", "people_count": 2, "role_description": "체험 부스 진행과 물품 관리"},
            ],
            operation_dates=[first_day.isoformat(), second_day.isoformat()],
        )
        poster_task = await ensure_task(
            "[기술 시연] 가을 학교 축제 포스터 제출",
            TaskType.SUBMISSION,
            poster_manager,
            description="PNG, JPG 또는 PDF 포스터 파일을 올려 제출 기능을 검사합니다.",
            due_at=datetime.combine(first_day - timedelta(days=7), time(18, 0), tzinfo=UTC),
        )
        await ensure_task(
            "[삭제 기능 검사] 독립 업무",
            TaskType.SIMPLE,
            teacher,
            description="제출물이나 조 기록이 없어 안전하게 삭제할 수 있는 검사 데이터입니다.",
            due_at=datetime.combine(first_day, time(12, 0), tzinfo=UTC),
        )

        proposal_title = "[기술 시연] 가을 학교 축제 운영 제안"
        proposal = await db.scalar(
            select(CommunityPost).where(CommunityPost.term_id == term.id, CommunityPost.title == proposal_title)
        )
        if not proposal:
            proposal = CommunityPost(
                term_id=term.id,
                author_id=manager.id,
                kind="SUGGESTION",
                title=proposal_title,
                content="전교생이 함께 참여하는 체험 부스와 독서 교환 행사를 운영합니다.",
                is_anonymous=False,
                test_recommendation_bonus=10,
                agenda_at=datetime.now(UTC),
                plan_writer_id=manager.id,
                meeting_date=date.today(),
                meeting_time_slot="LUNCH",
                meeting_time=time(12, 40),
                converted_event_id=event.id,
                converted_at=datetime.now(UTC),
                converted_by=teacher.id,
                proposal_status="CONFIRMED",
                proposal_topic="학생 참여형 가을 행사",
                current_proposal_version=1,
            )
            db.add(proposal)
            await db.flush()
            db.add(ProposalVersion(
                post_id=proposal.id,
                version_number=1,
                title=proposal_title,
                description=proposal.content,
                topic=proposal.proposal_topic,
                change_summary="기능 검사 최초 제안",
                author_id=manager.id,
            ))
        plan = await db.scalar(select(CommunityEventPlan).where(CommunityEventPlan.post_id == proposal.id))
        if not plan:
            plan = CommunityEventPlan(
                post_id=proposal.id,
                author_id=manager.id,
                purpose="학생들이 역할을 나누어 학교 행사를 직접 운영합니다.",
                target_participants="전교생",
                schedule_plan="이틀간 점심시간과 방과 후 운영",
                location_plan=event.location,
                program_plan="안내, 독서 교환, 체험 부스를 운영합니다.",
                role_plan="안내조와 운영조로 나누어 진행합니다.",
                budget_plan="인쇄비와 소모품비 5만원",
                safety_plan="통로를 확보하고 담당 교사가 현장을 확인합니다.",
                operation_days=2,
                teams_per_day=2,
                people_per_team=2,
                team_role_description="행사 안내와 부스 운영",
                team_requirements=formation_task.team_requirements,
                operation_dates=formation_task.operation_dates,
                team_manager_id=manager.id,
                poster_manager_id=poster_manager.id,
                poster_required=True,
                team_task_id=formation_task.id,
                poster_task_id=poster_task.id,
                status="APPROVED",
                version=1,
                submitted_at=datetime.now(UTC),
                submitted_by=manager.id,
                approved_at=datetime.now(UTC),
                approved_by=teacher.id,
                meeting_notes={"결정": "이틀간 두 조로 운영", "확인": "참여자와 안전 계획 점검"},
                final_plan={"title": proposal_title, "status": "teacher-approved"},
            )
            db.add(plan)

        async def ensure_notice(title: str, content: str, pinned: bool = False) -> None:
            notice = await db.scalar(select(Notice).where(Notice.term_id == term.id, Notice.title == title))
            if not notice:
                notice = Notice(
                    term_id=term.id,
                    title=title,
                    content=content,
                    type=NoticeType.GENERAL,
                    author_id=teacher.id,
                    pinned=pinned,
                    waiting_enabled=False,
                )
                db.add(notice)
                await db.flush()
                db.add_all(NoticeRecipient(notice_id=notice.id, user_id=user.id) for user in participants)

        await ensure_notice("[기술 시연] 축제 준비 안내", "조 편성과 포스터 제출 업무를 각 담당 계정에서 확인해 주세요.", True)
        await ensure_notice("[삭제 기능 검사] 독립 공지", "신청 내역이 없는 공지로 삭제 동작을 확인할 수 있습니다.")

        delete_event_title = "[삭제 기능 검사] 독립 행사"
        delete_event = await db.scalar(
            select(Event).where(Event.term_id == term.id, Event.title == delete_event_title, Event.status != "DELETED")
        )
        if not delete_event:
            db.add(Event(
                term_id=term.id,
                title=delete_event_title,
                type=EventType.EVENT,
                description="연결된 업무가 없는 행사 삭제 검사 데이터입니다.",
                location="시청각실",
                event_date=second_day,
                starts_at=time(15, 0),
                ends_at=time(16, 0),
                department_id=departments["기획부"].id,
                manager_id=teacher.id,
                status="PLANNED",
            ))
        await db.commit()
        print("Demo data ready")
        print(f"Login: demo-teacher@studentflow.example.com / {DEMO_PASSWORD}")
        print(f"Tutorial: {event_title}")
        print("Delete checks: [삭제 기능 검사] 독립 업무/행사/공지")


async def create_teacher(email: str, name: str, password: str) -> None:
    try:
        normalized_email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    except ValidationError as error:
        raise SystemExit("올바른 이메일 주소를 입력해 주세요.") from error

    async with SessionFactory() as db:
        term = await current_term(db)
        existing = await db.scalar(select(User).where(User.email == normalized_email))
        if existing:
            raise SystemExit("이미 존재하는 이메일입니다.")
        db.add(
            User(
                email=normalized_email,
                name=name,
                password_hash=hash_password(password),
                role=Role.TEACHER,
                term_id=term.id,
            )
        )
        await db.commit()
        print(f"Created teacher: {normalized_email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="기능 검사 예시 데이터를 보강합니다.")
    parser.add_argument("--email")
    parser.add_argument("--name")
    parser.add_argument("--password")
    args = parser.parse_args()
    if args.demo:
        asyncio.run(seed_demo_data())
    elif args.email and args.name and args.password:
        asyncio.run(create_teacher(args.email, args.name, args.password))
    else:
        parser.error("--demo 또는 --email, --name, --password를 함께 입력해 주세요.")
