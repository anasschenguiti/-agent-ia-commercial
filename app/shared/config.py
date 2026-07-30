"""
Configuration centrale de l'application via Pydantic Settings.
Charge les variables d'environnement depuis le fichier .env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "Sales AI Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "*"
    ]

    # ── Base de données & Supabase ────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_commercial"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Celery ────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── LLM / OpenAI ──────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # ── Qdrant ────────────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    # ── HubSpot ───────────────────────────────────────────────────────
    HUBSPOT_API_KEY: str = ""

    # ── Odoo ──────────────────────────────────────────────────────────
    ODOO_URL: str = "https://your-odoo-instance.odoo.com"
    ODOO_DB: str = "your_db"
    ODOO_USER: str = "admin"
    ODOO_PASSWORD: str = ""

    # ── Email / SMTP ──────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@yourcompany.com"

    # ── WhatsApp Business API ─────────────────────────────────────────
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""

    # ── LinkedIn ──────────────────────────────────────────────────────
    LINKEDIN_ACCESS_TOKEN: str = ""

    # ── B2B Intelligence APIs (optionnels, self-service gratuit) ──────
    # Apollo.io : 10 000 credits/mois gratuits, signup en 2 min sur apollo.io
    # Permet de recuperer les emails + linkedin des decideurs B2B.
    # NOTE 2024 : les endpoints /mixed_companies et /people/match sont
    # verrouilles en plan gratuit. Le provider s'auto-desactive si 403.
    APOLLO_API_KEY: str = ""

    # Hunter.io : 25 calls/mois gratuits, signup en 30 sec sur hunter.io
    # Permet de recuperer les emails publics associes a un domaine.
    HUNTER_API_KEY: str = ""

    # Snov.io : 50 credits/mois gratuits, signup sur snov.io
    # Alternative a Hunter, surtout utile pour .ma, .fr, .eu.
    SNOVIO_API_KEY: str = ""

    # Bing Search : 1000 calls/mois gratuits sur microsoft.com/bing/apis
    # Si vide, fallback automatique sur DuckDuckGo HTML.
    BING_SEARCH_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
