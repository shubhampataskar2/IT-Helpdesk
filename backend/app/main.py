from contextlib import asynccontextmanager

from anyio import to_thread
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1 import admin, analytics, auth, kb, tickets, users
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.core.database import init_db
from app.services.bootstrap import seed

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await to_thread.run_sync(init_db)
    await to_thread.run_sync(seed)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded, slow down."})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, users.router, tickets.router, kb.router, analytics.router, admin.router):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": settings.app_name}
