from fastapi import APIRouter, Depends
from core.rbac import require_role

router = APIRouter()

@router.get("/admin/health")
def system_health(
    user=Depends(require_role("admin"))
):
    return {"status": "OK", "checked_by": user["user_id"]}
