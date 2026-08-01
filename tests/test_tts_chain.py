"""
Unit tests pour la chaîne de fallback TTS à 3 niveaux (Chatterbox, Edge-TTS, Piper) et le Circuit Breaker.
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.voice.tts import TTSService, TTSCircuitBreaker, ChatterboxSynthesizer
from app.shared.config import settings


@pytest.fixture
def tts_service():
    service = TTSService()
    service.timeout_sec = 0.5  # Court timeout pour tests d'exécution rapide
    service.circuit_breaker.threshold = 5
    service.circuit_breaker.cooldown_sec = 10.0
    service.circuit_breaker.record_success()  # Reset circuit breaker
    return service


@pytest.mark.asyncio
async def test_chatterbox_success(tts_service):
    """Test 1: Chatterbox réussit -> Tier 1 utilisé, Edge-TTS et Piper non appelés."""
    with patch.object(tts_service.chatterbox, "synthesize", new_callable=AsyncMock) as mock_chatterbox, \
         patch("edge_tts.Communicate") as mock_edge_tts, \
         patch.object(tts_service, "_synthesize_piper", new_callable=AsyncMock) as mock_piper:
        
        mock_chatterbox.return_value = b"RIFF_WAV_CHATTERBOX_AUDIO"

        audio_bytes, content_type = await tts_service.synthesize("Bonjour, marhaba")

        assert audio_bytes == b"RIFF_WAV_CHATTERBOX_AUDIO"
        assert content_type == "audio/wav"
        mock_chatterbox.assert_called_once()
        mock_edge_tts.assert_not_called()
        mock_piper.assert_not_called()


@pytest.mark.asyncio
async def test_chatterbox_timeout_fallback_to_edgetts(tts_service):
    """Test 2: Chatterbox échoue/expire -> Tier 2 (Edge-TTS) est exécuté."""
    async def delayed_chatterbox(*args, **kwargs):
        await asyncio.sleep(2.0)  # Supérieur au timeout_sec (0.5s)
        return b"TOO_LATE"

    async def mock_communicate_save(tmp_path):
        with open(tmp_path, "wb") as f:
            f.write(b"ID3_MP3_EDGETTS_AUDIO")

    with patch.object(tts_service.chatterbox, "synthesize", side_effect=delayed_chatterbox), \
         patch("edge_tts.Communicate") as mock_edge_class, \
         patch.object(tts_service, "_synthesize_piper", new_callable=AsyncMock) as mock_piper:

        mock_instance = MagicMock()
        mock_instance.save = AsyncMock(side_effect=mock_communicate_save)
        mock_edge_class.return_value = mock_instance

        audio_bytes, content_type = await tts_service.synthesize("Marhaba bkom")

        assert audio_bytes == b"ID3_MP3_EDGETTS_AUDIO"
        assert content_type == "audio/mpeg"
        mock_piper.assert_not_called()


@pytest.mark.asyncio
async def test_chatterbox_and_edgetts_failure_fallback_to_piper(tts_service):
    """Test 3: Chatterbox et Edge-TTS échouent tous les deux -> Piper garanti est utilisé (voix arabe)."""
    with patch.object(tts_service.chatterbox, "synthesize", side_effect=RuntimeError("Chatterbox Error")), \
         patch("edge_tts.Communicate", side_effect=RuntimeError("EdgeTTS Network Drop")), \
         patch.object(tts_service, "_synthesize_piper", new_callable=AsyncMock) as mock_piper:

        mock_piper.return_value = b"RIFF_WAV_PIPER_ARABIC_AUDIO"

        audio_bytes, content_type = await tts_service.synthesize("Ahlan wa sahlan")

        assert audio_bytes == b"RIFF_WAV_PIPER_ARABIC_AUDIO"
        assert content_type == "audio/wav"
        mock_piper.assert_called_once()


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_5_failures(tts_service):
    """Test 4: Disjoncteur s'ouvre après 5 échecs consécutifs d'Edge-TTS et le saute sur les requêtes suivantes."""
    with patch.object(tts_service.chatterbox, "synthesize", side_effect=RuntimeError("Chatterbox Down")), \
         patch("edge_tts.Communicate", side_effect=RuntimeError("Edge-TTS Cut Off")), \
         patch.object(tts_service, "_synthesize_piper", new_callable=AsyncMock) as mock_piper:

        mock_piper.return_value = b"PIPER_FALLBACK"

        # Simule 5 échecs consécutifs d'Edge-TTS
        for _ in range(5):
            await tts_service.synthesize("Test failure")

        assert tts_service.circuit_breaker.is_open() is True

        # La 6ème requête doit SAUTER Edge-TTS directement sans tenter Communicate
        with patch("edge_tts.Communicate") as mock_edge_class:
            audio_bytes, content_type = await tts_service.synthesize("Request during open circuit")

            assert audio_bytes == b"PIPER_FALLBACK"
            mock_edge_class.assert_not_called()


@pytest.mark.asyncio
async def test_langfuse_tracing_event(tts_service):
    """Test 5: Instrument avec événements de traçabilité Langfuse lors des fallbacks."""
    with patch.object(tts_service.chatterbox, "synthesize", side_effect=RuntimeError("Chatterbox Fail")), \
         patch.object(tts_service, "_synthesize_piper", new_callable=AsyncMock) as mock_piper, \
         patch.object(tts_service, "_log_langfuse_trace") as mock_trace_log:

        mock_piper.return_value = b"PIPER_AUDIO"

        await tts_service.synthesize("Trace test")

        mock_trace_log.assert_called_once()
        _, kwargs = mock_trace_log.call_args
        assert kwargs["tier_used"] in ["piper", "piper_guaranteed_offline"]
        assert len(kwargs["skipped_tiers"]) >= 1
