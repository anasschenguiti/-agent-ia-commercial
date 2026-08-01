"""
Endpoints FastAPI pour la gestion des interactions vocales (Voice AI Agent).
Supporte l'endpoint HTTP REST /interact et le WebSocket temps réel /ws.
"""
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect

from app.voice.agent_voice import VoiceAgent
from app.shared.config import settings

logger = logging.getLogger("sales_ai.voice.router")

router = APIRouter(prefix="/voice", tags=["Voice Agent AI"])


@router.get("/config")
async def get_voice_config():
    """Retourne la configuration active des services vocaux et LLM."""
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "ollama_model": settings.OLLAMA_MODEL,
        "stt_engine": settings.STT_ENGINE,
        "stt_model_size": settings.STT_MODEL_SIZE,
        "tts_engine": settings.TTS_ENGINE,
        "tts_voice_darija": settings.TTS_VOICE_DARIJA,
        "tts_voice_french": settings.TTS_VOICE_FRENCH,
    }


@router.post("/interact")
async def voice_interaction(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    Endpoint principal d'interaction vocale HTTP :
    Prend un fichier audio (webm, wav, mp3), exécute STT -> LangGraph Qwen Agent -> TTS,
    et retourne la transcription, la réponse texte et le fichier audio généré en base64.
    """
    if not session_id:
        session_id = f"voice_session_{uuid.uuid4().hex[:8]}"

    try:
        audio_content = await file.read()
        if not audio_content:
            raise HTTPException(status_code=400, detail="Fichier audio vide")

        voice_agent = VoiceAgent(session_id=session_id)
        result = await voice_agent.process_voice_interaction(
            audio_bytes=audio_content,
            filename=file.filename or "input.webm"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement vocal : {str(e)}")


@router.websocket("/ws")
@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket, session_id: Optional[str] = None):
    """
    Endpoint WebSocket bidirectionnel pour la voix en direct.
    Reçoit des paquets audio binaires ou des messages JSON,
    exécute l'agent vocal et renvoie la réponse audio/texte en streaming.
    """
    await websocket.accept()
    if not session_id:
        session_id = f"ws_voice_{uuid.uuid4().hex[:8]}"

    voice_agent = VoiceAgent(session_id=session_id)
    logger.info(f"Connexion WebSocket vocale établie : session {session_id}")

    try:
        while True:
            # Attend de l'audio binaire ou un message JSON
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                result = await voice_agent.process_voice_interaction(
                    audio_bytes=audio_bytes, filename="stream.webm"
                )
                await websocket.send_json(result)

            elif "text" in message and message["text"]:
                import json
                try:
                    payload = json.loads(message["text"])
                    if payload.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif "audio_base64" in payload:
                        import base64
                        raw_bytes = base64.b64decode(payload["audio_base64"])
                        result = await voice_agent.process_voice_interaction(
                            audio_bytes=raw_bytes, filename="input.webm"
                        )
                        await websocket.send_json(result)
                except Exception as parse_err:
                    await websocket.send_json({"error": f"Payload non valide: {parse_err}"})

    except WebSocketDisconnect:
        logger.info(f"Déconnexion WebSocket vocale : session {session_id}")
    except Exception as e:
        logger.error(f"Erreur WebSocket vocale ({session_id}) : {e}")
        try:
            await websocket.close()
        except Exception:
            pass
