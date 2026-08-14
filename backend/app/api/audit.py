from fastapi import APIRouter, Depends

from app.api.pending import feature_not_ready
from app.core.security import require_roles
from app.models.entities import Role, User

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("")
async def list_audit_logs(_: User = Depends(require_roles(Role.TEACHER))):
    feature_not_ready()
