import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import current_user
from app.models.entities import Comment, Role, Task, TaskAssignee, User
from app.schemas import CommentIn, CommentOut
from app.services.notifications import create_notifications

router = APIRouter(prefix="/comments", tags=["comments"])


async def visible_task(db: AsyncSession, task_id: uuid.UUID, user: User) -> Task:
    task = await db.get(Task, task_id)
    if not task or task.term_id != user.term_id:
        raise AppError(404, "comment_target_not_found", "댓글을 작성할 업무를 찾을 수 없습니다.")
    if user.role in {Role.EXECUTIVE_BOARD, Role.TEACHER} or task.created_by == user.id:
        return task
    assigned_user = await db.scalar(
        select(User)
        .join(TaskAssignee, TaskAssignee.user_id == User.id)
        .where(TaskAssignee.task_id == task.id, User.id == user.id)
    )
    if assigned_user:
        return task
    if user.role == Role.DEPARTMENT_HEAD and user.department_id:
        department_assignee = await db.scalar(
            select(User.id)
            .join(TaskAssignee, TaskAssignee.user_id == User.id)
            .where(
                TaskAssignee.task_id == task.id,
                User.term_id == user.term_id,
                User.department_id == user.department_id,
            )
            .limit(1)
        )
        if department_assignee:
            return task
    raise AppError(404, "comment_target_not_found", "댓글을 작성할 업무를 찾을 수 없습니다.")


async def comment_out(db: AsyncSession, comment: Comment, user: User) -> CommentOut:
    author = await db.get(User, comment.author_id)
    deleted = comment.deleted_at is not None
    return CommentOut.model_validate(comment).model_copy(
        update={
            "content": "삭제된 댓글입니다." if deleted else comment.content,
            "author_name": author.name if author else "알 수 없음",
            "is_mine": comment.author_id == user.id,
            "can_delete": comment.author_id == user.id or user.role == Role.TEACHER,
            "deleted": deleted,
        }
    )


@router.get("", response_model=list[CommentOut])
async def list_comments(
    target_type: str,
    target_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if target_type != "task":
        raise AppError(422, "comment_target_invalid", "현재는 업무 댓글만 지원합니다.")
    await visible_task(db, target_id, user)
    comments = list(
        (
            await db.scalars(
                select(Comment)
                .where(
                    Comment.term_id == user.term_id,
                    Comment.target_type == target_type,
                    Comment.target_id == target_id,
                )
                .order_by(Comment.created_at, Comment.id)
            )
        ).all()
    )
    by_parent: dict[uuid.UUID | None, list[Comment]] = {}
    comment_ids = {comment.id for comment in comments}
    for comment in comments:
        parent_id = comment.parent_id if comment.parent_id in comment_ids else None
        by_parent.setdefault(parent_id, []).append(comment)
    ordered: list[Comment] = []

    def append_thread(parent_id: uuid.UUID | None) -> None:
        for item in by_parent.get(parent_id, []):
            ordered.append(item)
            append_thread(item.id)

    append_thread(None)
    return [await comment_out(db, comment, user) for comment in ordered]


@router.post("", response_model=CommentOut)
async def create_comment(
    data: CommentIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await visible_task(db, data.target_id, user)
    content = data.content.strip()
    if not content:
        raise AppError(422, "comment_content_required", "댓글 내용을 입력해 주세요.")
    if data.parent_id:
        parent = await db.get(Comment, data.parent_id)
        if (
            not parent
            or parent.term_id != user.term_id
            or parent.target_type != data.target_type
            or parent.target_id != data.target_id
            or parent.deleted_at is not None
        ):
            raise AppError(422, "comment_parent_invalid", "답글을 달 댓글을 찾을 수 없습니다.")
    comment = Comment(
        term_id=user.term_id,
        target_type=data.target_type,
        target_id=data.target_id,
        author_id=user.id,
        parent_id=data.parent_id,
        content=content,
        is_anonymous=False,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    assignee_ids = set(
        (
            await db.scalars(
                select(TaskAssignee.user_id).where(TaskAssignee.task_id == task.id)
            )
        ).all()
    )
    recipients = (assignee_ids | {task.created_by}) - {user.id}
    if recipients:
        await create_notifications(
            db,
            recipients,
            notification_type="TASK_COMMENTED",
            title=f"{task.title}에 새 댓글이 있습니다",
            content=f"{user.name}: {comment.content[:120]}",
            target_type="task",
            target_id=task.id,
        )
    return await comment_out(db, comment, user)


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    comment = await db.get(Comment, comment_id)
    if not comment or comment.term_id != user.term_id:
        raise AppError(404, "comment_not_found", "댓글을 찾을 수 없습니다.")
    await visible_task(db, comment.target_id, user)
    if comment.author_id != user.id and user.role != Role.TEACHER:
        raise AppError(403, "comment_delete_forbidden", "본인이 작성한 댓글만 삭제할 수 있습니다.")
    if comment.deleted_at is None:
        comment.deleted_at = datetime.now(UTC)
        await db.commit()
    return Response(status_code=204)
