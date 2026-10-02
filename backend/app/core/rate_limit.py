from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.rate_limit_storage,
    enabled=settings.enable_rate_limit,
    default_limits=["120/minute"],
)
