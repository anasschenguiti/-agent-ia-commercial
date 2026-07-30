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
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_launch_scraping():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/prospection/search",
            json={"keywords": ["startup", "SaaS"], "location": "Paris"},
        )
    assert response.status_code == 200
    assert "message" in response.json()
