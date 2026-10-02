from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.services import email_service, ticket_service
from app.services.sla_service import check_overdue
from app.workers.celery_app import celery_app

logger = get_logger("tasks")


@celery_app.task(name="app.workers.tasks.analyze_ticket")
def analyze_ticket(ticket_id: int) -> str:
    db = SessionLocal()
    try:
        ticket_service.run_ticket_analysis(db, ticket_id)
        logger.info("Analysis complete for ticket %s", ticket_id)
        return "ok"
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.embed_article")
def embed_article(article_id: int) -> str:
    from app.ai.factory import get_ai_provider
    from app.services import kb_service

    db = SessionLocal()
    try:
        kb_service.embed_article(db, article_id, get_ai_provider())
        logger.info("Embedded article %s", article_id)
        return "ok"
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.sla_check")
def sla_check() -> dict:
    db = SessionLocal()
    try:
        overdue = check_overdue(db)
        escalated = 0
        response_ids = {t.id for t in overdue["response"]}
        resolve_ids = {t.id for t in overdue["resolve"]}
        for ticket in overdue["response"] + overdue["resolve"]:
            if ticket.escalated:
                continue
            ticket.escalated = True
            kind = "response+resolve" if ticket.id in response_ids and ticket.id in resolve_ids else (
                "resolve" if ticket.id in resolve_ids else "response"
            )
            email_service.notify_sla_breach(ticket, kind)
            escalated += 1
        db.commit()
        logger.info("SLA check done, %s escalated", escalated)
        return {"response": len(overdue["response"]), "resolve": len(overdue["resolve"]),
                "escalated": escalated}
    finally:
        db.close()
