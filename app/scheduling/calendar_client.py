"""
Client calendrier : Google Calendar / Outlook via Microsoft Graph.

Week 1 (securite) : on n'utilise PLUS SECRET_KEY comme bearer.
Les tokens OAuth2 sont configures via GOOGLE_CALENDAR_TOKEN / OUTLOOK_TOKEN.
Un hook de refresh est expose ; en production, brancher le flow OAuth2 complet.
"""

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
        # Tokens dedies (NE PLUS UTILISER settings.SECRET_KEY).
        # Hook de refresh : en prod, implementer le flow OAuth2 ici.
        self.access_token = (
            settings.GOOGLE_CALENDAR_TOKEN
            if provider == "google"
            else settings.OUTLOOK_TOKEN
        )
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _is_configured(self) -> bool:
        """Vrai uniquement si un token reel (non vide, non placeholder) est defini."""
        if not self.access_token:
            return False
        bad_prefixes = ("change-me", "dev-secret", "your-", "CHANGE_ME")
        return not any(self.access_token.startswith(p) for p in bad_prefixes)

    async def _refresh_token(self) -> None:
        """Hook de refresh OAuth2. En prod : appeler le endpoint token provider."""
        # Placeholder : on relit juste la config. A implementer avec le
        # flow OAuth2 (client_id, client_secret, refresh_token) pour la prod.
        self.access_token = (
            settings.GOOGLE_CALENDAR_TOKEN
            if self.provider == "google"
            else settings.OUTLOOK_TOKEN
        )
        self.headers["Authorization"] = f"Bearer {self.access_token}"

    async def get_free_slots(
        self, date_from: datetime, date_to: datetime
    ) -> List[Dict[str, Any]]:
        """Retourne les creneaux libres dans la plage."""
        if not self._is_configured():
            return self._generate_mock_slots(date_from, date_to)

        if self.provider == "google":
            return await self._google_free_busy(date_from, date_to)
        elif self.provider == "outlook":
            return await self._outlook_free_busy(date_from, date_to)
        return []

    async def create_event(self, payload: dict) -> Dict[str, Any]:
        """Cree un evenement dans le calendrier."""
        if not self._is_configured():
            return {"status": "simulated", "event_id": "event_mock_999", "event": payload}

        if self.provider == "google":
            return await self._google_create_event(payload)
        elif self.provider == "outlook":
            return await self._outlook_create_event(payload)
        return {"status": "unsupported_provider"}

    async def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Recupere un evenement par son ID."""
        if not self._is_configured():
            return {"id": event_id, "summary": "Reunion Commerciale IA", "status": "confirmed"}

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
        """Supprime un evenement."""
        if not self._is_configured():
            print(f"[CalendarClient] Suppression simulee de l'evenement {event_id}")
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
            "items": [{"id": "primary"}],
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(endpoint, json=payload, headers=self.headers, timeout=5.0)
                if res.status_code == 200:
                    busy_slots = res.json().get("calendars", {}).get("primary", {}).get("busy", [])
                    return busy_slots
                if res.status_code == 401:
                    await self._refresh_token()
            except Exception as e:
                print(f"[CalendarClient] Erreur Google FreeBusy : {e}")
        return []

    async def _google_create_event(self, payload: dict) -> Dict[str, Any]:
        """Cree un evenement via Google Calendar API."""
        endpoint = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(endpoint, json=payload, headers=self.headers, timeout=5.0)
                if res.status_code in [200, 201]:
                    return res.json()
                if res.status_code == 401:
                    await self._refresh_token()
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
            "availabilityViewInterval": 60,
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
        """Genere 4 creneaux libres par jour entre date_from et date_to."""
        slots = []
        current_day = date_from
        while current_day <= date_to:
            if current_day.weekday() < 5:
                for hour in [9, 10, 14, 15]:
                    start = current_day.replace(hour=hour, minute=0, second=0, microsecond=0)
                    end = start + timedelta(minutes=45)
                    slots.append({
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "provider": self.provider,
                    })
            current_day += timedelta(days=1)
        return slots
