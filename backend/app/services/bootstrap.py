from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models import KBArticle, User
from app.schemas import KBArticleCreate
from app.services import kb_service

logger = get_logger("bootstrap")

SAMPLE_KB = [
    {
        "title": "VPN connection drops frequently",
        "category": "network",
        "body": "1) Run `ipconfig /renew` to refresh the DHCP lease. "
        "2) Ensure the VPN client is up to date. 3) Verify DNS resolves with `nslookup vpn.corp.internal`. "
        "4) If the tunnel drops every ~10 minutes, the session idle timeout or routing conflict is likely. "
        "Contact the network team with the client logs.",
    },
    {
        "title": "Outlook not syncing to the Exchange server",
        "category": "software",
        "body": "Restart Outlook in safe mode (Win: `outlook.exe /safe`). Clear the credentials in Windows "
        "Credential Manager, then relaunch. If the account shows 'disconnected', run the Outlook auto "
        "account repair and check the cached mode toggle.",
    },
    {
        "title": "Laptop battery drains quickly",
        "category": "hardware",
        "body": "Open power settings and check that the 'Best power efficiency' plan is active. Reduce screen "
        "brightness and disable Bluetooth when unused. Run `powercfg /batteryreport` to review battery "
        "health; if design capacity is below 70%, request a battery replacement.",
    },
    {
        "title": "Multi-factor authentication (MFA) locked out",
        "category": "access",
        "body": "In the identity portal, click 'Trouble signing in?' and use the recovery codes. If codes "
        "were not saved, an admin must reset MFA for the account. Administrators: use the 'Reset MFA' "
        "action in the admin console.",
    },
]


def _seed_admin(db) -> None:
    admin = db.scalar(select(User).where(User.email == settings.seed_admin_email))
    if admin:
        return
    user = User(
        email=settings.seed_admin_email,
        full_name="System Administrator",
        password_hash=hash_password(settings.seed_admin_password),
        role="admin",
    )
    db.add(user)
    db.commit()
    logger.info("Seeded admin user %s (change the default password!)", settings.seed_admin_email)


def _seed_kb(db) -> None:
    if db.scalar(select(func.count()).select_from(KBArticle)):
        return
    from app.ai.factory import get_ai_provider

    provider = get_ai_provider()
    for item in SAMPLE_KB:
        article = kb_service.create_article(db, None, KBArticleCreate(**item))
        kb_service.embed_article(db, article.id, provider)
    logger.info("Seeded %d sample KB articles", len(SAMPLE_KB))


def seed() -> None:
    try:
        db = SessionLocal()
        try:
            _seed_admin(db)
            _seed_kb(db)
        finally:
            db.close()
    except Exception:  # noqa: BLE001 - DB may not be ready yet; log and continue
        logger.exception("Bootstrap seeding failed")
