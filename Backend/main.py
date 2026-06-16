from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database import AsyncSessionLocal, engine, Base
from app.rate_limit import limiter
from app.api.users import router as users_router
from app.api.trips import router as trips_router
from app.api.recommendations import router as recommendations_router
from app.api.forms import router as forms_router
from app.api.votes import router as votes_router
from app.api.ai_metrics import router as ai_metrics_router
from app.api.dashboard import router as dashboard_router
from app.services.template_seeder import seed_templates
import app.models
import logging

logger = logging.getLogger("voyant")

app = FastAPI(
    title="Voyant API",
    description="AI powered group travel planning",
    version="1.0.0",
)

# ── rate limiting ────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS (config-driven) ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── routers ──────────────────────────────────────────────────────────
app.include_router(users_router)
app.include_router(trips_router)
app.include_router(recommendations_router)
app.include_router(forms_router)
app.include_router(votes_router)
app.include_router(ai_metrics_router)
app.include_router(dashboard_router)

# ── Prometheus /metrics ──────────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.on_event("startup")
async def startup():
    if settings.SECRET_KEY == "changethislater":
        logger.warning(
            "SECRET_KEY is the insecure default. Set a real SECRET_KEY in .env "
            "before deploying to production."
        )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed_templates(db)
    logger.info("Startup complete; database ready.")


@app.get("/")
async def root():
    return {"message": "Welcome to Voyant API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}