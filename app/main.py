"""
Point d'entrée principal de l'application FastAPI.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.prospection.router import router as prospection_router
from app.conversation.router import router as conversation_router
from app.crm.router import router as crm_router
from app.scheduling.router import router as scheduling_router
from app.communication.router import router as communication_router
from app.shared.auth_router import router as auth_router
from app.analysis.router import router as analysis_router
from app.shared.database import init_db, seed_users, AsyncSessionLocal
from app.shared.redis_client import get_redis_client
from app.conversation.rag import RAGPipeline

from app.shared.supabase_client import check_supabase_health

# Import models to ensure they register on Base.metadata
from app.prospection.models_sql import ProspectSQL
from app.conversation.models_sql import MessageSQL
from app.shared.models_sql import UserSQL
from app.analysis.models_sql import ProspectAnalysisSQL


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise les tables en base de données au démarrage
    await init_db()
    # Seede l'utilisateur admin par défaut
    await seed_users()
    yield


app = FastAPI(
    title="Sales AI Agent",
    description="Agent IA de prospection et de vente automatisé (IKSATECH)",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routers
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(prospection_router, prefix="/api/prospection", tags=["Prospection"])
app.include_router(analysis_router)
app.include_router(conversation_router, prefix="/api/conversation", tags=["Conversation"])
app.include_router(crm_router, prefix="/api/crm", tags=["CRM"])
app.include_router(scheduling_router, prefix="/api/scheduling", tags=["Scheduling"])
app.include_router(communication_router, prefix="/api/communication", tags=["Communication"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Bienvenue sur Sales AI Agent API (IKSATECH)",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/health",
        "status": "online"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de santé détaillé contrôlant Postgres, Redis, Qdrant et Supabase."""
    health_status = {
        "status": "ok",
        "version": "1.0.0",
        "services": {
            "postgres": "unknown",
            "redis": "unknown",
            "qdrant": "unknown",
            "supabase": "unknown"
        }
    }

    # 1. Test Postgres
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(ProspectSQL.__table__.select().limit(1))
            health_status["services"]["postgres"] = "online"
    except Exception as e:
        health_status["services"]["postgres"] = f"offline: {e}"

    # 2. Test Redis
    try:
        r = await get_redis_client()
        await r.ping()
        health_status["services"]["redis"] = "online"
    except Exception as e:
        health_status["services"]["redis"] = f"offline: {e}"

    # 3. Test Qdrant
    try:
        rag = RAGPipeline()
        health_status["services"]["qdrant"] = "online" if rag.vector_store else "offline"
    except Exception as e:
        health_status["services"]["qdrant"] = f"offline: {e}"

    # 4. Test Supabase
    try:
        health_status["services"]["supabase"] = await check_supabase_health()
    except Exception as e:
        health_status["services"]["supabase"] = f"offline: {e}"

    return health_status
