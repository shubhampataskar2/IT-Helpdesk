from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.core.jobs import run_background
from app.models import KBArticle, User
from app.schemas import KBArticleCreate, KBArticleOut, KBPage, KBSearchHit
from app.services import kb_service

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.post("", response_model=KBArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: KBArticleCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    article = kb_service.create_article(db, user.id, payload)
    background.add_task(run_background, "embed_article", article.id)
    return article


@router.get("", response_model=KBPage)
def list_articles(
    q: str | None = None,
    category: str | None = Query(None, pattern="^(hardware|software|network|access|other)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return kb_service.list_articles(db, category, q, page, size)


@router.get("/search", response_model=list[KBSearchHit])
def search_articles(
    q: str = Query(min_length=2),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.ai.factory import get_ai_provider

    raw = kb_service.search(db, q, get_ai_provider(), limit=limit)
    return [
        KBSearchHit(
            article_id=h["article_id"],
            title=h["title"],
            snippet=(h["body"][:200] + "…") if len(h["body"]) > 200 else h["body"],
            score=h["score"],
            category=h["category"],
        )
        for h in raw
    ]


@router.get("/{article_id}", response_model=KBArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    article = db.get(KBArticle, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    kb_service.delete_article(db, user.id, article_id)
    return None
