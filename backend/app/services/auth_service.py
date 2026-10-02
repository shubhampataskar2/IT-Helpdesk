import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import RefreshToken, User
from app.services import audit_service


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register(db, email: str, full_name: str, password: str) -> User:
    existing = db.scalar(select(User).where(User.email == email.lower()))
    if existing:
        raise ValueError("Email already registered")
    user = User(
        email=email.lower(),
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        role="employee",
    )
    db.add(user)
    db.flush()
    audit_service.write_audit(db, user.id, "user.register", "user", user.id, {"email": user.email})
    db.commit()
    db.refresh(user)
    return user


def authenticate(db, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")
    if not user.is_active:
        raise ValueError("Account is deactivated")
    return user


def issue_tokens(db, user: User) -> dict:
    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh),
                        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)))
    db.commit()
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


def rotate_refresh(db, refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)))
    if not stored or stored.revoked_at is not None:
        raise ValueError("Refresh token revoked")
    if stored.expires_at < datetime.now(timezone.utc):
        raise ValueError("Refresh token expired")
    stored.revoked_at = datetime.now(timezone.utc)
    user = db.get(User, stored.user_id)
    if not user or not user.is_active:
        raise ValueError("User unavailable")
    return issue_tokens(db, user)


def revoke_refresh(db, refresh_token: str) -> None:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)))
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()
