import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.security_event import SecurityEvent


def record_security_event(
    db: Session,
    *,
    event_type: str,
    success: bool = True,
    user_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: dict | None = None,
) -> SecurityEvent:
    event = SecurityEvent(
        user_id=user_id,
        event_type=event_type,
        success=success,
        ip_address=ip_address[:45] if ip_address else None,
        user_agent=user_agent[:500] if user_agent else None,
        details=json.dumps(details, ensure_ascii=False) if details else None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_security_events(db: Session, user_id: int, limit: int = 50):
    return db.scalars(
        select(SecurityEvent)
        .where(SecurityEvent.user_id == user_id)
        .order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc())
        .limit(limit)
    ).all()
