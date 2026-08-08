"""
Client Supabase centralisé pour Sales AI Agent.
Gère l'initialisation du SDK Supabase et le contrôle de santé.
"""

from typing import Optional
from app.shared.config import settings

_supabase_client = None


def get_supabase_client():
    """
    Retourne l'instance du client Supabase si configuré dans .env.
    Retourne None si SUPABASE_URL ou SUPABASE_KEY sont vides.
    """
    global _supabase_client

    url = getattr(settings, "SUPABASE_URL", "").strip()
    key = getattr(settings, "SUPABASE_KEY", "").strip()

    if not url or not key:
        return None

    if _supabase_client is None:
        try:
            from supabase import create_client, Client
            _supabase_client = create_client(url, key)
        except Exception as e:
            print(f"[SupabaseClient] Erreur d'initialisation : {e}")
            return None

    return _supabase_client


async def check_supabase_health() -> str:
    """
    Vérifie la connectivité à l'API Supabase pour le router de santé.
    """
    url = getattr(settings, "SUPABASE_URL", "").strip()
    key = getattr(settings, "SUPABASE_KEY", "").strip()

    if not url or not key:
        return "unconfigured (missing SUPABASE_URL / SUPABASE_KEY)"

    client = get_supabase_client()
    if client is None:
        return "offline (initialization failed)"

    try:
        # Simple ping request via REST endpoint check
        import httpx
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        async with httpx.AsyncClient(timeout=4.0) as http_client:
            res = await http_client.get(f"{url}/rest/v1/", headers=headers)
            if res.status_code in (200, 404, 401):
                return "online"
            return f"degraded (status {res.status_code})"
    except Exception as e:
        return f"offline ({e})"
