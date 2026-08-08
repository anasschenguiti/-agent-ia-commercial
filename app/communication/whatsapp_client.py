"""
Client WhatsApp Business API.
"""

import httpx
from typing import Any, Dict, Optional

from app.shared.config import settings


class WhatsAppClient:
    """
    Envoi de messages via WhatsApp Business API (Meta Cloud API).
    Doc : https://developers.facebook.com/docs/whatsapp/cloud-api
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(self):
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def send_text(self, to: str, message: str) -> Dict[str, Any]:
        """Envoie un message texte simple."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }
        return await self._post(payload)

    async def send_template(
        self, to: str, template_name: str, language: str = "fr", components: list = []
    ) -> Dict[str, Any]:
        """Envoie un message basé sur un template approuvé Meta."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components,
            },
        }
        return await self._post(payload)

    async def _post(self, payload: dict) -> Dict[str, Any]:
        """Effectue un appel POST vers l'API WhatsApp Meta Cloud (ou simulation)."""
        if not self.access_token or "change-me" in self.access_token or not self.phone_number_id:
            return {"status": "simulated", "message": "Mode simulation (remplissez WHATSAPP_ACCESS_TOKEN dans .env pour l'envoi réel)", "payload": payload}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/{self.phone_number_id}/messages",
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code in [200, 201]:
                    return response.json()
                return {"status": "failed", "error": response.text, "payload": payload}
            except Exception as e:
                return {"status": "error", "error": str(e), "payload": payload}
