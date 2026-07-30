"""
Mémoire conversationnelle : stockage et récupération de l'historique des échanges.
Utilise Redis pour la persistance des sessions actives.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

# Import lazy : Redis n'est utilisé que dans save() / load() pour éviter une ImportError au démarrage
# from app.shared.redis_client import get_redis_client


class ConversationMemory:
    """
    Gère la mémoire à court et long terme d'une session de conversation.
    
    - Court terme : Redis (TTL 24h par défaut)
    - Long terme   : Base de données relationnelle (PostgreSQL)
    """

    TTL_SECONDS = 86400  # 24 heures

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.redis_key = f"conv:{session_id}:messages"
        self._local_buffer: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str) -> None:
        """Ajoute un message au buffer local."""
        self._local_buffer.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def get_history(self) -> List[Dict[str, Any]]:
        """Récupère l'historique complet de la session depuis PostgreSQL."""
        await self.load()
        return self._local_buffer

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Retourne les n derniers messages du buffer local."""
        return self._local_buffer[-n:]

    async def clear(self) -> None:
        """Efface la mémoire de la session en base, dans Redis et en local."""
        self._local_buffer = []
        
        # Supprimer de Redis
        try:
            from app.shared.redis_client import get_redis_client
            client = await get_redis_client()
            await client.delete(self.redis_key)
        except Exception as e:
            print(f"[ConversationMemory] Erreur suppression Redis : {e}")

        # Supprimer de PostgreSQL
        from app.shared.database import AsyncSessionLocal
        from app.conversation.models_sql import MessageSQL
        from sqlalchemy import delete
        
        async with AsyncSessionLocal() as session:
            try:
                stmt = delete(MessageSQL).where(MessageSQL.session_id == self.session_id)
                await session.execute(stmt)
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"[ConversationMemory] Erreur lors de la suppression de l'historique : {e}")

    async def save(self) -> None:
        """Persiste le buffer local en base de données PostgreSQL et met à jour Redis."""
        if not self._local_buffer:
            return
            
        # 1. Enregistrer dans PostgreSQL
        from app.shared.database import AsyncSessionLocal
        from app.conversation.models_sql import MessageSQL
        
        async with AsyncSessionLocal() as session:
            try:
                for msg in self._local_buffer:
                    db_message = MessageSQL(
                        session_id=self.session_id,
                        prospect_id=self.session_id,
                        role=msg["role"],
                        content=msg["content"]
                    )
                    session.add(db_message)
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"[ConversationMemory] Erreur d'enregistrement de l'historique : {e}")
                
        # 2. Mettre à jour Redis avec l'historique complet
        try:
            from app.shared.redis_client import get_redis_client
            import json
            client = await get_redis_client()
            
            cached = await client.get(self.redis_key)
            existing_messages = []
            if cached:
                existing_messages = json.loads(cached)
            else:
                # Recharger depuis PostgreSQL si Redis est vide
                from sqlalchemy.future import select
                async with AsyncSessionLocal() as session:
                    stmt = select(MessageSQL).where(MessageSQL.session_id == self.session_id).order_by(MessageSQL.timestamp.asc())
                    result = await session.execute(stmt)
                    db_messages = result.scalars().all()
                    existing_messages = [
                        {
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.timestamp.isoformat(),
                        }
                        for msg in db_messages
                    ]
            
            # Concaténer le buffer local sans introduire de doublons
            for local_msg in self._local_buffer:
                if not any(e.get("content") == local_msg.get("content") and e.get("role") == local_msg.get("role") for e in existing_messages):
                    existing_messages.append(local_msg)
            
            await client.setex(
                self.redis_key,
                self.TTL_SECONDS,
                json.dumps(existing_messages)
            )
            self._local_buffer.clear()
        except Exception as e:
            print(f"[ConversationMemory] Erreur de synchronisation Redis : {e}")
            self._local_buffer.clear()

    async def load(self) -> None:
        """Charge l'historique complet depuis Redis (cache) ou PostgreSQL."""
        # 1. Tenter le chargement depuis Redis
        try:
            from app.shared.redis_client import get_redis_client
            import json
            client = await get_redis_client()
            cached = await client.get(self.redis_key)
            if cached:
                self._local_buffer = json.loads(cached)
                return
        except Exception as e:
            print(f"[ConversationMemory] Erreur lecture Redis : {e}")

        # 2. Repli sur PostgreSQL
        from app.shared.database import AsyncSessionLocal
        from app.conversation.models_sql import MessageSQL
        from sqlalchemy.future import select
        
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(MessageSQL).where(MessageSQL.session_id == self.session_id).order_by(MessageSQL.timestamp.asc())
                result = await session.execute(stmt)
                db_messages = result.scalars().all()
                
                self._local_buffer = []
                for msg in db_messages:
                    self._local_buffer.append({
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                    })
                
                # Ré-indexer dans Redis pour le cache
                try:
                    from app.shared.redis_client import get_redis_client
                    import json
                    client = await get_redis_client()
                    await client.setex(
                        self.redis_key,
                        self.TTL_SECONDS,
                        json.dumps(self._local_buffer)
                    )
                except Exception as ex:
                    print(f"[ConversationMemory] Erreur de mise en cache Redis : {ex}")
            except Exception as e:
                print(f"[ConversationMemory] Erreur lors du chargement de l'historique : {e}")

