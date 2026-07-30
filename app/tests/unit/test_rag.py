"""
Tests unitaires pour le module RAG.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.conversation.rag import RAGPipeline


@pytest.fixture
def mock_rag():
    with patch("app.conversation.rag.QdrantClient") as mock_qdrant_cls, \
         patch("app.conversation.rag.OpenAIEmbeddings") as mock_embeddings_cls:
        
        # Configuration des mocks
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = True
        mock_qdrant_cls.return_value = mock_client
        
        mock_embedder = MagicMock()
        mock_embedder.aembed_query = AsyncMock(return_value=[0.1] * 1536)
        mock_embeddings_cls.return_value = mock_embedder
        
        pipeline = RAGPipeline()
        yield pipeline, mock_client, mock_embedder


@pytest.mark.asyncio
async def test_rag_retrieve(mock_rag):
    pipeline, mock_client, mock_embedder = mock_rag
    
    # Mock des résultats de recherche Qdrant
    mock_search_result = MagicMock()
    mock_search_result.payload = {"content": "IKSATECH propose du développement de logiciels sur mesure."}
    mock_client.search.return_value = [mock_search_result]
    
    result = await pipeline.retrieve("Quels services proposez-vous ?")
    
    assert "IKSATECH propose du développement de logiciels" in result
    mock_embedder.aembed_query.assert_called_once_with("Quels services proposez-vous ?")
    mock_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_rag_index_document(mock_rag):
    pipeline, mock_client, mock_embedder = mock_rag
    
    await pipeline.index_document("Nouveau service de cybersécurité", {"category": "security"})
    
    mock_embedder.aembed_query.assert_called_once_with("Nouveau service de cybersécurité")
    mock_client.upsert.assert_called_once()
