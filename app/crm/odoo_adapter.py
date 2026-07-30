"""
Adaptateur Odoo CRM.
Encapsule les appels à l'API JSON-RPC d'Odoo.
"""

import httpx
from typing import Any, Dict, List, Optional

from app.shared.config import settings


import httpx
from typing import Any, Dict, List, Optional

from app.shared.config import settings


class OdooAdapter:
    """
    Connecteur vers Odoo via JSON-RPC.
    Doc : https://www.odoo.com/documentation/17.0/developer/reference/external_api.html
    """

    def __init__(self):
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USER
        self.password = settings.ODOO_PASSWORD
        self.uid: Optional[int] = None

    def _is_configured(self) -> bool:
        return bool(
            self.url 
            and not self.url.startswith("https://your-odoo-instance") 
            and self.password 
            and len(self.password) > 0
        )

    async def _authenticate(self) -> int:
        """Authentifie et retourne l'UID utilisateur."""
        if not self._is_configured():
            self.uid = 1
            return self.uid

        async with httpx.AsyncClient() as client:
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "db": self.db,
                    "login": self.username,
                    "password": self.password,
                },
            }
            try:
                response = await client.post(
                    f"{self.url}/web/session/authenticate",
                    json=payload,
                    timeout=5.0
                )
                if response.status_code == 200:
                    res_json = response.json()
                    if "result" in res_json and "uid" in res_json["result"]:
                        self.uid = res_json["result"]["uid"]
                        return self.uid
                self.uid = 1
            except Exception as e:
                print(f"[OdooAdapter] Erreur d'authentification : {e}")
                self.uid = 1
            return self.uid

    async def _call(self, model: str, method: str, args: list) -> Any:
        """Appel JSON-RPC générique (execute_kw) vers un modèle Odoo."""
        if not self._is_configured():
            return []

        if not self.uid:
            await self._authenticate()

        async with httpx.AsyncClient() as client:
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [self.db, self.uid, self.password, model, method, args],
                },
            }
            try:
                response = await client.post(
                    f"{self.url}/jsonrpc",
                    json=payload,
                    timeout=5.0
                )
                if response.status_code == 200:
                    return response.json().get("result", [])
                return []
            except Exception as e:
                print(f"[OdooAdapter] Erreur RPC call sur {model}.{method} : {e}")
                return []

    async def upsert_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Crée ou met à jour un partenaire dans Odoo."""
        if not self._is_configured():
            return {"status": "simulated", "action": "upsert_contact", "contact": contact}

        email = contact.get("email")
        try:
            partner_id = None
            if email:
                # Rechercher si l'email existe
                existing = await self._call("res.partner", "search", [[("email", "=", email)]])
                if existing:
                    partner_id = existing[0]

            if partner_id:
                # Mise à jour
                await self._call("res.partner", "write", [[partner_id], contact])
                return {"status": "success", "id": partner_id, "action": "write"}
            else:
                # Création
                new_id = await self._call("res.partner", "create", [contact])
                return {"status": "success", "id": new_id, "action": "create"}
        except Exception as e:
            print(f"[OdooAdapter] Erreur upsert_contact : {e}")
            return {"status": "error", "detail": str(e)}

    async def list_contacts(self) -> List[Dict[str, Any]]:
        """Récupère les partenaires Odoo."""
        if not self._is_configured():
            return []
        return await self._call("res.partner", "search_read", [[], ["name", "email", "phone"]])

    async def update_deal_stage(self, contact_id: str, stage: str) -> Dict[str, Any]:
        """Met à jour l'étape d'une opportunité CRM Odoo."""
        if not self._is_configured():
            return {"status": "simulated", "contact_id": contact_id, "stage": stage}

        try:
            # Recherche des opportunités liées à ce contact
            lead_ids = await self._call("crm.lead", "search", [[("partner_id", "=", int(contact_id))]])
            if lead_ids:
                # Mise à jour de l'opportunité (Odoo utilise l'ID de l'étape pour stage_id)
                # On écrit le nom de l'étape si stage_id est de type texte, ou on convertit
                await self._call("crm.lead", "write", [lead_ids, {"stage_id": stage}])
                return {"status": "success", "lead_ids": lead_ids}
            return {"status": "warning", "detail": "Aucun deal trouvé pour ce partenaire"}
        except Exception as e:
            print(f"[OdooAdapter] Erreur update_deal_stage : {e}")
            return {"status": "error", "detail": str(e)}

    async def create_activity(self, payload: dict) -> Dict[str, Any]:
        """Enregistre une activité dans Odoo."""
        if not self._is_configured():
            return {"status": "simulated", "activity": payload}

        try:
            result = await self._call("mail.activity", "create", [payload])
            return {"status": "success", "result": result}
        except Exception as e:
            print(f"[OdooAdapter] Erreur create_activity : {e}")
            return {"status": "error", "detail": str(e)}
