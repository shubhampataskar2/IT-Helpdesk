from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_support
from app.core.database import get_db
from app.models import User
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(require_support)):
    return analytics_service.overview(db)


@router.get("/sla")
def sla(db: Session = Depends(get_db), _: User = Depends(require_support)):
    return analytics_service.sla_stats(db)


@router.get("/engineers")
def engineers(db: Session = Depends(get_db), _: User = Depends(require_support)):
    return analytics_service.engineer_stats(db)
