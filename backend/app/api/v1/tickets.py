from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_support
from app.core.database import get_db
from app.core.jobs import run_background
from app.models import Ticket, User
from app.schemas import (
    AssignIn,
    CommentCreate,
    CommentOut,
    Page,
    TicketCreate,
    TicketDetail,
    TicketOut,
    TicketUpdate,
)
from app.services import audit_service, email_service, sla_service, ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _ticket_dict(db: Session, ticket: Ticket) -> dict:
    dup = None
    if ticket.duplicate_of_id:
        original = db.get(Ticket, ticket.duplicate_of_id)
        if original:
            dup = {"ticket_id": original.id, "ticket_number": original.number}
    return {
        "id": ticket.id,
        "number": ticket.number,
        "title": ticket.title,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category,
        "ai_summary": ticket.ai_summary,
        "ai_suggested_fix": ticket.ai_suggested_fix,
        "ai_confidence": ticket.ai_confidence,
        "ai_refined": ticket.ai_refined,
        "creator_id": ticket.creator_id,
        "creator_name": ticket.creator.full_name if ticket.creator else None,
        "assignee_id": ticket.assignee_id,
        "assignee_name": ticket.assignee.full_name if ticket.assignee else None,
        "duplicate_of": dup,
        "first_response_at": ticket.first_response_at,
        "sla_response_due_at": ticket.sla_response_due_at,
        "sla_resolve_due_at": ticket.sla_resolve_due_at,
        "escalated": ticket.escalated,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at,
        "closed_at": ticket.closed_at,
    }


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = ticket_service.create_ticket(db, user, payload)
    background.add_task(run_background, "analyze_ticket", ticket.id)
    email_service.notify_ticket_created(ticket, ticket.ai_summary)
    return _ticket_dict(db, ticket)


@router.get("", response_model=Page)
def list_tickets(
    status_filter: str | None = Query(None, alias="status", pattern="^(new|open|in_progress|resolved|closed)$"),
    priority: str | None = Query(None, pattern="^(low|medium|high|critical)$"),
    category: str | None = Query(None, pattern="^(hardware|software|network|access|other)$"),
    q: str | None = None,
    mine: bool = Query(False),
    assignee_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Ticket)
    if mine:
        stmt = stmt.where(Ticket.creator_id == user.id)
    elif user.role == "employee":
        stmt = stmt.where(or_(Ticket.creator_id == user.id, Ticket.assignee_id == user.id))
    if status_filter:
        stmt = stmt.where(Ticket.status == status_filter)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)
    if category:
        stmt = stmt.where(Ticket.category == category)
    if assignee_id is not None:
        stmt = stmt.where(Ticket.assignee_id == assignee_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Ticket.title.ilike(like), Ticket.description.ilike(like), Ticket.number.ilike(like)))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Ticket.created_at.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return {"items": [_ticket_dict(db, t) for t in rows], "total": total, "page": page, "size": size}


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    if user.role == "employee" and ticket.creator_id != user.id and ticket.assignee_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your ticket")
    data = _ticket_dict(db, ticket)
    data["comments"] = [
        CommentOut(id=c.id, body=c.body, author_name=c.author.full_name if c.author else None,
                   created_at=c.created_at)
        for c in ticket.comments
    ]
    return data


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")

    if user.role == "employee":
        if ticket.creator_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your ticket")
        if payload.status == "resolved" or payload.status == "closed":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Employees cannot resolve/close tickets")
        if payload.status is not None and payload.status != "open":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed for your role")

    status_changed = payload.status is not None
    if status_changed:
        try:
            ticket = ticket_service.apply_status(db, user, ticket, payload.status)
        except PermissionError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
    if payload.title is not None:
        ticket.title = payload.title.strip()
    if payload.description is not None:
        ticket.description = payload.description.strip()
        ticket.ai_refined = False
    changed_priority = payload.priority is not None and payload.priority != ticket.priority
    if payload.priority is not None:
        ticket.priority = payload.priority
    if changed_priority:
        sla_service.apply_sla(ticket)
    if payload.category is not None:
        ticket.category = payload.category

    audit_service.write_audit(db, user.id, "ticket.update", "ticket", ticket.id,
                              {"fields": [f for f in ("title", "description", "priority", "category", "status")
                                          if getattr(payload, f) is not None]})
    db.commit()
    db.refresh(ticket)
    if status_changed:
        email_service.notify_status_change(ticket)
    return _ticket_dict(db, ticket)


@router.post("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    ticket_id: int,
    payload: AssignIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_support),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    assignee = user if payload.assignee_id is None else db.get(User, payload.assignee_id)
    if assignee is None or assignee.role not in ("support", "admin"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assignee must be a support engineer or admin")
    ticket.assignee_id = assignee.id
    sla_service.mark_first_response(ticket, db)
    audit_service.write_audit(db, user.id, "ticket.assign", "ticket", ticket.id,
                              {"assignee": assignee.email})
    db.commit()
    db.refresh(ticket)
    email_service.notify_ticket_assigned(ticket, assignee.email, user.full_name)
    return _ticket_dict(db, ticket)


@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    if user.role == "employee" and ticket.creator_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your ticket")
    comment = ticket_service.add_comment(db, user, ticket, payload.body)
    db.commit()
    db.refresh(comment)
    return CommentOut(id=comment.id, body=comment.body,
                      author_name=comment.author.full_name if comment.author else None,
                      created_at=comment.created_at)


@router.post("/{ticket_id}/reopen", response_model=TicketOut)
def reopen_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    try:
        ticket_service.apply_status(db, user, ticket, "open")
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
    audit_service.write_audit(db, user.id, "ticket.reopen", "ticket", ticket.id)
    db.commit()
    db.refresh(ticket)
    email_service.notify_status_change(ticket)
    return _ticket_dict(db, ticket)


@router.post("/{ticket_id}/resolve", response_model=TicketOut)
def resolve_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(require_support)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    try:
        ticket_service.apply_status(db, user, ticket, "resolved")
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
    db.commit()
    db.refresh(ticket)
    email_service.notify_ticket_resolved(ticket)
    return _ticket_dict(db, ticket)
