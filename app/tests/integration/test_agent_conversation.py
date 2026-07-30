"""
Tests d'intégration pour le flux conversationnel de l'agent.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.conversation.agent import ConversationAgent


@pytest.fixture
def mock_agent():
    with patch("app.conversation.agent.ChatOpenAI") as mock_openai_cls, \
         patch("app.conversation.agent.RAGPipeline") as mock_rag_cls, \
         patch("app.conversation.agent.ConversationMemory") as mock_memory_cls:
        
        # Configuration des mocks
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock()
        mock_openai_cls.return_value = mock_llm
        
        mock_rag = MagicMock()
        mock_rag.retrieve = AsyncMock(return_value="Contexte de test")
        mock_rag_cls.return_value = mock_rag
        
        mock_memory = MagicMock()
        mock_memory.get_history = AsyncMock(return_value=[])
        mock_memory.save = AsyncMock()
        mock_memory.clear = AsyncMock()
        mock_memory.load = AsyncMock()
        mock_memory_cls.return_value = mock_memory
        
        agent = ConversationAgent(session_id="test-session")
        yield agent, mock_llm, mock_rag, mock_memory


@pytest.mark.asyncio
async def test_agent_objection_handling(mock_agent):
    agent, mock_llm, mock_rag, mock_memory = mock_agent
    
    # Tester une objection de prix
    response = await agent.process("C'est trop cher pour notre budget")
    
    assert "Je comprends que le budget est une préoccupation" in response
    mock_rag.retrieve.assert_called_once_with("C'est trop cher pour notre budget")
    mock_memory.add_message.assert_any_call("user", "C'est trop cher pour notre budget")
    mock_memory.save.assert_called_once()


@pytest.mark.asyncio
async def test_agent_llm_response(mock_agent):
    agent, mock_llm, mock_rag, mock_memory = mock_agent
    
    # Mock du retour du LLM
    mock_response = MagicMock()
    mock_response.content = "Bonjour ! Nous pouvons vous aider avec nos offres."
    mock_llm.ainvoke.return_value = mock_response
    
    # Simuler une clé d'API valide
    with patch("app.conversation.agent.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-valid-key-for-test"
        mock_settings.OPENAI_MODEL = "gpt-4o"
        
        response = await agent.process("Bonjour, que proposez-vous ?")
        
        assert response == "Bonjour ! Nous pouvons vous aider avec nos offres."
        mock_llm.ainvoke.assert_called_once()
        mock_memory.add_message.assert_any_call("user", "Bonjour, que proposez-vous ?")
        mock_memory.add_message.assert_any_call("assistant", "Bonjour ! Nous pouvons vous aider avec nos offres.")


@pytest.mark.asyncio
async def test_chat_endpoint():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    with patch("app.conversation.router.ConversationAgent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.process = AsyncMock(return_value="Bonjour ! C'est l'agent commercial.")
        mock_agent.save_state = AsyncMock()
        mock_agent_cls.return_value = mock_agent
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/conversation/chat/test-session-123",
                json={"message": "Bonjour"}
            )
            
        assert response.status_code == 200
        assert response.json()["response"] == "Bonjour ! C'est l'agent commercial."
        mock_agent.process.assert_called_once_with("Bonjour")
        mock_agent.save_state.assert_called_once()
