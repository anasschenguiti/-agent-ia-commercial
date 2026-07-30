"""
Adaptateur HubSpot CRM.
Encapsule les appels à l'API HubSpot v3.
"""

import httpx
from typing import Any, Dict, List

from app.shared.config import settings


import httpx
from typing import Any, Dict, List

from app.shared.config import settings


class HubSpotAdapter:
    """
    Connecteur vers l'API HubSpot.
    Doc : https://developers.hubspot.com/docs/api/crm/contacts
    """

    BASE_URL = "https://api.hubapi.com"

    def __init__(self):
        self.api_key = settings.HUBSPOT_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("change-me") and len(self.api_key) > 5)

    async def upsert_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Crée ou met à jour un contact dans HubSpot."""
        if not self._is_configured():
            return {"status": "simulated", "action": "upsert_contact", "contact": contact}

        email = contact.get("email")
        async with httpx.AsyncClient() as client:
            try:
                # 1. Rechercher si le contact existe déjà par son email
                contact_id = None
                if email:
                    search_payload = {
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email
                            }]
                        }]
                    }
                    search_res = await client.post(
                        f"{self.BASE_URL}/crm/v3/objects/contacts/search",
                        json=search_payload,
                        headers=self.headers,
                        timeout=5.0
                    )
                    if search_res.status_code == 200:
                        results = search_res.json().get("results", [])
                        if results:
                            contact_id = results[0]["id"]

                # 2. Si le contact existe, on le met à jour. Sinon on le crée.
                if contact_id:
                    res = await client.patch(
                        f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}",
                        json={"properties": contact},
                        headers=self.headers,
                        timeout=5.0
                    )
                else:
                    res = await client.post(
                        f"{self.BASE_URL}/crm/v3/objects/contacts",
                        json={"properties": contact},
                        headers=self.headers,
                        timeout=5.0
                    )
                
                if res.status_code in [200, 201]:
                    return {"status": "success", "data": res.json()}
                return {"status": "error", "code": res.status_code, "detail": res.text}
            except Exception as e:
                print(f"[HubSpotAdapter] Erreur lors de l'upsert : {e}")
                return {"status": "error", "detail": str(e)}

    async def list_contacts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère la liste des contacts HubSpot."""
        if not self._is_configured():
            return []

        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(
                    f"{self.BASE_URL}/crm/v3/objects/contacts?limit={limit}",
                    headers=self.headers,
                    timeout=5.0
                )
                if res.status_code == 200:
                    return res.json().get("results", [])
                return []
            except Exception as e:
                print(f"[HubSpotAdapter] Erreur lors de la récupération : {e}")
                return []

    async def update_deal_stage(self, contact_id: str, stage: str) -> Dict[str, Any]:
        """Met à jour l'étape pipeline d'un deal associé au contact."""
        if not self._is_configured():
            return {"status": "simulated", "contact_id": contact_id, "stage": stage}

        async with httpx.AsyncClient() as client:
            try:
                # 1. Lire les associations deals pour le contact
                assoc_res = await client.get(
                    f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}?associations=deals",
                    headers=self.headers,
                    timeout=5.0
                )
                if assoc_res.status_code != 200:
                    return {"status": "error", "detail": "Impossible de lire le contact"}
                
                associations = assoc_res.json().get("associations", {}).get("deals", {}).get("results", [])
                if not associations:
                    return {"status": "warning", "detail": "Aucun deal associé trouvé"}
                
                # 2. Mettre à jour le premier deal associé
                deal_id = associations[0]["id"]
                res = await client.patch(
                    f"{self.BASE_URL}/crm/v3/objects/deals/{deal_id}",
                    json={"properties": {"dealstage": stage}},
                    headers=self.headers,
                    timeout=5.0
                )
                if res.status_code == 200:
                    return {"status": "success", "data": res.json()}
                return {"status": "error", "code": res.status_code, "detail": res.text}
            except Exception as e:
                print(f"[HubSpotAdapter] Erreur lors de la modification du dealstage : {e}")
                return {"status": "error", "detail": str(e)}

    async def create_activity(self, payload: dict) -> Dict[str, Any]:
        """Enregistre une activité (note de communication) dans HubSpot."""
        if not self._is_configured():
            return {"status": "simulated", "activity": payload}

        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{self.BASE_URL}/crm/v3/objects/notes",
                    json={"properties": payload},
                    headers=self.headers,
                    timeout=5.0
                )
                if res.status_code in [200, 201]:
                    return {"status": "success", "data": res.json()}
                return {"status": "error", "code": res.status_code, "detail": res.text}
            except Exception as e:
                print(f"[HubSpotAdapter] Erreur d'enregistrement d'activité : {e}")
                return {"status": "error", "detail": str(e)}
