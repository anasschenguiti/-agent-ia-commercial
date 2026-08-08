"""
Endpoints chat et WebSocket pour le module de conversation.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import List

from app.conversation.agent import ConversationAgent
from app.conversation.memory import ConversationMemory

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
):
    """WebSocket pour le chat en temps réel avec l'agent."""
    await websocket.accept()
    agent = ConversationAgent(session_id=session_id)
    try:
        while True:
            data = await websocket.receive_text()
            response = await agent.process(data)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        await agent.save_state()


@router.post("/chat/{session_id}")
async def chat(
    session_id: str,
    payload: dict,
):
    """Endpoint REST pour envoyer un message à l'agent."""
    agent = ConversationAgent(session_id=session_id)
    user_message = payload.get("message", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message vide")
    response = await agent.process(user_message)
    await agent.save_state()
    return {"session_id": session_id, "response": response}


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Récupère l'historique d'une conversation."""
    memory = ConversationMemory(session_id=session_id)
    messages = await memory.get_history()
    return {"session_id": session_id, "messages": messages}


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Efface l'historique d'une session."""
    memory = ConversationMemory(session_id=session_id)
    await memory.clear()
    return {"message": "Historique effacé"}
