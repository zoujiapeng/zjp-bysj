from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.dependencies import client_ip
from app.models import AuditLog, User


def add_audit_log(
    db: Session,
    *,
    actor: User | None,
    action: str,
    resource_type: str,
    resource_id: int | str | None,
    summary: str,
    request: Request | None = None,
    extra_data: dict[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        summary=summary[:500],
        ip_address=client_ip(request) if request else None,
        extra_data=extra_data or {},
    )
    db.add(log)
    return log
