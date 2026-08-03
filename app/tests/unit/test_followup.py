"""
Tests unitaires pour le module de relances automatiques avec session de base de données simulée (Mock).
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.prospection.models_sql import ProspectSQL, ProspectStatus
from app.conversation.models_sql import MessageSQL
from app.prospection.followup_service import FollowUpService


@pytest.mark.asyncio
async def test_followup_states_with_time_shifting():
    # Mock de la session de base de données
    mock_db = AsyncMock(spec=AsyncSession)

    prospect = ProspectSQL(
        id="test_prospect_followup",
        first_name="Alice",
        last_name="Martin",
        email="alice@followup.com",
        status=ProspectStatus.NEW,
        score=75.0
    )

    # 1. Mock de get_pending_followups (aucun message)
    mock_prospects_res = MagicMock()
    mock_prospects_res.scalars.return_value.all.return_value = [prospect]
    
    mock_messages_res_1 = MagicMock()
    mock_messages_res_1.scalars.return_value.all.return_value = []
    
    mock_db.execute.side_effect = [mock_prospects_res, mock_messages_res_1]

    service = FollowUpService(db=mock_db)

    # Aucun message échangé -> État J0_PENDING
    followups = await service.get_pending_followups(simulate_days=0)
    assert len(followups) == 1
    assert followups[0]["state"] == "J0_PENDING"
    assert followups[0]["action"] == "Envoyer premier message (J0)"

    # 2. Mock de get_pending_followups (1 message envoyé à l'instant par l'assistant)
    latest_msg = MessageSQL(
        id=1,
        session_id=prospect.id,
        prospect_id=prospect.id,
        role="assistant",
        content="Hello!",
        timestamp=datetime.now(timezone.utc)
    )
    
    mock_prospects_res_2 = MagicMock()
    mock_prospects_res_2.scalars.return_value.all.return_value = [prospect]
    
    mock_messages_res_2 = MagicMock()
    mock_messages_res_2.scalars.return_value.all.return_value = [latest_msg]
    
    mock_db.execute.side_effect = [mock_prospects_res_2, mock_messages_res_2]
    
    # 0 jour simulé -> Doit être en attente de J3 (J3_WAITING)
    followups_waiting = await service.get_pending_followups(simulate_days=0)
    assert followups_waiting[0]["state"] == "J3_WAITING"

    # 3. Même message, mais on simule +4 jours
    mock_prospects_res_3 = MagicMock()
    mock_prospects_res_3.scalars.return_value.all.return_value = [prospect]
    
    mock_messages_res_3 = MagicMock()
    mock_messages_res_3.scalars.return_value.all.return_value = [latest_msg]
    
    mock_db.execute.side_effect = [mock_prospects_res_3, mock_messages_res_3]
    
    # 4 jours simulés -> Doit passer à J3_PENDING (urgent)
    followups_pending = await service.get_pending_followups(simulate_days=4)
    assert followups_pending[0]["state"] == "J3_PENDING"
    assert followups_pending[0]["action"] == "Envoyer relance J3"
