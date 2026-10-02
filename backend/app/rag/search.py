import re

from sqlalchemy import func, or_, select, text

from app.ai.heuristic import vector_to_string
from app.models import KBArticle, Ticket


def _like_escaped(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _is_postgres(db) -> bool:
    return db.bind.dialect.name == "postgresql"


def has_embeddings(db) -> bool:
    if not _is_postgres(db):
        return False
    total = db.scalar(select(func.count()).select_from(KBArticle))
    embedded = db.scalar(
        select(func.count()).select_from(KBArticle).where(KBArticle.embedding.is_not(None))
    )
    return bool(total and embedded)


def search_kb(db, query: str, provider, limit: int = 5) -> list[dict]:
    """Vector search over pgvector when embeddings exist, otherwise keyword fallback."""
    if has_embeddings(db):
        vec = provider.embed(query)
        sql = text(
            """
            SELECT id, title, body, category,
                   1 - (embedding <=> CAST(:emb AS vector)) AS sim
            FROM kb_articles
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :lim
            """
        )
        rows = db.execute(sql, {"emb": vector_to_string(vec), "lim": limit}).mappings().all()
        hits = [
            {
                "article_id": r["id"],
                "title": r["title"],
                "body": r["body"],
                "category": r["category"],
                "score": round(float(r["sim"]), 4),
            }
            for r in rows
            if float(r["sim"]) >= 0.05
        ]
        if hits:
            return hits

    term = _like_escaped(query)
    pattern = f"%{term}%"
    stmt = (
        select(KBArticle)
        .where(
            or_(
                KBArticle.title.ilike(pattern, escape="\\"),
                KBArticle.body.ilike(pattern, escape="\\"),
            )
        )
        .limit(limit)
    )
    return [
        {
            "article_id": a.id,
            "title": a.title,
            "body": a.body,
            "category": a.category,
            "score": None,
        }
        for a in db.scalars(stmt)
    ]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def detect_duplicate(db, provider, ticket_text: str, exclude_id: int, threshold: float) -> tuple[int, float] | None:
    """Return (ticket_id, similarity) of the most similar active ticket, if any.

    Vector similarity (pgvector) is the primary signal, blended with a token
    Jaccard term so that the heuristic provider still produces meaningful
    matches without embeddings from a remote model.
    """
    rows = []
    if _is_postgres(db):
        vec = provider.embed(ticket_text)
        sql = text(
            """
            SELECT id, 1 - (description_embedding <=> CAST(:emb AS vector)) AS sim
            FROM tickets
            WHERE description_embedding IS NOT NULL
              AND status IN ('new', 'open', 'in_progress')
              AND id != :exclude
            ORDER BY description_embedding <=> CAST(:emb AS vector)
            LIMIT 8
            """
        )
        rows = db.execute(sql, {"emb": vector_to_string(vec), "exclude": exclude_id}).mappings().all()
    if not rows:
        return None

    query_tokens = _tokens(ticket_text)
    best: tuple[int, float] | None = None
    for row in rows:
        sim = float(row["sim"])
        if provider.kind == "heuristic":
            stored = db.get(Ticket, row["id"])
            if stored is None:
                continue
            stored_tokens = _tokens(f"{stored.title} {stored.description}")
            union = query_tokens | stored_tokens
            jaccard = len(query_tokens & stored_tokens) / len(union) if union else 0.0
            sim = 0.6 * sim + 0.4 * jaccard
        if best is None or sim > best[1]:
            best = (int(row["id"]), sim)
    candidate_id, candidate_sim = best  # type: ignore[misc]
    if candidate_sim >= threshold:
        return candidate_id, candidate_sim
    return None
