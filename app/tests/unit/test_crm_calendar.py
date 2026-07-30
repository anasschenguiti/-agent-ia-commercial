"""
Tests unitaires pour les connecteurs CRM et Calendriers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from app.crm.hubspot_adapter import HubSpotAdapter
from app.crm.odoo_adapter import OdooAdapter
from app.scheduling.calendar_client import CalendarClient


# ── Tests HubSpot ──
@pytest.fixture
def mock_hubspot():
    with patch("app.crm.hubspot_adapter.settings") as mock_settings:
        mock_settings.HUBSPOT_API_KEY = "sk-hubspot-test-key"
        adapter = HubSpotAdapter()
        yield adapter


@pytest.mark.asyncio
async def test_hubspot_upsert_new_contact(mock_hubspot):
    contact_data = {"email": "test@iksatech.com", "firstname": "John"}
    
    # Mock de la réponse HTTPX pour la recherche (aucun contact trouvé) et la création
    with patch("httpx.AsyncClient.post") as mock_post:
        # Mock de recherche (retourne vide)
        mock_search_res = MagicMock()
        mock_search_res.status_code = 200
        mock_search_res.json.return_value = {"results": []}
        
        # Mock de création
        mock_create_res = MagicMock()
        mock_create_res.status_code = 201
        mock_create_res.json.return_value = {"id": "12345", "properties": contact_data}
        
        mock_post.side_effect = [mock_search_res, mock_create_res]
        
        res = await mock_hubspot.upsert_contact(contact_data)
        
        assert res["status"] == "success"
        assert res["data"]["id"] == "12345"
        assert mock_post.call_count == 2


# ── Tests Odoo ──
@pytest.fixture
def mock_odoo():
    with patch("app.crm.odoo_adapter.settings") as mock_settings:
        mock_settings.ODOO_URL = "https://test-instance.odoo.com"
        mock_settings.ODOO_DB = "test_db"
        mock_settings.ODOO_USER = "admin"
        mock_settings.ODOO_PASSWORD = "test-password"
        adapter = OdooAdapter()
        yield adapter


@pytest.mark.asyncio
async def test_odoo_authenticate(mock_odoo):
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"result": {"uid": 42}}
        mock_post.return_value = mock_res
        
        uid = await mock_odoo._authenticate()
        
        assert uid == 42
        assert mock_odoo.uid == 42
        mock_post.assert_called_once()


# ── Tests Calendriers ──
@pytest.mark.asyncio
async def test_calendar_mock_slots():
    # En l'absence de clé de configuration, le calendrier doit générer des créneaux de simulation
    client = CalendarClient(provider="google")
    
    date_from = datetime(2026, 7, 20, 0, 0, 0) # Un lundi
    date_to = datetime(2026, 7, 21, 23, 59, 59) # Un mardi
    
    slots = await client.get_free_slots(date_from, date_to)
    
    assert len(slots) > 0
    # On doit retrouver 4 créneaux par jour (9h, 10h, 14h, 15h)
    assert any("09:00:00" in s["start"] for s in slots)
    assert any("15:00:00" in s["start"] for s in slots)
