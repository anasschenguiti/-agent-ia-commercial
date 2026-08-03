"""
Module de Synthèse Vocale (Text-to-Speech) 100% Gratuit & Auto-Hébergé.
Chaîne de fallback à 3 niveaux pour la voix marocaine Darija (Chatterbox, Edge-TTS, Piper).
"""
import io
import os
import time
import logging
import asyncio
import tempfile
import struct
import wave
from typing import Tuple, AsyncGenerator, List, Dict, Any, Optional
from app.shared.config import settings

logger = logging.getLogger("sales_ai.voice.tts")


class TTSCircuitBreaker:
    """Disjoncteur (Circuit Breaker) pour protéger le temps de latence contre les pannes d'Edge-TTS."""

    def __init__(self, threshold: int = 5, cooldown_sec: float = 300.0):
        self.threshold = threshold
        self.cooldown_sec = cooldown_sec
        self.failure_count = 0
        self.last_failure_time = 0.0

    def is_open(self) -> bool:
        """Retourne True si le disjoncteur est OUVERT (service ignoré)."""
        if self.failure_count >= self.threshold:
            if time.time() - self.last_failure_time < self.cooldown_sec:
                return True
            # Réinitialisation après expiration du cooldown
            self.failure_count = 0
        return False

    def record_failure(self):
        """Enregistre un échec de service."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.threshold:
            logger.warning(f"[TTS CircuitBreaker] Seuil d'échecs atteint ({self.failure_count}). Disjoncteur OUVERT pendant {self.cooldown_sec}s.")

    def record_success(self):
        """Réinitialise le compteur après un succès."""
        self.failure_count = 0


class ChatterboxSynthesizer:
    """Synthétiseur Chatterbox Multilingual v3 avec clonage de voix (MIT License)."""

    def __init__(self, ref_voice_path: str):
        self.ref_voice_path = ref_voice_path
        self._model = None

    async def synthesize(self, text: str) -> bytes:
        """Clone la voix à partir du fichier audio de référence et synthétise le texte."""
        if not os.path.exists(self.ref_voice_path):
            raise FileNotFoundError(f"Échantillon de voix de référence introuvable: {self.ref_voice_path}")

        try:
            from chatterbox_tts import ChatterboxMultilingual
            if self._model is None:
                self._model = ChatterboxMultilingual.from_pretrained("resemble-ai/chatterbox-multilingual-v3")
            
            audio = await asyncio.to_thread(
                self._model.synthesize,
                text=text,
                audio_prompt_path=self.ref_voice_path
            )
            return audio
        except Exception as exc:
            raise RuntimeError(f"Chatterbox TTS indisponible ou non installé: {exc}")


class TTSService:
    """Service de synthèse vocale résilient à 3 niveaux (Chatterbox -> Edge-TTS -> Piper)."""

    def __init__(self):
        self.timeout_sec = float(settings.TTS_TIER_TIMEOUT_MS) / 1000.0
        self.circuit_breaker = TTSCircuitBreaker(
            threshold=settings.TTS_CIRCUIT_BREAKER_THRESHOLD,
            cooldown_sec=float(settings.TTS_CIRCUIT_BREAKER_COOLDOWN_SEC)
        )
        self.chatterbox = ChatterboxSynthesizer(settings.TTS_REFERENCE_VOICE_PATH)
        self.piper_model_path = settings.TTS_PIPER_MODEL_PATH
        self.darija_voice = settings.TTS_VOICE_DARIJA
        self.french_voice = settings.TTS_VOICE_FRENCH

    def _detect_language(self, text: str) -> str:
        """Détecte précisément si le texte est en Français ('fr'), Anglais ('en') ou Darija/Arabe ('ar')."""
        if not text:
            return "ar"

        # 1. Détection des caractères arabes
        if any("\u0600" <= char <= "\u06FF" for char in text):
            return "ar"

        text_lower = text.lower()

        # 2. Score Mots-clés Français
        fr_keywords = [
            "bonjour", "souhaite", "excellente", "journée", "comment", "pouvez", "pouvoir", "proposons",
            "création", "sur-mesure", "tarifs", "tarif", "solution", "solutions", "échange", "minutes",
            "besoin", "besoins", "souhaitez", "équipe", "expert", "experts", "discuter", "service",
            "services", "nous", "vous", "avec", "pour", "dans", "cette", "votre", "nos", "plus",
            "demande", "devis", "gratuit", "contact", "développement"
        ]
        fr_score = sum(1 for kw in fr_keywords if kw in text_lower)
        if any(c in text for c in ["é", "è", "ê", "à", "ç", "ù"]):
            fr_score += 3

        # 3. Score Mots-clés Anglais
        en_keywords = [
            "hello", "hi", "good", "morning", "afternoon", "evening", "welcome", "how", "can", "help",
            "assist", "offer", "provide", "website", "custom", "starting", "from", "talk", "discuss",
            "requirements", "call", "schedule", "meeting", "thanks", "thank", "you", "our", "your",
            "team", "expert", "experts", "free", "quote", "contact", "development"
        ]
        en_score = sum(1 for kw in en_keywords if kw in text_lower)

        if fr_score > en_score and fr_score >= 2:
            return "fr"
        elif en_score > fr_score and en_score >= 2:
            return "en"
        elif fr_score >= 1 and fr_score > en_score:
            return "fr"
        elif en_score >= 1:
            return "en"
        else:
            return "ar"

    def _select_voice(self, text: str) -> tuple:
        """Retourne (voice_name, rate) adapté à la langue détectée."""
        lang = self._detect_language(text)
        if lang == "en":
            # Aria : voix anglaise naturelle, chaleureuse et professionnelle
            return "en-US-AriaNeural", "+0%"
        elif lang == "fr":
            # Vivienne Multilinguale : voix française fluide et naturelle
            return (self.french_voice or "fr-FR-VivienneMultilingualNeural"), "+10%"
        else:
            # Mouna : voix féminine marocaine naturelle (meilleure que Jamal pour la Darija)
            return (self.darija_voice or "ar-MA-MounaNeural"), "-5%"

    async def synthesize(self, text: str, language_hint: str = "ar") -> Tuple[bytes, str]:
        """
        Synthétise le texte avec une chaîne de fallback ordonnée :
        1. Chatterbox (Clonage local) — Timeout 3s
        2. Edge-TTS (ar-MA-JamalNeural) — Timeout 3s avec Circuit Breaker
        3. Piper (ar_JO-kareem-low) — Niveau garanti offline (voix arabe)
        """
        if not text:
            return b"", "audio/mpeg"

        start_time = time.time()
        skipped_tiers: List[Dict[str, Any]] = []
        tier_used: Optional[str] = None
        audio_bytes = b""
        content_type = "audio/mpeg"

        fallback_order = [t.strip() for t in settings.TTS_FALLBACK_ORDER.split(",") if t.strip()]

        for tier in fallback_order:
            tier_start = time.time()

            # TIER 1: Chatterbox Multilingual v3 (Local Voice Cloning)
            if tier == "chatterbox":
                try:
                    audio_bytes = await asyncio.wait_for(
                        self.chatterbox.synthesize(text),
                        timeout=self.timeout_sec
                    )
                    if audio_bytes:
                        tier_used = "chatterbox"
                        content_type = "audio/wav"
                        break
                except Exception as e:
                    skipped_tiers.append({
                        "tier": "chatterbox",
                        "reason": str(e),
                        "latency_ms": round((time.time() - tier_start) * 1000, 2)
                    })

            # TIER 2: Edge-TTS (ar-MA-JamalNeural) avec Circuit Breaker
            elif tier == "edge_tts":
                if self.circuit_breaker.is_open():
                    skipped_tiers.append({
                        "tier": "edge_tts",
                        "reason": "Circuit breaker OPEN (skipping Edge-TTS due to consecutive failures)",
                        "latency_ms": 0.0
                    })
                    continue

                try:
                    import edge_tts
                    voice, rate = self._select_voice(text)
                    communicate = edge_tts.Communicate(text, voice, rate=rate)
                    
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                        tmp_path = tmp.name

                    await asyncio.wait_for(
                        communicate.save(tmp_path),
                        timeout=self.timeout_sec
                    )

                    with open(tmp_path, "rb") as f:
                        audio_bytes = f.read()

                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

                    if audio_bytes:
                        self.circuit_breaker.record_success()
                        tier_used = "edge_tts"
                        content_type = "audio/mpeg"
                        break
                except Exception as e:
                    self.circuit_breaker.record_failure()
                    skipped_tiers.append({
                        "tier": "edge_tts",
                        "reason": str(e),
                        "latency_ms": round((time.time() - tier_start) * 1000, 2)
                    })

            # TIER 3: gTTS (Google Text-to-Speech)
            elif tier == "gtts":
                try:
                    import gtts
                    lang = self._detect_language(text)
                    tts_obj = gtts.gTTS(text=text, lang=lang)
                    fp = io.BytesIO()
                    tts_obj.write_to_fp(fp)
                    audio_bytes = fp.getvalue()
                    if audio_bytes:
                        tier_used = "gtts"
                        content_type = "audio/mpeg"
                        break
                except Exception as e:
                    skipped_tiers.append({
                        "tier": "gtts",
                        "reason": str(e),
                        "latency_ms": round((time.time() - tier_start) * 1000, 2)
                    })

            # TIER 4: Piper (ar_JO-kareem-low)
            elif tier == "piper":
                try:
                    audio_bytes = await self._synthesize_piper(text)
                    if audio_bytes:
                        tier_used = "piper"
                        content_type = "audio/wav"
                        break
                except Exception as e:
                    skipped_tiers.append({
                        "tier": "piper",
                        "reason": str(e),
                        "latency_ms": round((time.time() - tier_start) * 1000, 2)
                    })
                    audio_bytes = self._generate_fallback_arabic_audio(text)
                    tier_used = "spoken_fallback"
                    content_type = "audio/mpeg"
                    break

        total_latency_ms = round((time.time() - start_time) * 1000, 2)
        self._log_langfuse_trace(
            text=text,
            tier_used=tier_used,
            total_latency_ms=total_latency_ms,
            skipped_tiers=skipped_tiers
        )

        return audio_bytes, content_type

    async def _synthesize_piper(self, text: str) -> bytes:
        """Synthétise le texte de façon 100% offline avec Piper ar_JO-kareem-low."""
        if not os.path.exists(self.piper_model_path):
            raise FileNotFoundError(f"Modèle Piper ar_JO-kareem-low introuvable : {self.piper_model_path}")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        cmd = ["piper", "--model", self.piper_model_path, "--output_file", tmp_path]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate(input=text.encode("utf-8"))

        if os.path.exists(tmp_path):
            with open(tmp_path, "rb") as f:
                audio_bytes = f.read()
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return audio_bytes

        raise RuntimeError("Piper CLI n'a pas produit de fichier de sortie WAV.")

    def _generate_fallback_arabic_audio(self, text: str) -> bytes:
        """Génère un signal audio d'urgence avec la voix synthétisée gTTS."""
        try:
            import gtts
            lang = self._detect_language(text)
            tts_obj = gtts.gTTS(text=text, lang=lang)
            fp = io.BytesIO()
            tts_obj.write_to_fp(fp)
            return fp.getvalue()
        except Exception:
            fp = io.BytesIO()
            with wave.open(fp, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(24000)
                samples = struct.pack('<h', 0) * 12000
                wav_file.writeframes(samples)
            return fp.getvalue()

    def _log_langfuse_trace(
        self,
        text: str,
        tier_used: Optional[str],
        total_latency_ms: float,
        skipped_tiers: List[Dict[str, Any]]
    ):
        """Instrument la synthèse vocale avec traçabilité Langfuse."""
        event_payload = {
            "text": text[:50] + "..." if len(text) > 50 else text,
            "tier_used": tier_used,
            "total_latency_ms": total_latency_ms,
            "skipped_tiers": skipped_tiers
        }
        logger.info(f"[Langfuse Trace] TTS Synthesis Event: {event_payload}")
        try:
            from app.shared.config import settings
            if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
                from langfuse import Langfuse
                langfuse = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST
                )
                langfuse.trace(
                    name="tts_synthesis_chain",
                    metadata=event_payload
                )
        except Exception as e:
            logger.debug(f"Clarté Langfuse non disponible ({e})")

    async def synthesize_stream(self, text: str, chunk_size: int = 4096) -> AsyncGenerator[bytes, None]:
        """Génère les octets audio sous forme de flux (streaming)."""
        if not text:
            return

        audio_bytes, _ = await self.synthesize(text)
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i:i + chunk_size]


# Singleton global
tts_service = TTSService()
