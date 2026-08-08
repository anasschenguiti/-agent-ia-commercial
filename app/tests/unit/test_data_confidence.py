"""
Test unitaire — Guardrail A1 : Absences de données inventées et présence de data_confidence.
"""
import pytest
from app.prospection.live_scraper import MultiSourceLiveScraper
from app.prospection.models import ProspectBase


@pytest.mark.asyncio
async def test_no_fabricated_phone_or_revenue():
    scraper = MultiSourceLiveScraper()
    # Lead sans site web
    raw_lead = [{
        "first_name": "Test",
        "last_name": "User",
        "company": "Test Company",
        "website": "",
        "phone": "",
        "company_size": None,
    }]
    
    enriched = await scraper._enrich_leads_via_web(raw_lead, "Casablanca", "Maroc", "Tech")
    lead = enriched[0]

    # Vérification strictes des guardrails
    assert lead["phone"] is None
    assert lead["phone_source"] == "not_found"
    assert lead["annual_revenue"] is None
    assert lead["annual_revenue_source"] == "unavailable"
    assert "data_confidence" in lead
    assert lead["data_confidence"]["phone"] == "unavailable"


def test_prospect_model_data_confidence():
    p = ProspectBase(
        first_name="Mehdi",
        last_name="Tazi",
        company="Tech Corp",
        data_confidence={"phone": "unavailable", "email": "verified"},
        phone_source="not_found"
    )
    assert p.data_confidence["phone"] == "unavailable"
    assert p.phone_source == "not_found"
