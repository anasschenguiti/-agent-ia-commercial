"""
Adaptateur Odoo CRM.
Encapsule les appels a l'API JSON-RPC d'Odoo.

Week 2 (bug fix) : update_deal_stage acceptait un str (nom d'etape) qu'il
envoyait tel quel a Odoo qui attend un integer ID. On resout maintenant
le nom -> integer via search sur crm.stage, avec cache Redis 24h.
"""

import httpx
from typing import Any, Dict, List, Optional

from app.shared.config import settings
from app.shared.redis_client import RedisCache


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
        self._stage_cache = RedisCache(prefix="odoo:stage")

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
                    timeout=5.0,
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
        """Appel JSON-RPC generique (execute_kw) vers un modele Odoo."""
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
                    timeout=5.0,
                )
                if response.status_code == 200:
                    return response.json().get("result", [])
                return []
            except Exception as e:
                print(f"[OdooAdapter] Erreur RPC call sur {model}.{method} : {e}")
                return []

    async def upsert_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Cree ou met a jour un partenaire dans Odoo."""
        if not self._is_configured():
            return {"status": "simulated", "action": "upsert_contact", "contact": contact}

        email = contact.get("email")
        try:
            partner_id = None
            if email:
                existing = await self._call("res.partner", "search", [[("email", "=", email)]])
                if existing:
                    partner_id = existing[0]

            if partner_id:
                await self._call("res.partner", "write", [[partner_id], contact])
                return {"status": "success", "id": partner_id, "action": "write"}
            else:
                new_id = await self._call("res.partner", "create", [contact])
                return {"status": "success", "id": new_id, "action": "create"}
        except Exception as e:
            print(f"[OdooAdapter] Erreur upsert_contact : {e}")
            return {"status": "error", "detail": str(e)}

    async def list_contacts(self) -> List[Dict[str, Any]]:
        """Recupere les partenaires Odoo."""
        if not self._is_configured():
            return []
        return await self._call("res.partner", "search_read", [[], ["name", "email", "phone"]])

    async def _resolve_stage_id(self, stage: str) -> int:
        """
        Resout un nom d'etape CRM en integer ID (Odoo exige un int).
        Utilise un cache Redis 24h pour eviter de re-requeter a chaque appel.
        """
        cache_key = f"name:{stage.lower().strip()}"
        cached = await self._stage_cache.get(cache_key)
        if cached is not None:
            return int(cached)

        # Recherche insensible a la casse.
        rows = await self._call(
            "crm.stage",
            "search_read",
            [[("name", "ilike", stage)], ["id", "name"]],
        )
        if not rows:
            raise ValueError(f"Etape CRM inconnue dans Odoo : {stage!r}")

        stage_id = int(rows[0]["id"])
        await self._stage_cache.set(cache_key, stage_id, ttl=24 * 3600)
        return stage_id

    async def update_deal_stage(self, contact_id: str, stage) -> Dict[str, Any]:
        """
        Met a jour l'etape d'une opportunite CRM Odoo.

        Accepte str (nom d'etape ou ID numerique) ou int.
        Resolut le nom en ID integer via crm.stage avec cache Redis 24h.
        """
        if not self._is_configured():
            return {"status": "simulated", "contact_id": contact_id, "stage": stage}

        try:
            # Resolve stage to integer (Odoo crm.stage.id field)
            if isinstance(stage, str):
                if stage.isdigit():
                    stage_id = int(stage)
                else:
                    stage_id = await self._resolve_stage_id(stage)
            else:
                stage_id = int(stage)

            # Resolve contact_id to partner_id
            contact_str = str(contact_id).strip()
            if contact_str.isdigit():
                partner_id = int(contact_str)
            else:
                # Search partner by email or name if contact_id is non-numeric
                partners = await self._call(
                    "res.partner",
                    "search",
                    [["|", ("email", "=", contact_str), ("name", "ilike", contact_str)]],
                )
                if partners:
                    partner_id = partners[0]
                else:
                    return {
                        "status": "error",
                        "detail": f"Partenaire introuvable pour contact_id={contact_id!r}",
                    }

            lead_ids = await self._call(
                "crm.lead",
                "search",
                [[("partner_id", "=", partner_id)]],
            )
            if lead_ids:
                await self._call(
                    "crm.lead",
                    "write",
                    [lead_ids, {"stage_id": stage_id}],
                )
                return {"status": "success", "lead_ids": lead_ids, "stage_id": stage_id}
            return {"status": "warning", "detail": f"Aucun deal trouve pour le partenaire ID {partner_id}"}
        except Exception as e:
            print(f"[OdooAdapter] Erreur update_deal_stage : {e}")
            return {"status": "error", "detail": str(e)}

    async def create_activity(self, payload: dict) -> Dict[str, Any]:
        """Enregistre une activite dans Odoo."""
        if not self._is_configured():
            return {"status": "simulated", "activity": payload}

        try:
            result = await self._call("mail.activity", "create", [payload])
            return {"status": "success", "result": result}
        except Exception as e:
            print(f"[OdooAdapter] Erreur create_activity : {e}")
            return {"status": "error", "detail": str(e)}
