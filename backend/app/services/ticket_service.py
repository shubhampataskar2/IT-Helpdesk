import secrets
from datetime import datetime

from app.ai.factory import get_ai_provider
from app.ai.heuristic import HeuristicProvider
from app.core.config import settings
from app.core.constants import ROLE_RANK, TICKET_TRANSITIONS
from app.core.logging import get_logger
from app.models import Ticket, TicketComment, User
from app.rag.search import detect_duplicate, search_kb
from app.services import audit_service, email_service
from app.services.sla_service import apply_sla, now

logger = get_logger("ticket")


def generate_ticket_number() -> str:
    return f"HT-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def quick_analyze(title: str, description: str):
    return HeuristicProvider().classify(title, description)


def create_ticket(db, user: User, payload) -> Ticket:
    quick = quick_analyze(payload.title, payload.description)
    ticket = Ticket(
        number=generate_ticket_number(),
        title=payload.title.strip(),
        description=payload.description.strip(),
        category=quick.category,
        priority=quick.priority,
        ai_summary=quick.summary,
        ai_suggested_fix=quick.suggested_fix,
        ai_confidence=quick.confidence,
        creator_id=user.id,
    )
    apply_sla(ticket)
    db.add(ticket)
    db.flush()
    audit_service.write_audit(
        db, user.id, "ticket.create", "ticket", ticket.id, {"number": ticket.number, "priority": quick.priority}
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def can_transition(user: User, ticket: Ticket, to_status: str) -> bool:
    if ticket.status == to_status:
        return False
    if user.role == "admin" and to_status in ("new", "open", "in_progress", "resolved", "closed"):
        return True
    for tr in TICKET_TRANSITIONS:
        if tr.from_status == ticket.status and tr.to_status == to_status:
            if ROLE_RANK[user.role] < ROLE_RANK[tr.role]:
                continue
            if tr.allow_owner and user.role == "employee" and ticket.creator_id != user.id:
                continue
            return True
    return False


def apply_status(db, user: User, ticket: Ticket, to_status: str) -> Ticket:
    if not can_transition(user, ticket, to_status):
        raise PermissionError(f"Transition {ticket.status}->{to_status} not allowed for {user.role}")
    previous = ticket.status
    ticket.status = to_status
    if to_status == "resolved":
        ticket.resolved_at = now()
    if to_status == "closed":
        ticket.closed_at = now()
        if ticket.resolved_at is None:
            ticket.resolved_at = now()
    if to_status in ("in_progress", "open") and previous == "new":
        ticket.first_response_at = ticket.first_response_at or now()
    audit_service.write_audit(
        db, user.id, "ticket.status_update", "ticket", ticket.id,
        {"from": previous, "to": to_status},
    )
    return ticket


def add_comment(db, user: User, ticket: Ticket, body: str) -> TicketComment:
    comment = TicketComment(ticket_id=ticket.id, author_id=user.id, body=body.strip())
    db.add(comment)
    if ticket.status == "new":
        ticket.status = "open"
        ticket.first_response_at = ticket.first_response_at or now()
        ticket.resolved_at = None
    audit_service.write_audit(db, user.id, "ticket.comment", "ticket", ticket.id, {"length": len(body)})
    return comment


def run_ticket_analysis(db, ticket_id: int) -> None:
    """Full AI pipeline executed asynchronously (celery or inline thread)."""
    try:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            return
        provider = get_ai_provider()
        text = f"{ticket.title}\n{ticket.description}"
        analysis = provider.classify(ticket.title, ticket.description)

        if analysis.category != ticket.category:
            ticket.category = analysis.category
        if analysis.priority != ticket.priority:
            ticket.priority = analysis.priority
            apply_sla(ticket)
        ticket.ai_summary = analysis.summary
        ticket.ai_suggested_fix = analysis.suggested_fix
        ticket.ai_confidence = analysis.confidence
        ticket.ai_refined = True
        ticket.description_embedding = provider.embed(text)

        dup = detect_duplicate(db, provider, text, ticket.id, settings.duplicate_threshold)
        if dup:
            ticket.duplicate_of_id = dup[0]

        kb_hits = search_kb(db, text, provider, limit=2)
        if kb_hits:
            refs = "; ".join(f"[{h['title']}]" for h in kb_hits)
            existing = ticket.ai_suggested_fix or ""
            ticket.ai_suggested_fix = f"{existing}\n\nKnowledge base: {refs}" if existing else f"Knowledge base: {refs}"

        audit_service.write_audit(
            db, None, "ticket.ai_analysis", "ticket", ticket.id,
            {"provider": provider.kind, "priority": analysis.priority, "category": analysis.category,
             "duplicate": bool(dup)},
        )
        db.commit()
        db.refresh(ticket)
        email_service.notify_ticket_created(ticket, analysis.summary)
        if dup:
            original = db.get(Ticket, dup[0])
            if original:
                email_service.notify_duplicate(ticket, original)
    except Exception:  # noqa: BLE001
        logger.exception("Ticket analysis failed for %s", ticket_id)
