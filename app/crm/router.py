"""
Endpoints API pour le module CRM.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.crm.service import CRMService

router = APIRouter()


@router.post("/sync/{crm_type}/{prospect_id}")
async def sync_prospect(
    crm_type: str,
    prospect_id: str,
    service: CRMService = Depends(),
):
    """Synchronise un prospect vers le CRM cible (hubspot ou odoo)."""
    if crm_type not in ("hubspot", "odoo"):
        raise HTTPException(status_code=400, detail="CRM non supporté")
    result = await service.sync_prospect(crm_type, prospect_id)
    return result


@router.get("/contacts")
async def list_crm_contacts(
    crm_type: str = "hubspot",
    service: CRMService = Depends(),
):
    """Récupère les contacts depuis le CRM."""
    return await service.list_contacts(crm_type)


@router.put("/contacts/{contact_id}/stage")
async def update_deal_stage(
    contact_id: str,
    stage: str,
    crm_type: str = "hubspot",
    service: CRMService = Depends(),
):
    """Met à jour l'étape pipeline d'un contact."""
    return await service.update_stage(crm_type, contact_id, stage)


@router.post("/activities")
async def log_activity(
    payload: dict,
    crm_type: str = "hubspot",
    service: CRMService = Depends(),
):
    """Enregistre une activité commerciale dans le CRM."""
    return await service.log_activity(crm_type, payload)
