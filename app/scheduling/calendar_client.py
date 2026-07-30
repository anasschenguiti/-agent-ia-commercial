"""
Client calendrier : Google Calendar / Outlook via Microsoft Graph.
"""

import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.shared.config import settings


import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.shared.config import settings


class CalendarClient:
    """
    Connecteur calendrier.
    Supporte Google Calendar (OAuth2) et Outlook (Microsoft Graph).
    """

    def __init__(self, provider: str = "google"):
        self.provider = provider
        # Token d'accès (à récupérer dynamiquement via flow OAuth2 en prod)
        self.access_token = settings.SECRET_KEY # Placeholder pour auth header
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def _is_configured(self) -> bool:
        # Permet de basculer en mode simulé si pas de token réel
        return bool(
            self.access_token 
            and not self.access_token.startswith("change-me") 
            and not self.access_token.startswith("dev-secret")
            and len(self.access_token) > 40
        )

    async def get_free_slots(
        self, date_from: datetime, date_to: datetime
    ) -> List[Dict[str, Any]]:
        """Retourne les créneaux libres dans la plage."""
        if not self._is_configured():
            return self._generate_mock_slots(date_from, date_to)

        if self.provider == "google":
            return await self._google_free_busy(date_from, date_to)
        elif self.provider == "outlook":
            return await self._outlook_free_busy(date_from, date_to)
        return []

    async def create_event(self, payload: dict) -> Dict[str, Any]:
        """Crée un événement dans le calendrier."""
        if not self._is_configured():
            return {"status": "simulated", "event_id": "event_mock_999", "event": payload}

        if self.provider == "google":
            return await self._google_create_event(payload)
        elif self.provider == "outlook":
            return await self._outlook_create_event(payload)
        return {"status": "unsupported_provider"}

    async def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un événement par son ID."""
        if not self._is_configured():
            return {"id": event_id, "summary": "Réunion Commerciale IA", "status": "confirmed"}

        endpoint = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
        if self.provider == "outlook":
            endpoint = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"

        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(endpoint, headers=self.headers, timeout=5.0)
                if res.status_code == 200:
                    return res.json()
            except Exception as e:
                print(f"[CalendarClient] Erreur get_event : {e}")
        return None

    async def delete_event(self, event_id: str) -> None:
        """Supprime un événement."""
        if not self._is_configured():
            print(f"[CalendarClient] Suppression simulée de l'événement {event_id}")
            return

        endpoint = f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
        if self.provider == "outlook":
            endpoint = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"

        async with httpx.AsyncClient() as client:
            try:
                await client.delete(endpoint, headers=self.headers, timeout=5.0)
            except Exception as e:
                print(f"[CalendarClient] Erreur delete_event : {e}")

    # ── Google Calendar ──────────────────────────────────────────────
    async def _google_free_busy(
        self, date_from: datetime, date_to: datetime
    ) -> List[Dict[str, Any]]:
        """Appel FreeBusy API Google Calendar."""
        endpoint = "https://www.googleapis.com/calendar/v3/freeBusy"
        payload = {
            "timeMin": date_from.isoformat() + "Z",
            "timeMax": date_to.isoformat() + "Z",
            "items": [{"id": "primary"}]
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(endpoint, json=payload, headers=self.headers, timeout=5.0)
                if res.status_code == 200:
                    busy_slots = res.json().get("calendars", {}).get("primary", {}).get("busy", [])
                    return busy_slots
            except Exception as e:
                print(f"[CalendarClient] Erreur Google FreeBusy : {e}")
        return []

    async def _google_create_event(self, payload: dict) -> Dict[str, Any]:
        """Crée un événement via Google Calendar API."""
        endpoint = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(endpoint, json=payload, headers=self.headers, timeout=5.0)
                if res.status_code in [200, 201]:
                    return res.json()
            except Exception as e:
                print(f"[CalendarClient] Erreur Google CreateEvent : {e}")
        return {"status": "error"}

    # ── Microsoft Graph (Outlook) ───────────────────────────────────
    async def _outlook_free_busy(self, date_from: datetime, date_to: datetime) -> List[Dict[str, Any]]:
        endpoint = "https://graph.microsoft.com/v1.0/me/calendar/getSchedule"
        payload = {
            "schedules": ["primary"],
            "startTime": {"dateTime": date_from.isoformat(), "timeZone": "UTC"},
            "endTime": {"dateTime": date_to.isoformat(), "timeZone": "UTC"},
            "availabilityViewInterval": 60
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(endpoint, json=payload, headers=self.headers, timeout=5.0)
                if res.status_code == 200:
                    schedule_items = res.json().get("value", [])[0].get("scheduleItems", [])
                    return schedule_items
            except Exception as e:
                print(f"[CalendarClient] Erreur Outlook FreeBusy : {e}")
        return []

    async def _outlook_create_event(self, payload: dict) -> Dict[str, Any]:
        endpoint = "https://graph.microsoft.com/v1.0/me/events"
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(endpoint, json=payload, headers=self.headers, timeout=5.0)
                if res.status_code in [200, 201]:
                    return res.json()
            except Exception as e:
                print(f"[CalendarClient] Erreur Outlook CreateEvent : {e}")
        return {"status": "error"}

    # ── Mocks / Simulation ──
    def _generate_mock_slots(self, date_from: datetime, date_to: datetime) -> List[Dict[str, Any]]:
        """Génère 4 créneaux libres par jour entre date_from et date_to."""
        slots = []
        current_day = date_from
        while current_day <= date_to:
            # Ne planifier que sur les jours ouvrables (lundi à vendredi)
            if current_day.weekday() < 5:
                for hour in [9, 10, 14, 15]:
                    start = current_day.replace(hour=hour, minute=0, second=0, microsecond=0)
                    end = start + timedelta(minutes=45)
                    slots.append({
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "provider": self.provider
                    })
            current_day += timedelta(days=1)
        return slots
