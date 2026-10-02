from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models import User
from app.schemas import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        user = auth_service.register(db, payload.email, payload.full_name, payload.password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return auth_service.issue_tokens(db, user)


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginIn, db: Session = Depends(get_db)):
    try:
        user = auth_service.authenticate(db, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))
    return auth_service.issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    try:
        return auth_service.rotate_refresh(db, payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))


@router.post("/logout/refresh", status_code=status.HTTP_204_NO_CONTENT)
def logout_refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    auth_service.revoke_refresh(db, payload.refresh_token)
    return None


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
