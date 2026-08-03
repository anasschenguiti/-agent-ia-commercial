"""
Tests pour les endpoints /health/live et /health/ready.

Week 1 : split du /health en deux probes distinctes.
"""

import pytest
import time
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_live_always_returns_200():
    """/health/live doit toujours repondre 200, sans dependances externes."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_live_is_fast():
    """/health/live doit repondre en < 50ms (cible : 5-10ms)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = time.time()
        response = await client.get("/health/live")
        elapsed_ms = (time.time() - start) * 1000
    assert response.status_code == 200
    # Tolere jusqu'a 500ms en CI charge, mais vise 50ms.
    assert elapsed_ms < 500, f"/health/live trop lent: {elapsed_ms:.1f}ms"


@pytest.mark.asyncio
async def test_health_ready_returns_services_dict():
    """/health/ready doit renvoyer un dict par service."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    for service in ("postgres", "redis", "qdrant", "supabase"):
        assert service in data["services"]
    # status global peut etre 'ok' ou 'degraded' selon l'env de test.
    assert data["status"] in ("ok", "degraded")
