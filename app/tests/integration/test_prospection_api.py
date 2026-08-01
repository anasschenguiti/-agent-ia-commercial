"""
Tests d'intégration pour les endpoints de prospection.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    # Week 1 : /health renvoie un JSON avec status et services.
    # En environnement de test sans Postgres/Redis, status peut etre 'ok'
    # (services 'unknown') ou 'degraded' (services 'offline'). Les deux
    # sont acceptables tant que le endpoint repond en 200.
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "services" in data


@pytest.mark.asyncio
async def test_launch_scraping():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/prospection/search",
            json={"keywords": ["startup", "SaaS"], "location": "Paris"},
        )
    assert response.status_code == 200
    assert "message" in response.json()
