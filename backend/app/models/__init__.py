from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="employee")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    tickets_created = relationship("Ticket", foreign_keys="Ticket.creator_id", back_populates="creator")
    assigned_tickets = relationship("Ticket", foreign_keys="Ticket.assignee_id", back_populates="assignee")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status_created", "status", "created_at"),
        Index("ix_tickets_creator", "creator_id"),
        Index("ix_tickets_assignee", "assignee_id"),
    )

    id = Column(Integer, primary_key=True)
    number = Column(String(30), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(String(20), nullable=False, default="new", index=True)
    priority = Column(String(10), nullable=False, default="medium", index=True)
    category = Column(String(20), nullable=False, default="other", index=True)

    ai_summary = Column(Text, nullable=True)
    ai_suggested_fix = Column(Text, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_refined = Column(Boolean, nullable=False, default=False)
    description_embedding = Column(Text, nullable=True)

    duplicate_of_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)

    creator_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    first_response_at = Column(DateTime(timezone=True), nullable=True)
    sla_response_due_at = Column(DateTime(timezone=True), nullable=True)
    sla_resolve_due_at = Column(DateTime(timezone=True), nullable=True)
    escalated = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship("User", foreign_keys=[creator_id], back_populates="tickets_created")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tickets")
    duplicate_of = relationship("Ticket", remote_side=[id])
    comments = relationship(
        "TicketComment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at",
    )


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")


class KBArticle(Base):
    __tablename__ = "kb_articles"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(20), nullable=False, default="other", index=True)
    embedding = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(40), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
