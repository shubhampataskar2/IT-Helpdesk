from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.constants import SLA_TARGETS
from app.models import Ticket, User


def now() -> datetime:
    return datetime.now(timezone.utc)


def sla_targets(priority: str) -> tuple[int, int]:
    target = SLA_TARGETS.get(priority, SLA_TARGETS["medium"])
    return target["response"], target["resolve"]


def apply_sla(ticket: Ticket) -> None:
    response_min, resolve_min = sla_targets(ticket.priority)
    ticket.sla_response_due_at = now() + timedelta(minutes=response_min)
    ticket.sla_resolve_due_at = now() + timedelta(minutes=resolve_min)
    ticket.escalated = False


def refresh_sla(ticket: Ticket) -> None:
    apply_sla(ticket)


def mark_first_response(ticket: Ticket, db) -> None:
    if ticket.first_response_at is None:
        ticket.first_response_at = now()


def assign_ticket(db, ticket: Ticket, assignee: User, actor: User) -> None:
    ticket.assignee = assignee
    mark_first_response(ticket, db)


def reopen_ticket(db, ticket: Ticket) -> None:
    ticket.status = "open"
    ticket.resolved_at = None


def check_overdue(db) -> dict:
    """Find active tickets past their response/resolve SLA deadline."""
    overdue = {"response": [], "resolve": []}
    active_statuses = ("new", "open", "in_progress")
    stmt = select(Ticket).where(Ticket.status.in_(active_statuses))
    for ticket in db.scalars(stmt):
        if ticket.sla_response_due_at and ticket.first_response_at is None and ticket.sla_response_due_at < now():
            overdue["response"].append(ticket)
        if ticket.sla_resolve_due_at and ticket.sla_resolve_due_at < now() and ticket.resolved_at is None:
            overdue["resolve"].append(ticket)
    return overdue
