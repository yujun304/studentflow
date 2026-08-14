from fastapi import APIRouter, Depends

from app.api.pending import feature_not_ready
from app.core.security import current_user
from app.models.entities import User
from app.schemas import CommentIn, CommentOut

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("", response_model=list[CommentOut])
async def list_comments(target_type: str, target_id: str, _: User = Depends(current_user)):
    feature_not_ready()


@router.post("", response_model=CommentOut)
async def create_comment(_: CommentIn, __: User = Depends(current_user)):
    feature_not_ready()
