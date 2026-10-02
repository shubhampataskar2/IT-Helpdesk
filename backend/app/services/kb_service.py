from sqlalchemy import func, select

from app.models import KBArticle
from app.rag.search import search_kb
from app.services import audit_service


def create_article(db, actor_id: int, payload) -> KBArticle:
    article = KBArticle(title=payload.title.strip(), body=payload.body.strip(), category=payload.category)
    db.add(article)
    db.flush()
    audit_service.write_audit(db, actor_id, "kb.create", "kb_article", article.id, {"title": article.title})
    db.commit()
    db.refresh(article)
    return article


def delete_article(db, actor_id: int, article_id: int) -> None:
    article = db.get(KBArticle, article_id)
    if article is None:
        return
    db.delete(article)
    audit_service.write_audit(db, actor_id, "kb.delete", "kb_article", article_id, {"title": article.title})
    db.commit()


def embed_article(db, article_id: int, provider) -> None:
    article = db.get(KBArticle, article_id)
    if article is None:
        return
    try:
        article.embedding = provider.embed(f"{article.title}\n{article.body}")
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


def list_articles(db, category: str | None, term: str | None, page: int, size: int) -> dict:
    stmt = select(KBArticle)
    if category:
        stmt = stmt.where(KBArticle.category == category)
    if term:
        pattern = f"%{term}%"
        stmt = stmt.where(KBArticle.title.ilike(pattern) | KBArticle.body.ilike(pattern))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(KBArticle.updated_at.desc()).offset((page - 1) * size).limit(size)).all()
    return {"items": rows, "total": total, "page": page, "size": size}


def search(db, query: str, provider, limit: int = 5) -> list[dict]:
    return search_kb(db, query, provider, limit=limit)
