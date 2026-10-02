from app.models import AuditLog


def write_audit(db, actor_id: int | None, action: str, entity_type: str, entity_id: int | None = None,
                details: dict | None = None) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details,
    )
    db.add(entry)
    return entry
