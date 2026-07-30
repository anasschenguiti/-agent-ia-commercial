"""
Client LinkedIn : envoi de messages et InMails via l'API LinkedIn.
"""

import httpx
from typing import Any, Dict, Optional

from app.shared.config import settings


class LinkedInClient:
    """
    Automatisation LinkedIn via l'API officielle (Marketing API) ou Playwright.
    
    IMPORTANT : Respecter les limites de l'API LinkedIn et les CGU.
    - Rate limit : ~100 requêtes/jour par utilisateur
    - Utiliser uniquement des comptes authentifiés via OAuth2
    """

    BASE_URL = "https://api.linkedin.com/v2"

    def __init__(self):
        self.access_token = settings.LINKEDIN_ACCESS_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def send_message(
        self, recipient_urn: str, message: str
    ) -> Dict[str, Any]:
        """Envoie un message à un contact LinkedIn."""
        payload = {
            "recipients": [{"person": {"$URN": recipient_urn}}],
            "subject": "Prise de contact",
            "body": message,
        }
        return await self._post("/messages", payload)

    async def get_profile(self, profile_id: str) -> Dict[str, Any]:
        """Récupère les informations d'un profil LinkedIn."""
        return await self._get(f"/people/{profile_id}")

    async def _post(self, endpoint: str, payload: dict) -> Dict[str, Any]:
        """Requête POST vers l'API LinkedIn (ou simulation)."""
        if not self.access_token or "change-me" in self.access_token:
            return {"status": "simulated", "message": "Mode simulation (remplissez LINKEDIN_ACCESS_TOKEN dans .env pour l'envoi réel)", "endpoint": endpoint}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}{endpoint}",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code in [200, 201]:
                    return response.json()
                return {"status": "failed", "error": response.text, "endpoint": endpoint}
            except Exception as e:
                return {"status": "error", "error": str(e), "endpoint": endpoint}

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        """Requête GET vers l'API LinkedIn (ou simulation)."""
        if not self.access_token or "change-me" in self.access_token:
            return {"status": "simulated", "message": "Mode simulation", "endpoint": endpoint}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}{endpoint}",
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
                return {"status": "failed", "error": response.text, "endpoint": endpoint}
            except Exception as e:
                return {"status": "error", "error": str(e), "endpoint": endpoint}
