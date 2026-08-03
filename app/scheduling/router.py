"""
Endpoints API pour la planification de rendez-vous.
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List

from app.scheduling.service import SchedulingService

router = APIRouter()


@router.get("/slots")
async def get_available_slots(
    date_from: datetime,
    date_to: datetime,
    service: SchedulingService = Depends(),
):
    """Retourne les créneaux disponibles dans une plage de dates."""
    return await service.get_available_slots(date_from, date_to)


@router.post("/appointments")
async def create_appointment(
    payload: dict,
    service: SchedulingService = Depends(),
):
    """Crée un rendez-vous et l'ajoute au calendrier."""
    return await service.create_appointment(payload)


@router.get("/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    service: SchedulingService = Depends(),
):
    """Récupère les détails d'un rendez-vous."""
    appt = await service.get_appointment(appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    return appt


@router.delete("/appointments/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    service: SchedulingService = Depends(),
):
    """Annule un rendez-vous."""
    await service.cancel_appointment(appointment_id)
    return {"message": "Rendez-vous annulé"}
