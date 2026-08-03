"""
Tests unitaires pour le moteur de templates et les endpoints d'analytics/export CSV.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.communication.templates import TemplateEngine, MessageTemplate
from app.prospection.models import ProspectRead, ProspectStatus
from datetime import datetime, timezone


def test_template_engine_list_and_render():
    engine = TemplateEngine()
    
    # 1. Lister tous les templates
    templates = engine.list_templates()
    assert len(templates) >= 4

    # 2. Rendre un template avec variables
    context = {
        "first_name": "Karim",
        "company": "Atlas Tech",
        "job_title": "Directeur Général",
        "score": 92
    }
    rendered = engine.render("email_intro", context)
    
    assert rendered["channel"] == "email"
    assert "Atlas Tech" in rendered["subject"]
    assert "Karim" in rendered["content"]
    assert "Directeur Général" in rendered["content"]


def test_template_engine_custom_save_and_delete():
    engine = TemplateEngine()
    
    new_tpl = MessageTemplate(
        id="test_custom",
        channel="whatsapp",
        name="Test Template",
        subject=None,
        content="Salut {first_name} de {company} !"
    )
    engine.save_template(new_tpl)
    
    assert engine.get_template("test_custom") is not None
    
    deleted = engine.delete_template("test_custom")
    assert deleted is True
    assert engine.get_template("test_custom") is None


@pytest.mark.asyncio
async def test_analytics_and_export_endpoints():
    from app.prospection.router import get_analytics, export_prospects_csv
    from app.prospection.service import ProspectionService

    mock_service = AsyncMock(spec=ProspectionService)
    
    now = datetime.now(timezone.utc)
    mock_prospects = [
        ProspectRead(
            id="p1", first_name="Amina", last_name="El Amrani", email="amina@test.com",
            company="Morocco IT", job_title="CTO", score=90.0, status=ProspectStatus.NEW,
            created_at=now, updated_at=now
        ),
        ProspectRead(
            id="p2", first_name="Youssef", last_name="Tazi", email="youssef@test.com",
            company="Casatech", job_title="CEO", score=60.0, status=ProspectStatus.CONTACTED,
            created_at=now, updated_at=now
        )
    ]
    mock_service.list_prospects.return_value = mock_prospects

    # Test Analytics
    analytics = await get_analytics(service=mock_service)
    assert analytics["total_prospects"] == 2
    assert analytics["hot_count"] == 1
    assert analytics["warm_count"] == 1
    assert analytics["avg_score"] == 75.0

    # Test Export CSV
    response = await export_prospects_csv(service=mock_service)
    assert response.status_code == 200
    assert response.media_type == "text/csv"
    assert b"Amina" in response.body
    assert b"Casatech" in response.body
