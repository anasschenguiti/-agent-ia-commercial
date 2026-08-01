"""
Pipeline RAG (Retrieval-Augmented Generation) avec Qdrant.

Week 2 (bug fix) : on ne retourne PLUS la chaine '[Contexte RAG - Mode simule ...]'
qui etait injectee dans le prompt LLM et empoisonnait les reponses.

La methode retrieve() renvoie maintenant un dict explicite :
  {"context": "...", "status": "ok" | "unavailable" | "error"}
Le caller (agent.py) injecte le contexte UNIQUEMENT si status == "ok".
"""

import uuid
from typing import Dict, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_openai import OpenAIEmbeddings

from app.shared.config import settings


class RAGPipeline:
    """
    Gere la recherche vectorielle dans Qdrant pour fournir du contexte au LLM.

    Collections Qdrant suggerees :
    - "product_knowledge" : fiches produits, FAQs
    - "sales_playbooks"  : techniques de vente, objections traitees
    - "case_studies"     : etudes de cas clients
    """

    COLLECTION_NAME = "sales_knowledge"

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.embedder: Optional[OpenAIEmbeddings] = None
        self.enabled: bool = False
        self._init_error: Optional[str] = None

        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
            )
            # OpenAI obligatoire pour les embeddings (1536 dims).
            if settings.OPENAI_API_KEY:
                self.embedder = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    openai_api_key=settings.OPENAI_API_KEY,
                )
            if self.client and self.embedder:
                if not self.client.collection_exists(self.COLLECTION_NAME):
                    self.client.create_collection(
                        collection_name=self.COLLECTION_NAME,
                        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                    )
                self.enabled = True
        except Exception as e:
            self._init_error = str(e)
            self.client = None
            self.embedder = None
            self.enabled = False

    async def retrieve(self, query: str, top_k: int = 5, min_score: float = 0.35) -> Dict[str, str]:
        """
        Recherche les passages les plus pertinents pour la requete.

        Returns:
            dict avec {"context": str, "status": "ok"|"unavailable"|"error"}
            - status="unavailable" : Qdrant OU OpenAI non configures => PAS d'injection
            - status="error"      : erreur reseau / search => PAS d'injection
            - status="ok"         : au moins un resultat au-dessus du seuil de score => INJECTION
        """
        if not self.enabled or not self.client or not self.embedder:
            return {"context": "", "status": "unavailable"}

        try:
            query_vector = await self.embedder.aembed_query(query)
            results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=min_score,
            )
            chunks = []
            for r in results:
                if r.payload and r.score >= min_score:
                    c = r.payload.get("content", "").strip()
                    if c and not c.startswith("[Contexte RAG - Mode simule"):
                        chunks.append(c)

            context = "\n\n".join(chunks).strip()
            if not context:
                return {"context": "", "status": "unavailable"}
            return {"context": context, "status": "ok"}
        except Exception as e:
            return {"context": "", "status": "error", "error": str(e)}

    async def index_document(self, content: str, metadata: dict) -> bool:
        """Indexe un nouveau document dans Qdrant. Returns True si OK."""
        if not self.enabled or not self.client or not self.embedder:
            return False
        try:
            vector = await self.embedder.aembed_query(content)
            point_id = str(uuid.uuid4())
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    {
                        "id": point_id,
                        "vector": vector,
                        "payload": {"content": content, **metadata},
                    }
                ],
            )
            return True
        except Exception:
            return False

    async def delete_document(self, document_id: str) -> bool:
        """Supprime un document de l'index."""
        if not self.client:
            return False
        try:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[document_id],
            )
            return True
        except Exception:
            return False
