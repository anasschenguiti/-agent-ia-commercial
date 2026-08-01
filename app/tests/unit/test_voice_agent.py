"""
Tests unitaires pour le module Voice Agent AI (STT, TTS et FastAPI router).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.voice.stt import STTService
from app.voice.tts import TTSService
from app.voice.agent_voice import VoiceAgent


@pytest.mark.asyncio
async def test_voice_config_endpoint():
    """Vérifie l'endpoint /api/v1/voice/config."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/voice/config")
        assert response.status_code == 200
        data = response.json()
        assert "llm_provider" in data
        assert "stt_engine" in data
        assert "tts_engine" in data


@pytest.mark.asyncio
async def test_stt_transcribe_fallback():
    """Vérifie le fonctionnement du service STT (transcription)."""
    stt = STTService()
    transcript = await stt.transcribe(b"fake audio data", filename="sample.webm")
    assert isinstance(transcript, dict)
    assert "text" in transcript
    assert transcript["text"] == ""  # fallback: pas de transcription reussie


@pytest.mark.asyncio
async def test_tts_synthesize():
    """Vérifie la génération de synthèse vocale TTS."""
    tts = TTSService()
    audio_bytes, content_type = await tts.synthesize("Salam, marhaba bikom f IKSATECH", language_hint="ar")
    assert isinstance(audio_bytes, bytes)
    assert content_type == "audio/mpeg"


@pytest.mark.asyncio
async def test_voice_agent_orchestration():
    """Vérifie l'orchestration complète VoiceAgent (STT -> LLM -> TTS)."""
    agent_voice = VoiceAgent(session_id="test_voice_session")
    res = await agent_voice.process_voice_interaction(b"audio test binary", filename="test.webm")

    assert "session_id" in res
    assert "user_transcript" in res
    assert "agent_response" in res
    assert "audio_base64" in res
    assert "metrics" in res
    assert res["metrics"]["total_duration_sec"] >= 0
