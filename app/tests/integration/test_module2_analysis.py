"""
Test d'intégration — Module 2 : API d'Analyse IA (POST /api/analysis/{prospect_id}).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.shared.database import init_db


@pytest.mark.asyncio
async def test_module2_analysis_endpoint():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Créer un prospect
        search_res = await ac.post("/api/prospection/search", json={"query": {"keywords": ["agence"], "max_results": 1}})
        assert search_res.status_code == 200
        data = search_res.json()
        assert len(data["prospects"]) > 0
        prospect_id = data["prospects"][0]["id"]

        # 2. Exécuter l'analyse IA
        analysis_res = await ac.post(f"/api/analysis/{prospect_id}")
        assert analysis_res.status_code == 200
        analysis_data = analysis_res.json()
        assert "diagnostic" in analysis_data
        assert "signals" in analysis_data
        assert len(analysis_data["diagnostic"]) > 10
