from sqlalchemy.orm import Session
from models.audit_log import AuditLog

def log_audit_event(
    db: Session,
    *,
    actor_id: str,
    actor_type: str,
    role: str,
    action: str,
    resource: str | None = None,
    details: dict | None = None
):
    log = AuditLog(
        actor_id=actor_id,
        actor_type=actor_type,
        role=role,
        action=action,
        resource=resource,
        details=details
    )

    db.add(log)
    db.commit()
