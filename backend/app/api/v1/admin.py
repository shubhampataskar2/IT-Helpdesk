from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-logs")
def audit_logs(
    action: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    total = len(db.scalars(stmt).all())
    rows = db.scalars(stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    items = []
    for row in rows:
        actor = db.get(User, row.actor_id) if row.actor_id else None
        items.append({
            "id": row.id,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "details": row.details,
            "actor_name": actor.full_name if actor else None,
            "created_at": row.created_at,
        })
    return {"items": items, "total": total, "page": page, "size": size}
