"""
Configuration centrale de l'application via Pydantic Settings.
Charge les variables d'environnement depuis le fichier .env.

SECURITE (Week 1):
- SECRET_KEY ne peut PAS etre une valeur par defaut connue.
- ADMIN_BOOTSTRAP_TOKEN doit etre defini pour permettre /api/auth/register.
- Le constructeur leve une RuntimeError si l'app demarre avec une cle faible.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, field_validator
from typing import List


# Placeholders consideres comme "non-securises" => l'app refuse de demarrer.
_WEAK_SECRETS = {
    "change-me-in-production",
    "change-me-with-a-long-random-string",
    "change-me-admin-bootstrap-token",
    "dev-secret-key-sales-ai-agent-2026",
}


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "Sales AI Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # SECRET_KEY utilisee pour signer les JWT. SecretStr evite l'affichage
    # accidentel dans les logs / repr(). La validation ci-dessous refuse
    # les placeholders connus.
    SECRET_KEY: SecretStr

    # Token requis pour creer un nouvel utilisateur via /api/auth/register.
    ADMIN_BOOTSTRAP_TOKEN: SecretStr = SecretStr("")

    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

    # ── Base de donnees & Supabase ───────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_commercial"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Celery ────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── LLM / OpenAI & Ollama Local (Qwen 2.5) ───────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    LLM_PROVIDER: str = "ollama"  # "ollama" ou "openai"
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    # Base modele recommande (qwen2.5:7b-instruct ~= 4.7 GB).
    # NOTE (Week 2): le projet n'effectue AUCUN fine-tuning LoRA/PEFT.
    # La qualite Darija / multilingue est obtenue par prompt engineering
    # via Ollama SYSTEM dans le Modelfile.
    OLLAMA_MODEL: str = "qwen2.5:7b-instruct"

    # ── Voice / STT & TTS ─────────────────────────────────────────────
    STT_ENGINE: str = "faster_whisper"  # "faster_whisper", "openai"
    STT_MODEL_SIZE: str = "distil-large-v3"  # "medium", "distil-large-v3"
    STT_VAD_ENGINE: str = "silero_vad"

    TTS_ENGINE: str = "chatterbox"  # "chatterbox", "edge_tts", "piper"
    TTS_FALLBACK_ORDER: str = "chatterbox,edge_tts,piper"
    TTS_REFERENCE_VOICE_PATH: str = "assets/voices/darija_reference.wav"
    TTS_TIER_TIMEOUT_MS: int = 3000
    TTS_CIRCUIT_BREAKER_THRESHOLD: int = 5
    TTS_CIRCUIT_BREAKER_COOLDOWN_SEC: int = 300
    TTS_PIPER_MODEL_PATH: str = "assets/piper/ar_JO-kareem-low.onnx"
    TTS_VOICE_DARIJA: str = "ar-MA-JamalNeural"
    TTS_VOICE_FRENCH: str = "fr-FR-HenriNeural"

    # ── Calendar (tokens OAUTH2 dedies) ──────────────────────────────
    GOOGLE_CALENDAR_TOKEN: str = ""
    OUTLOOK_TOKEN: str = ""

    # ── Qdrant ────────────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    # ── HubSpot ──────────────────────────────────────────────────────
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
    SMTP_SECURE: bool = True
    FROM_EMAIL: str = "noreply@yourcompany.com"

    # ── WhatsApp Business API ─────────────────────────────────────────
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""

    # ── LinkedIn ──────────────────────────────────────────────────────
    LINKEDIN_ACCESS_TOKEN: str = ""

    # ── B2B Intelligence APIs ─────────────────────────────────────────
    APOLLO_API_KEY: str = ""
    HUNTER_API_KEY: str = ""
    SNOVIO_API_KEY: str = ""
    BING_SEARCH_API_KEY: str = ""

    # ── Langfuse (LLM tracing, Week 3) ────────────────────────────────
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3000"

    # ── OpenTelemetry (Week 3) ───────────────────────────────────────
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "sales-agent-api"

    # ── Frontend (Next.js) ────────────────────────────────────────────
    NEXT_PUBLIC_BACKEND_URL: str = "http://localhost:8000"

    # ── Validators (Week 1 hardening) ─────────────────────────────────
    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def _validate_secret_key(cls, v):
        """Refuse un SECRET_KEY faible ou egal a un placeholder connu."""
        if v is None:
            raise ValueError("SECRET_KEY est obligatoire")
        # Accepte soit une SecretStr, soit une str brute
        raw = v.get_secret_value() if hasattr(v, "get_secret_value") else str(v)
        if raw in _WEAK_SECRETS:
            raise ValueError(
                "SECRET_KEY est un placeholder connu. Definit une vraie cle "
                "dans .env : python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        if len(raw) < 32:
            raise ValueError("SECRET_KEY doit faire au moins 32 caracteres")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _normalize_allowed_origins(cls, v):
        """Refuse '*' dans la liste (incompatible avec allow_credentials=True)."""
        if isinstance(v, str):
            v = [o.strip() for o in v.split(",") if o.strip()]
        if isinstance(v, list) and "*" in v:
            raise ValueError(
                "ALLOWED_ORIGINS ne peut pas contenir '*' "
                "(incompatible avec allow_credentials=True du CORS)."
            )
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
