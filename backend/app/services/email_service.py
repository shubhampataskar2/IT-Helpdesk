import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from app.core.config import settings
from app.models import Ticket

logger = logging.getLogger("helpdesk.email")


def send_email(to: str, subject: str, html: str) -> None:
    if not settings.mail_enabled or not settings.mail_host:
        logger.info("Email (skipped, SMTP disabled) to=%s subject=%s body=%s", to, subject, html[:800])
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(settings.mail_host, settings.mail_port, timeout=15) as server:
            server.starttls()
            if settings.mail_username:
                server.login(settings.mail_username, settings.mail_password)
            server.sendmail(settings.mail_from, [to], msg.as_string())
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send email to %s", to)


def _ticket_url(ticket_id: int) -> str:
    return f"{settings.frontend_url}/tickets/{ticket_id}"


def _base_html(ticket: Ticket, content: str) -> str:
    return (
        "<div style=\"font-family:Arial,sans-serif;max-width:600px;margin:auto;border:1px solid #e5e7eb;"
        "border-radius:8px;overflow:hidden\">"
        "<div style=\"background:#4338ca;color:#fff;padding:16px 24px;\">"
        f"<b>IT Helpdesk</b> &mdash; {escape(ticket.number)}</div>"
        f"<div style=\"padding:24px;\"><p style=\"color:#111827;\">{content}</p>"
        f"<p><a href=\"{ _ticket_url(ticket.id) }\" style=\"background:#4338ca;color:#fff;padding:10px 16px;"
        "border-radius:6px;text-decoration:none;\">View ticket</a></p></div></div>"
    )


def notify_ticket_created(ticket: Ticket, analysis_summary: str) -> None:
    html = _base_html(
        ticket,
        f"Your ticket was received with priority <b>{escape(ticket.priority)}</b> and category "
        f"<b>{escape(ticket.category)}</b>.<br><br>AI summary:<br>{escape(analysis_summary)}",
    )
    send_email(ticket.creator.email, f"[{ticket.number}] Ticket created", html)


def notify_ticket_assigned(ticket: Ticket, assignee_email: str, assigner_name: str) -> None:
    html = _base_html(ticket, f"Ticket assigned to you by <b>{escape(assigner_name)}</b>.")
    send_email(assignee_email, f"[{ticket.number}] Ticket assigned", html)


def notify_ticket_resolved(ticket: Ticket) -> None:
    html = _base_html(
        ticket,
        f"Ticket <b>{escape(ticket.title)}</b> has been resolved. Please verify and close it "
        "or reopen if the issue persists.",
    )
    send_email(ticket.creator.email, f"[{ticket.number}] Ticket resolved", html)


def notify_status_change(ticket: Ticket) -> None:
    html = _base_html(ticket, f"Ticket status changed to <b>{escape(ticket.status)}</b>.")
    send_email(ticket.creator.email, f"[{ticket.number}] Status update", html)


def notify_duplicate(ticket: Ticket, original: Ticket) -> None:
    html = _base_html(
        ticket,
        f"Your ticket appears to be a duplicate of <b>{escape(original.number)}</b>. "
        "A support engineer will consolidate the cases.",
    )
    send_email(ticket.creator.email, f"[{ticket.number}] Possibly duplicate ticket", html)


def notify_sla_breach(ticket: Ticket, kind: str) -> None:
    html = _base_html(ticket, f"SLA <b>{kind}</b> breach detected for this ticket.")
    recipients = {ticket.assignee.email} if ticket.assignee else set()
    for email in recipients:
        send_email(email, f"[{ticket.number}] SLA breach", html)
