"""
Logique métier du module CRM.
Façade qui délègue vers les adaptateurs HubSpot ou Odoo.
"""


from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Depends

from app.shared.database import get_db
from app.prospection.models_sql import ProspectSQL
from app.crm.hubspot_adapter import HubSpotAdapter
from app.crm.odoo_adapter import OdooAdapter


class CRMService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db
        self.adapters = {
            "hubspot": HubSpotAdapter(),
            "odoo": OdooAdapter(),
        }

    def _get_adapter(self, crm_type: str):
        adapter = self.adapters.get(crm_type)
        if not adapter:
            raise ValueError(f"Adaptateur CRM inconnu : {crm_type}")
        return adapter

    async def sync_prospect(self, crm_type: str, prospect_id: str) -> Dict[str, Any]:
        """Synchronise un prospect vers le CRM."""
        stmt = select(ProspectSQL).where(ProspectSQL.id == prospect_id)
        result = await self.db.execute(stmt)
        prospect = result.scalar_one_or_none()
        if not prospect:
            return {"status": "error", "detail": "Prospect non trouvé"}

        contact_payload = {
            "firstname": prospect.first_name,
            "lastname": prospect.last_name,
            "email": prospect.email,
            "phone": prospect.phone,
            "company": prospect.company,
            "website": prospect.website,
            "jobtitle": prospect.job_title,
        }

        adapter = self._get_adapter(crm_type)
        return await adapter.upsert_contact(contact_payload)

    async def list_contacts(self, crm_type: str) -> List[Dict[str, Any]]:
        """Récupère la liste des contacts depuis le CRM."""
        adapter = self._get_adapter(crm_type)
        return await adapter.list_contacts()

    async def update_stage(self, crm_type: str, contact_id: str, stage: str) -> Dict[str, Any]:
        """Met à jour l'étape pipeline d'un contact."""
        adapter = self._get_adapter(crm_type)
        return await adapter.update_deal_stage(contact_id, stage)

    async def log_activity(self, crm_type: str, payload: dict) -> Dict[str, Any]:
        """Enregistre une activité commerciale."""
        adapter = self._get_adapter(crm_type)
        return await adapter.create_activity(payload)
