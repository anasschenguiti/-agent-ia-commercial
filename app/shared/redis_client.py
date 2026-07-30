"""
Client Redis partagé pour la mémoire conversationnelle, le cache et les sessions.
"""

from typing import Optional, Any
import redis.asyncio as aioredis
import json

from app.shared.config import settings

# Instance singleton
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """Retourne l'instance Redis partagée (lazy init)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


class RedisCache:
    """Wrapper Redis avec sérialisation JSON et TTL."""

    def __init__(self, prefix: str = "cache"):
        self.prefix = prefix

    async def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur depuis Redis."""
        client = await get_redis_client()
        value = await client.get(f"{self.prefix}:{key}")
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Stocke une valeur dans Redis avec TTL (en secondes)."""
        client = await get_redis_client()
        await client.setex(
            f"{self.prefix}:{key}",
            ttl,
            json.dumps(value, default=str),
        )

    async def delete(self, key: str) -> None:
        """Supprime une clé Redis."""
        client = await get_redis_client()
        await client.delete(f"{self.prefix}:{key}")

    async def exists(self, key: str) -> bool:
        """Vérifie si une clé existe."""
        client = await get_redis_client()
        return bool(await client.exists(f"{self.prefix}:{key}"))
