"""
Orchestrateur principal de l'Agent Vocal (Voice AI Agent).
Transforme un extrait sonore en texte (STT), le soumet à l'agent conversationnel LangGraph Qwen,
puis convertit la réponse en audio (TTS) avec la bonne voix pour la langue détectée.
"""
import base64
import time
import logging
from typing import Dict, Any

from app.conversation.agent import ConversationAgent
from app.voice.stt import STTService
from app.voice.tts import TTSService

logger = logging.getLogger("sales_ai.voice.agent")

# Mapping Whisper language codes → internal language names used by ConversationAgent
WHISPER_LANG_MAP = {
    "ar": "Darija marocaine",   # Arabic → force Arabic/Darija mode
    "en": "Anglais",
    "fr": "Français",
    "es": "Français",           # fallback Spanish → French
}


class VoiceAgent:
    """Agent vocal complet intégrant STT, Agent LLM (Qwen Ollama) et TTS."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.agent = ConversationAgent(session_id=session_id)
        self.stt = STTService()
        self.tts = TTSService()

    async def process_voice_interaction(
        self, audio_bytes: bytes, filename: str = "input.webm"
    ) -> Dict[str, Any]:
        """
        Traite un flux vocal de A à Z :
        1. STT: Transcrit l'audio utilisateur en texte Darija/FR/AR.
        2. LLM: Soumet la transcription à l'agent LangGraph Qwen.
        3. TTS: Génère la réponse sonore.
        """
        start_time = time.time()

        # Step 1 : Transcription STT + Détection de la langue
        stt_start = time.time()
        stt_result = await self.stt.transcribe(audio_bytes, filename=filename)
        stt_duration = round(time.time() - stt_start, 3)

        if isinstance(stt_result, dict):
            user_text = stt_result.get("text", "")
            detected_lang = stt_result.get("detected_language", "UNKNOWN")   # e.g. "AR", "EN", "FR"
            lang_prob = stt_result.get("language_probability", 0.0)
        else:
            user_text = str(stt_result)
            detected_lang = "UNKNOWN"
            lang_prob = 0.0

        # Map Whisper language code → internal language string for the LLM agent
        lang_code_lower = detected_lang.lower()
        forced_language = WHISPER_LANG_MAP.get(lang_code_lower, None)   # None = let agent auto-detect
        logger.info(f"STT detected language: {detected_lang} (prob={lang_prob:.2f}) → forcing agent lang: {forced_language}")

        # Step 2 : Traitement Agent Conversationnel
        # Inject a language-override prefix so the LLM replies in the detected language
        if not user_text:
            user_text = "(Audio non capturé ou silencieux)"
            if lang_code_lower == "ar":
                agent_response = "عذراً، لم أتمكن من سماع صوتك. هل يمكنك التحدث بصوت أعلى والمحاولة مرة أخرى؟"
            elif lang_code_lower == "en":
                agent_response = "Sorry, I couldn't hear your voice. Could you speak a little louder and try again?"
            else:
                agent_response = "Désolé, je n'ai pas pu entendre votre voix. Pouvez-vous parler un peu plus fort et réessayer ?"
            llm_duration = 0.0
        else:
            # Prepend an invisible language directive so the LLM uses the right language
            if forced_language and forced_language != self.agent.detect_language(user_text):
                augmented_text = f"[LANGUE DÉTECTÉE: {forced_language}] {user_text}"
            else:
                augmented_text = user_text

            llm_start = time.time()
            agent_response = await self.agent.process_with_language(augmented_text, forced_language=forced_language)
            llm_duration = round(time.time() - llm_start, 3)

        # Step 3 : Synthèse Vocale TTS avec la voix correspondant à la langue détectée
        tts_start = time.time()
        # Pass language_hint from STT so TTS picks the right voice (Arabic / English / French)
        tts_lang_hint = lang_code_lower if lang_code_lower in ("ar", "en", "fr") else "ar"
        audio_out_bytes, content_type = await self.tts.synthesize(agent_response, language_hint=tts_lang_hint)
        tts_duration = round(time.time() - tts_start, 3)

        audio_b64 = base64.b64encode(audio_out_bytes).decode("utf-8") if audio_out_bytes else ""
        total_duration = round(time.time() - start_time, 3)

        logger.info(
            f"Voice Session {self.session_id} [{detected_lang}] - Total: {total_duration}s (STT: {stt_duration}s, LLM: {llm_duration}s, TTS: {tts_duration}s)"
        )

        return {
            "session_id": self.session_id,
            "user_transcript": user_text,
            "agent_response": agent_response,
            "detected_language": detected_lang,
            "language_probability": lang_prob,
            "audio_base64": audio_b64,
            "content_type": content_type,
            "metrics": {
                "stt_duration_sec": stt_duration,
                "llm_duration_sec": llm_duration,
                "tts_duration_sec": tts_duration,
                "total_duration_sec": total_duration,
            },
        }
