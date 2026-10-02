from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


# ---------- Users ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class RoleUpdateIn(BaseModel):
    role: str = Field(pattern="^(employee|support|admin)$")


# ---------- Tickets ----------
class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10, max_length=10000)


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    status: str | None = Field(default=None, pattern="^(new|open|in_progress|resolved|closed)$")
    priority: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    category: str | None = Field(default=None, pattern="^(hardware|software|network|access|other)$")


class AssignIn(BaseModel):
    assignee_id: int | None = None


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    body: str
    author_name: str | None = None
    created_at: datetime


class DuplicateInfo(BaseModel):
    ticket_id: int | None = None
    ticket_number: str | None = None
    similarity: float | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    title: str
    description: str
    status: str
    priority: str
    category: str
    ai_summary: str | None = None
    ai_suggested_fix: str | None = None
    ai_confidence: float | None = None
    ai_refined: bool = False
    creator_id: int
    creator_name: str | None = None
    assignee_id: int | None = None
    assignee_name: str | None = None
    duplicate_of: DuplicateInfo | None = None
    first_response_at: datetime | None = None
    sla_response_due_at: datetime | None = None
    sla_resolve_due_at: datetime | None = None
    escalated: bool = False
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class TicketDetail(TicketOut):
    comments: list[CommentOut] = Field(default_factory=list)


class Page(BaseModel):
    items: list[TicketOut]
    total: int
    page: int
    size: int


# ---------- Knowledge base ----------
class KBArticleCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=10, max_length=20000)
    category: str = Field(default="other", pattern="^(hardware|software|network|access|other)$")


class KBArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    category: str
    created_at: datetime
    updated_at: datetime


class KBSearchHit(BaseModel):
    article_id: int
    title: str
    snippet: str
    score: float | None = None
    category: str


class KBPage(BaseModel):
    items: list[KBArticleOut]
    total: int
    page: int
    size: int
