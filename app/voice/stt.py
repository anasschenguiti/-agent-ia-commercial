"""
Module de Reconnaissance Vocale (Speech-to-Text) 100% Gratuit & Auto-Hébergé.
Utilise Faster-Whisper avec le modèle 'small'/'medium' pour transcrire le vocal en Darija, Arabe ou Français.
"""
import io
import os
import logging
import tempfile
from typing import Optional, Dict, Any
from app.shared.config import settings

logger = logging.getLogger("sales_ai.voice.stt")

class STTService:
    """Service de transcription audio vers texte (Speech-to-Text)."""

    def __init__(self):
        self.engine = settings.STT_ENGINE
        self.model_size = settings.STT_MODEL_SIZE
        self.model = None
        self._init_model()

    def _init_model(self):
        """Initialise le modèle Faster-Whisper de manière paresseuse."""
        if self.engine == "faster_whisper":
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Chargement du modèle Faster-Whisper ({self.model_size})...")
                # Utilise int8 sur CPU pour une transcription instantanée et stable
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                logger.info("Modèle Faster-Whisper chargé avec succès.")
            except Exception as e:
                logger.warning(f"Impossible de charger Faster-Whisper (fallback actif) : {e}")
                self.model = None

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm", language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcrit les octets audio (WebM, WAV, MP3) en texte (Darija / Arabe / Français / Anglais).
        """
        if not audio_bytes or len(audio_bytes) == 0:
            return {"text": "", "detected_language": "UNKNOWN", "language_probability": 0.0}

        # 1. Utilisation de Faster-Whisper si disponible
        if self.model:
            try:
                ext = os.path.splitext(filename)[1] or ".webm"
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name

                # Transcrit avec filtrage Silero VAD
                use_vad = (settings.STT_VAD_ENGINE == "silero_vad")
                segments, info = self.model.transcribe(
                    tmp_path,
                    language=language,  # None = Détection automatique multilingue (EN, FR, AR, Darija)
                    beam_size=5,
                    vad_filter=use_vad,
                    vad_parameters=dict(min_silence_duration_ms=500) if use_vad else None,
                )
                text = " ".join([segment.text for segment in segments]).strip()
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

                if text:
                    logger.info(f"Transcription STT (Langue détectée: {info.language}, Confiance: {info.language_probability:.2f}) : '{text}'")
                    return {
                        "text": text,
                        "detected_language": info.language.upper(),
                        "language_probability": round(info.language_probability, 2)
                    }
            except Exception as e:
                logger.error(f"Erreur lors de la transcription Faster-Whisper : {e}")

        return {"text": "", "detected_language": "UNKNOWN", "language_probability": 0.0}
