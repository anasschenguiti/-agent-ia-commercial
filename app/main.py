"""
Point d'entree principal de l'application FastAPI.

Features:
- CORS durci & slowapi Limiter.
- Middleware GZip + En-têtes de sécurité HTTP.
- Structlog (JSON prod) & OpenTelemetry tracing.
- Probes /health/live et /health/ready.
"""

from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.prospection.router import router as prospection_router
from app.conversation.router import router as conversation_router
from app.crm.router import router as crm_router
from app.scheduling.router import router as scheduling_router
from app.communication.router import router as communication_router
from app.voice.router import router as voice_router
from app.shared.auth_router import router as auth_router
from app.analysis.router import router as analysis_router
from app.shared.database import init_db, seed_users, seed_prospects, AsyncSessionLocal
from app.shared.redis_client import get_redis_client
from app.conversation.rag import RAGPipeline
from app.shared.supabase_client import check_supabase_health
from app.shared.config import settings
from app.shared.logging_config import configure_logging, setup_opentelemetry

# Import models to ensure they register on Base.metadata
from app.prospection.models_sql import ProspectSQL
from app.conversation.models_sql import MessageSQL
from app.shared.models_sql import UserSQL
from app.analysis.models_sql import ProspectAnalysisSQL

# ── Configurer les logs structurés structlog ───────────────────────────
configure_logging()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injecte des en-têtes HTTP de sécurité de niveau entreprise."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:;"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_users()
    await seed_prospects()
    yield


# ── Limiter (slowapi) ──────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


app = FastAPI(
    title="Sales AI Agent",
    description="Agent IA de prospection et de vente automatise (IKSATECH)",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter

# ── Middlewares : GZip, Security Headers & CORS ────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)

# ── OpenTelemetry setup ────────────────────────────────────────────────
setup_opentelemetry(app)


# ── Global & Rate-limit error handlers ──────────────────────────────────
@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Trop de requetes. Reessayez plus tard."},
        headers={"Retry-After": str(exc.detail), "Access-Control-Allow-Origin": "*"},
    )


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erreur serveur interne: {str(exc)}"},
        headers={"Access-Control-Allow-Origin": "*"},
    )


# ── Routers ────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(prospection_router, prefix="/api/prospection", tags=["Prospection"])
app.include_router(analysis_router)
app.include_router(conversation_router, prefix="/api/conversation", tags=["Conversation"])
app.include_router(crm_router, prefix="/api/crm", tags=["CRM"])
app.include_router(scheduling_router, prefix="/api/scheduling", tags=["Scheduling"])
app.include_router(communication_router, prefix="/api/communication", tags=["Communication"])
app.include_router(voice_router, prefix="/api/v1", tags=["Voice Agent AI"])


# ── Endpoints Racine / Sante ───────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Bienvenue sur Sales AI Agent API (IKSATECH)",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/health/live",
        "status": "online",
    }


@app.get("/health/live", tags=["Health"])
async def health_live():
    """Liveness probe : toujours 200, doit repondre en <50ms."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
async def health_ready():
    """Readiness probe : remonte les dependances. Cache 30s en Redis."""
    cache_key = "health:ready:snapshot"
    ttl = 30

    try:
        r = await get_redis_client()
        cached = await r.get(cache_key)
        if cached:
            import json
            return json.loads(cached)
    except Exception:
        r = None

    started = time.time()
    health_status = {
        "status": "ok",
        "version": "1.0.0",
        "services": {
            "postgres": "unknown",
            "redis": "unknown",
            "qdrant": "unknown",
            "supabase": "unknown",
        },
    }

    # Postgres
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(ProspectSQL.__table__.select().limit(1))
            health_status["services"]["postgres"] = "online"
    except Exception as e:
        health_status["services"]["postgres"] = f"offline: {e}"

    # Redis
    if r is not None:
        try:
            await r.ping()
            health_status["services"]["redis"] = "online"
        except Exception as e:
            health_status["services"]["redis"] = f"offline: {e}"
    else:
        health_status["services"]["redis"] = "offline: client init failed"

    # Qdrant
    try:
        rag = RAGPipeline()
        health_status["services"]["qdrant"] = "online" if rag.client else "offline"
    except Exception as e:
        health_status["services"]["qdrant"] = f"offline: {e}"

    # Supabase
    try:
        health_status["services"]["supabase"] = await check_supabase_health()
    except Exception as e:
        health_status["services"]["supabase"] = f"offline: {e}"

    # Overall status
    services = health_status["services"]
    if any(str(v).startswith("offline") for v in services.values()):
        health_status["status"] = "degraded"

    health_status["latency_ms"] = round((time.time() - started) * 1000, 1)

    # Cache snapshot for 30s
    if r is not None:
        try:
            import json
            await r.set(cache_key, json.dumps(health_status), ex=ttl)
        except Exception:
            pass

    return health_status


@app.get("/health", tags=["Health"])
async def health_legacy():
    return await health_ready()
