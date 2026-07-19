from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import require_roles
from app.enums import UserRole
from app.models import AuditLog, User
from app.schemas import AuditLogOut, Page
from app.serializers import audit_log_out

router = APIRouter(prefix="/audit-logs", tags=["审计日志"])


@router.get("", response_model=Page[AuditLogOut])
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    action: str | None = None,
    actor_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    stmt = select(AuditLog).options(joinedload(AuditLog.actor))
    count_stmt = select(func.count(AuditLog.id))
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if actor_id:
        conditions.append(AuditLog.actor_id == actor_id)
    if date_from:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to:
        conditions.append(AuditLog.created_at <= date_to)
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)
    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).unique()
    return Page(
        items=[audit_log_out(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
