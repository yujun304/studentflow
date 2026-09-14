from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.operations import (
    create_decision,
    create_handover,
    create_map_assignment,
    create_run_item,
    list_completion_records,
    list_decisions,
    list_handovers,
    list_map_assignments,
    list_run_items,
    reorder_run_items,
    save_event_completion,
    update_decision_status,
    update_map_assignment_position,
    update_run_item_status,
)
from app.core.database import Base
from app.models.entities import (
    DecisionStatus,
    Event,
    EventParticipant,
    EventType,
    MapAssignment,
    Role,
    RunItemStatus,
    SchoolMap,
    StoredFile,
    Task,
    TaskAssignee,
    TaskStatus,
    Term,
    User,
)
from app.schemas import (
    DecisionCardIn,
    DecisionCardStatusIn,
    EventRunItemIn,
    EventRunItemsReorderIn,
    EventRunItemStatusIn,
    EventCompletionRecordIn,
    HandoverGuideIn,
    MapAssignmentIn,
    MapAssignmentPositionIn,
)


@pytest.mark.asyncio
async def test_operations_flow_links_decision_task_handover_runbook_and_map_assignment():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        previous = Term(
            name="2025 학생회",
            starts_on=date(2025, 3, 1),
            ends_on=date(2026, 2, 28),
            is_current=False,
        )
        current = Term(
            name="2026 학생회",
            starts_on=date(2026, 3, 1),
            ends_on=date(2027, 2, 28),
            is_current=True,
        )
        db.add_all([previous, current])
        await db.flush()
        teacher = User(
            email="teacher@example.com",
            name="담당 선생님",
            password_hash="unused",
            role=Role.TEACHER,
            term_id=current.id,
        )
        student = User(
            email="student@example.com",
            name="김학생",
            password_hash="unused",
            role=Role.MEMBER,
            term_id=current.id,
        )
        db.add_all([teacher, student])
        await db.flush()
        event = Event(
            term_id=current.id,
            title="학교 축제",
            type=EventType.EVENT,
            event_date=date(2026, 10, 10),
            manager_id=teacher.id,
        )
        db.add(event)
        await db.flush()
        db.add(EventParticipant(event_id=event.id, user_id=student.id))
        await db.commit()

        decision = await create_decision(
            DecisionCardIn(
                title="정문 안내판 설치",
                detail="행사 시작 전 설치 상태를 확인한다.",
                owner_id=student.id,
                due_at=datetime(2026, 10, 10, 0, tzinfo=UTC),
                event_id=event.id,
            ),
            teacher,
            db,
        )
        assert decision.task_id is not None
        task = await db.get(Task, decision.task_id)
        assert task and task.title == decision.title
        assert await db.scalar(
            select(TaskAssignee.id).where(
                TaskAssignee.task_id == task.id, TaskAssignee.user_id == student.id
            )
        )
        member_decisions = await list_decisions(student, db)
        assert [item.id for item in member_decisions] == [decision.id]
        finished = await update_decision_status(
            decision.id, DecisionCardStatusIn(status=DecisionStatus.DONE), student, db
        )
        assert finished.completed_at is not None
        assert (await db.get(Task, task.id)).status == TaskStatus.DONE

        handover = await create_handover(
            HandoverGuideIn(
                title="축제 운영 인수인계",
                summary="행사 3주 전부터 역할을 확정한다.",
                what_worked="동선별 안내조 편성",
                pitfalls="우천 시 안내판 고정 필요",
                checklist="안내판\n우비\n무전기",
                event_id=event.id,
                publish=True,
            ),
            teacher,
            db,
        )
        assert handover.published_at is not None
        assert any(item.id == handover.id for item in await list_handovers(None, student, db))

        run_item = await create_run_item(
            event.id,
            EventRunItemIn(
                title="정문 안내 시작",
                planned_at=datetime(2026, 10, 10, 0, tzinfo=UTC),
                location_label="정문",
                assignee_id=student.id,
            ),
            teacher,
            db,
        )
        active = await update_run_item_status(
            run_item.id,
            EventRunItemStatusIn(status=RunItemStatus.IN_PROGRESS, note="안내 시작"),
            student,
            db,
        )
        assert active.status == RunItemStatus.IN_PROGRESS
        second_run_item = await create_run_item(
            event.id,
            EventRunItemIn(
                title="무대 시작",
                planned_at=datetime(2026, 10, 10, 1, tzinfo=UTC),
                location_label="운동장",
                assignee_id=student.id,
            ),
            teacher,
            db,
        )
        reordered = await reorder_run_items(
            event.id,
            EventRunItemsReorderIn(item_ids=[second_run_item.id, run_item.id]),
            teacher,
            db,
        )
        assert [item.id for item in reordered] == [second_run_item.id, run_item.id]
        assert [item.id for item in await list_run_items(event.id, teacher, db)] == [
            second_run_item.id,
            run_item.id,
        ]

        stored = StoredFile(
            original_name="map.png",
            storage_key="test/map.png",
            mime_type="image/png",
            size=100,
            uploaded_by=teacher.id,
        )
        db.add(stored)
        await db.flush()
        school_map = SchoolMap(
            term_id=current.id,
            event_id=event.id,
            title="축제 배치도",
            file_id=stored.id,
            created_by=teacher.id,
        )
        db.add(school_map)
        await db.commit()
        assignment = await create_map_assignment(
            school_map.id,
            MapAssignmentIn(
                user_id=student.id,
                label="정문 A 지점",
                activity="방문객 동선 안내",
                x_ratio=0.25,
                y_ratio=0.75,
            ),
            teacher,
            db,
        )
        assert assignment.user_name == "김학생"
        visible = await list_map_assignments(school_map.id, student, db)
        assert len(visible) == 1
        assert visible[0].activity == "방문객 동선 안내"
        moved = await update_map_assignment_position(
            assignment.id,
            MapAssignmentPositionIn(x_ratio=0.6, y_ratio=0.4),
            teacher,
            db,
        )
        assert moved.x_ratio == 0.6
        assert moved.y_ratio == 0.4
        assert await db.scalar(
            select(MapAssignment.id).where(MapAssignment.id == assignment.id)
        ) == assignment.id

        completion = await save_event_completion(
            event.id,
            EventCompletionRecordIn(
                summary="축제를 안전하게 마무리했다.",
                outcomes="학생 안내 동선이 원활했다.",
                incidents="우천으로 일부 일정이 지연됐다.",
                recommendations="우천 동선을 사전에 공지한다.",
                attendee_count=320,
                completed_at=datetime(2026, 10, 10, 8, tzinfo=UTC),
                create_handover_draft=True,
            ),
            teacher,
            db,
        )
        assert completion.handover_guide_id is not None
        assert completion.event_title == "학교 축제"
        assert (await db.get(Event, event.id)).status == "COMPLETED"
        records = await list_completion_records(student, db)
        assert [record.id for record in records] == [completion.id]

    await engine.dispose()
