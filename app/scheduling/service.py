"""
Logique métier du module de planification.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.scheduling.calendar_client import CalendarClient


class SchedulingService:
    def __init__(self):
        self.calendar = CalendarClient()

    async def get_available_slots(
        self, date_from: datetime, date_to: datetime
    ) -> List[Dict[str, Any]]:
        """Récupère les créneaux libres dans la plage donnée."""
        return await self.calendar.get_free_slots(date_from, date_to)

    async def create_appointment(self, payload: dict) -> Dict[str, Any]:
        """Crée un rendez-vous dans le calendrier."""
        return await self.calendar.create_event(payload)

    async def get_appointment(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un événement par son ID."""
        return await self.calendar.get_event(appointment_id)

    async def cancel_appointment(self, appointment_id: str) -> None:
        """Annule et supprime un événement du calendrier."""
        await self.calendar.delete_event(appointment_id)
