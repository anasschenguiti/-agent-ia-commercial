"""
Pipeline RAG (Retrieval-Augmented Generation) avec Qdrant.
"""

from typing import List, Optional
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_openai import OpenAIEmbeddings

from app.shared.config import settings


class RAGPipeline:
    """
    Gère la recherche vectorielle dans Qdrant pour fournir du contexte au LLM.
    
    Collections Qdrant suggérées :
    - "product_knowledge" : fiches produits, FAQs
    - "sales_playbooks"  : techniques de vente, objections traitées
    - "case_studies"     : études de cas clients
    """

    COLLECTION_NAME = "sales_knowledge"

    def __init__(self):
        try:
            self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
            self.embedder = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY,
            )
            # Création de la collection si elle n'existe pas
            if not self.client.collection_exists(self.COLLECTION_NAME):
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
        except Exception as e:
            print(f"[RAGPipeline] Erreur d'initialisation Qdrant (RAG désactivé/simulé) : {e}")
            self.client = None
            self.embedder = None

    async def retrieve(self, query: str, top_k: int = 5) -> str:
        """
        Recherche les passages les plus pertinents pour la requête.
        Retourne un contexte textuel concaténé.
        """
        if not self.client or not self.embedder:
            return "[Contexte RAG - Mode simulé car Qdrant ou OpenAI non configuré]"

        try:
            query_vector = await self.embedder.aembed_query(query)
            results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_vector,
                limit=top_k,
            )
            return "\n\n".join([r.payload.get("content", "") for r in results if r.payload])
        except Exception as e:
            print(f"[RAGPipeline] Erreur lors de la récupération : {e}")
            return "[Contexte RAG - Erreur lors de la recherche vectorielle]"

    async def index_document(self, content: str, metadata: dict) -> None:
        """Indexe un nouveau document dans Qdrant."""
        if not self.client or not self.embedder:
            print("[RAGPipeline] Indexation impossible : client non configuré.")
            return

        try:
            vector = await self.embedder.aembed_query(content)
            point_id = str(uuid.uuid4())
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    {
                        "id": point_id,
                        "vector": vector,
                        "payload": {"content": content, **metadata}
                    }
                ]
            )
        except Exception as e:
            print(f"[RAGPipeline] Erreur d'indexation : {e}")

    async def delete_document(self, document_id: str) -> None:
        """Supprime un document de l'index."""
        if not self.client:
            return

        try:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[document_id]
            )
        except Exception as e:
            print(f"[RAGPipeline] Erreur de suppression : {e}")
