from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models import User
from app.schemas import RoleUpdateIn, UserOut
from app.services import audit_service

router = APIRouter(prefix="/users", tags=["users"])


class ActiveUpdateIn(BaseModel):
    is_active: bool


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.get("/engineers", response_model=list[UserOut])
def list_engineers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(User).where(User.role.in_(("support", "admin"))).order_by(User.full_name)).all()


@router.patch("/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: int,
    payload: RoleUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id and payload.role != "admin":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admins cannot demote themselves")
    user.role = payload.role
    audit_service.write_audit(db, admin.id, "user.role_update", "user", user.id,
                              {"to_role": payload.role})
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/active", response_model=UserOut)
def set_active(
    user_id: int,
    payload: ActiveUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Admins cannot deactivate themselves")
    user.is_active = payload.is_active
    audit_service.write_audit(db, admin.id, "user.active_update", "user", user.id,
                              {"is_active": payload.is_active})
    db.commit()
    db.refresh(user)
    return user
