from sqlalchemy import func, select

from app.models import Ticket
from app.services.sla_service import sla_targets


def _count(db, *criteria) -> int:
    stmt = select(func.count()).select_from(Ticket)
    for c in criteria:
        if c is not None:
            stmt = stmt.where(c)
    return db.scalar(stmt) or 0


def overview(db) -> dict:
    active = ("new", "open", "in_progress")
    total = _count(db)

    by_status = {
        s: _count(db, Ticket.status == s) for s in ("new", "open", "in_progress", "resolved", "closed")
    }
    open_tickets = sum(by_status[s] for s in active)

    category_dist = {c: 0 for c in ("hardware", "software", "network", "access", "other")}
    for c in category_dist:
        category_dist[c] = _count(db, Ticket.status.in_(active), Ticket.category == c)

    priority_dist = {p: 0 for p in ("low", "medium", "high", "critical")}
    for p in priority_dist:
        priority_dist[p] = _count(db, Ticket.status.in_(active), Ticket.priority == p)

    avg_resolve = db.execute(
        select(func.avg(func.extract("epoch", (Ticket.resolved_at - Ticket.created_at)) / 60))
        .where(Ticket.resolved_at.is_not(None))
    ).scalar()

    duplicates = _count(db, Ticket.duplicate_of_id.is_not(None))

    created_rows = db.execute(
        select(func.date(Ticket.created_at).label("d"), func.count().label("c"))
        .group_by(func.date(Ticket.created_at)).order_by(func.date(Ticket.created_at))
    ).all()
    resolved_rows = db.execute(
        select(func.date(Ticket.resolved_at).label("d"), func.count().label("c"))
        .where(Ticket.resolved_at.is_not(None))
        .group_by(func.date(Ticket.resolved_at)).order_by(func.date(Ticket.resolved_at))
    ).all()

    return {
        "total": total,
        "open_tickets": open_tickets,
        "by_status": by_status,
        "category_dist": category_dist,
        "priority_dist": priority_dist,
        "avg_resolve_minutes": round(float(avg_resolve), 1) if avg_resolve else None,
        "duplicates": duplicates,
        "created_by_day": {str(r[0]): r[1] for r in created_rows},
        "resolved_by_day": {str(r[0]): r[1] for r in resolved_rows},
    }


def sla_stats(db) -> dict:
    priorities = ("low", "medium", "high", "critical")
    result = {}
    for p in priorities:
        total = _count(db, Ticket.priority == p)
        resolved = _count(db, Ticket.priority == p, Ticket.resolved_at.is_not(None))
        met_response = 0
        met_resolve = 0
        response_base = 0
        rows = db.execute(
            select(Ticket.first_response_at, Ticket.resolved_at, Ticket.created_at)
            .where(Ticket.priority == p)
        ).all()
        response_target, resolve_target = sla_targets(p)
        for first_response, resolved_at, created_at in rows:
            if created_at is None:
                continue
            if first_response is not None:
                response_base += 1
                if first_response <= created_at + _minutes(response_target):
                    met_response += 1
            if resolved_at is not None:
                if resolved_at <= created_at + _minutes(resolve_target):
                    met_resolve += 1
        result[p] = {
            "total": total,
            "resolved": resolved,
            "response_measured": response_base,
            "response_compliance": round(met_response / response_base, 3) if response_base else None,
            "resolve_measured": resolved,
            "resolve_compliance": round(met_resolve / resolved, 3) if resolved else None,
        }
    return result


def _minutes(m):
    from datetime import timedelta
    return timedelta(minutes=m)


def engineer_stats(db) -> dict:
    from app.models import User

    engineers = db.scalars(select(User).where(User.role.in_(("support", "admin")))).all()
    out = []
    for u in engineers:
        assigned = _count(db, Ticket.assignee_id == u.id)
        active = _count(db, Ticket.status.in_(("new", "open", "in_progress")), Ticket.assignee_id == u.id)
        resolved_count = _count(db, Ticket.assignee_id == u.id, Ticket.resolved_at.is_not(None))
        avg = db.execute(
            select(func.avg(func.extract("epoch", (Ticket.resolved_at - Ticket.created_at)) / 60))
            .where(Ticket.resolved_at.is_not(None), Ticket.assignee_id == u.id)
        ).scalar()
        out.append({
            "user_id": u.id,
            "name": u.full_name,
            "email": u.email,
            "role": u.role,
            "assigned": assigned,
            "active": active,
            "resolved": resolved_count,
            "avg_resolve_minutes": round(float(avg), 1) if avg else None,
        })
    return out
