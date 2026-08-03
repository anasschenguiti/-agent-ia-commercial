"""
Fournisseurs de recherche abstraits et Registres d'entreprises officiels (SearchProvider & OpenDataProvider).
Respecte les guardrails : pas de scraping HTML brut risqué de Google/LinkedIn, throttling et cache Redis.
"""
import abc
import hashlib
import json
import time
import urllib.parse
from typing import Any, Dict, List, Optional
import httpx

from app.shared.config import settings
from app.shared.redis_client import get_redis_client


class SearchProvider(abc.ABC):
    """Interface abstraite pour les moteurs de recherche officiels."""

    @abc.abstractmethod
    async def search_web(self, query_str: str, limit: int = 6) -> List[Dict[str, Any]]:
        pass


class BingSearchProvider(SearchProvider):
    """Fournisseur de recherche Web Bing Search API / Fallback structuré."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "BING_SEARCH_API_KEY", "")
        self.endpoint = "https://api.bing.microsoft.com/v7.0/search"

    async def search_web(self, query_str: str, limit: int = 6) -> List[Dict[str, Any]]:
        if not self.api_key:
            # Fallback fournisseur de recherche Open Web API sécurisé
            return await self._search_open_web_api(query_str, limit)

        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {"q": query_str, "count": limit, "mkt": "fr-FR"}
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.get(self.endpoint, headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    web_pages = data.get("webPages", {}).get("value", [])
                    results = []
                    for page in web_pages[:limit]:
                        results.append({
                            "title": page.get("name"),
                            "url": page.get("url"),
                            "snippet": page.get("snippet"),
                        })
                    return results
            except Exception as e:
                print(f"[BingSearchProvider] Erreur : {e}")
        return await self._search_open_web_api(query_str, limit)

    async def _search_open_web_api(self, query_str: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback sécurisé via scraping HTML public DuckDuckGo sans API key.

        Le User-Agent est volontairement déclaré comme un outil, jamais comme un
        navigateur réel : DuckDuckGo/Overpass renvoient 406 si on prétend être
        Chrome/Mozilla (anti-bot basique)."""
        from bs4 import BeautifulSoup
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "SalesAIAgent/1.0 (contact@iksatech.com)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        data = {"q": query_str, "b": ""}
        results = []
        async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
            try:
                res = await client.post(url, data=data)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    # DuckDuckGo HTML 2026 : chaque résultat est un bloc
                    # <div class="links_main ... result__body"> contenant
                    #   - <a class="result__a" href="...">  -> titre + URL directe
                    #   - <a class="result__snippet" href="..."> -> snippet + URL
                    #   - <a class="result__url" href="...">  -> URL affichée
                    # L'ancien code cherchait 'h2.result__title' qui est juste le wrapper
                    # du titre, ce qui produisait des titres vides. On itère maintenant
                    # sur les blocs result__body.
                    for body in soup.find_all('div', class_='result__body', limit=limit):
                        a_title = body.find('a', class_='result__a')
                        a_snippet = body.find('a', class_='result__snippet')
                        a_url = body.find('a', class_='result__url')

                        title = a_title.get_text(strip=True) if a_title else ""
                        snippet = a_snippet.get_text(strip=True) if a_snippet else ""
                        raw_link = (
                            (a_title.get('href') if a_title else None)
                            or (a_url.get('href') if a_url else None)
                            or (a_snippet.get('href') if a_snippet else None)
                        )

                        if not (title and raw_link):
                            continue

                        # DuckDuckGo wrappe les liens externes en /?uddg=<encoded> :
                        # on décode pour récupérer l'URL réelle.
                        link = raw_link
                        if "uddg=" in link:
                            try:
                                link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])
                            except Exception:
                                pass

                        if link.startswith("//"):
                            link = "https:" + link
                        elif link.startswith("/"):
                            link = "https://duckduckgo.com" + link

                        results.append({
                            "title": title,
                            "url": link,
                            "snippet": snippet,
                        })
            except Exception as e:
                print(f"[OpenSearchHTML] Erreur : {e}")
        return results


class OverpassB2BProvider:
    """Fournisseur de données via OpenStreetMap Overpass API (B2B Local, 100% Gratuit)."""
    
    async def search_local_business(self, industry: str, location: str, limit: int = 5) -> List[Dict[str, Any]]:
        # Mapping simple d'industries vers tags OSM
        tag = 'office'
        if 'web' in industry.lower() or 'tech' in industry.lower() or 'software' in industry.lower():
            tag = 'office=it'
        elif 'marketing' in industry.lower() or 'agence' in industry.lower():
            tag = 'office=advertising_agency'
        elif 'consulting' in industry.lower() or 'conseil' in industry.lower():
            tag = 'office=consulting'
            
        # On NE PAS utiliser de f-string pour le corps de la requête Overpass :
        # les guillemets doubles autour de la clé/valeur OSM se font manger par
        # le triple-quoted f-string et la query sort malformée
        # (ex: node['office'=consulting] au lieu de node["office"="consulting"]),
        # ce qui faisait silencieusement échouer toutes les recherches.
        tag_key, _, tag_value = tag.partition("=")
        kv_clause = f'["{tag_key}"="{tag_value}"]' if tag_value else f'["{tag_key}"]'
        overpass_query = (
            f'[out:json][timeout:15];'
            f'area[name~"{location}", i]->.searchArea;'
            f'(node{kv_clause}(area.searchArea);'
            f'way{kv_clause}(area.searchArea););'
            f'out center {limit};'
        )
        
        url = "https://overpass-api.de/api/interpreter"
        # Overpass renvoie 406 Not Acceptable si on prétend être un navigateur
        # réel. On se déclare comme un outil (cf. usage policy Overpass).
        headers = {"User-Agent": "SalesAIAgent/1.0 (contact@iksatech.com)"}
        results = []
        async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
            try:
                res = await client.post(url, data={"data": overpass_query})
                if res.status_code == 200:
                    data = res.json()
                    for element in data.get("elements", []):
                        tags = element.get("tags", {})
                        if tags.get("name"):
                            results.append({
                                "company": tags.get("name"),
                                "website": tags.get("website") or tags.get("contact:website"),
                                "phone": tags.get("phone") or tags.get("contact:phone"),
                                "email": tags.get("email") or tags.get("contact:email"),
                                "industry": tags.get("office") or tags.get("amenity") or industry,
                                "location": location
                            })
            except Exception as e:
                print(f"[OverpassAPI] Erreur : {e}")
        return results


class OpenDataProvider(abc.ABC):
    """Interface abstraite pour les registres officiels d'entreprises."""

    @abc.abstractmethod
    async def search_registry(self, keywords: str, location: str, country: str, limit: int = 5) -> List[Dict[str, Any]]:
        pass


class OfficialB2BRegistryProvider(OpenDataProvider):
    """Fournisseur de données d'entreprises basés sur les annuaires & registres officiels."""

    async def search_registry(self, keywords: str, location: str, country: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recherche dans les API de registres officiels (OpenCorporates / Sirene API)."""
        is_france = any(c in country.lower() or c in location.lower() for c in ["france", "paris", "lyon"])
        if is_france:
            return await self._search_sirene_france(keywords, location, limit)
        return await self._search_opencorporates(keywords, location, country, limit)

    async def _search_sirene_france(self, keywords: str, location: str, limit: int) -> List[Dict[str, Any]]:
        url = f"https://recherche-entreprises.api.gouv.fr/search?q={urllib.parse.quote(keywords + ' ' + location)}&per_page={limit}"
        headers = {"User-Agent": "SalesAIAgent/1.0 (contact@iksatech.com)"}
        results = []
        async with httpx.AsyncClient(headers=headers, timeout=6.0) as client:
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    for comp in data.get("results", [])[:limit]:
                        nom = comp.get("nom_complet") or comp.get("nom_raison_sociale")
                        dirigeants = comp.get("dirigeants", [])
                        # REAL-ONLY: si aucun dirigeant n'est fourni par l'API, on NE FABRIQUE PAS.
                        # Le prospect restera 'Direction non identifiée' et le service l'écartera
                        # si aucun email/phone réel n'est trouvé ensuite.
                        # REAL-ONLY: pas de fabrication du dirigeant. Si l'API Sirene
                        # fournit nom/prenom/qualite, on les utilise tels quels.
                        # Sinon le prospect restera "non identifie" et le service
                        # l'ecartera si aucun email/phone reel n'est trouve ensuite.
                        if dirigeants:
                            d0 = dirigeants[0]
                            fn = (d0.get("prenoms") or "").strip() or None
                            ln = (d0.get("nom") or "").strip() or None
                            # La vraie qualite du registre INSEE ("President de SAS",
                            # "Gerant", "Directeur general", etc.) — pas un generique.
                            role = (d0.get("qualite") or "Dirigeant").strip() or "Dirigeant"
                        else:
                            fn, ln, role = None, nom, None

                        # REAL-ONLY: site web uniquement si l'API Sirene le fournit réellement.
                        site = comp.get("site_internet")  # peut être None
                        # Siege (adresse reelle) — utile pour le scoring localisation
                        siege = comp.get("siege") or {}
                        siege_addr = siege.get("adresse") or ""
                        siege_cp = siege.get("code_postal") or ""
                        full_location = siege_addr or f"{location}, France"
                        results.append({
                            "first_name": fn,
                            "last_name": ln,
                            "company": nom,
                            "job_title": role,
                            "email": None,
                            "phone": None,
                            "industry": comp.get("libelle_activite_principale", "Secteur Officiel Sirene"),
                            "company_size": comp.get("tranche_effectif_salarie"),
                            "location": full_location,
                            "country": "France",
                            "website": site,
                            "linkedin_url": None,
                            "notes": (
                                f"Registre Officiel INSEE (SIREN: {comp.get('siren')}"
                                f"{', CP ' + siege_cp if siege_cp else ''}"
                                f", qualite: {role})"
                            ),
                            "source": "sirene",
                        })
            except Exception as e:
                print(f"[SireneProvider] Erreur API Sirene : {e}")
        return results

    async def _search_opencorporates(self, keywords: str, location: str, country: str, limit: int) -> List[Dict[str, Any]]:
        url = f"https://api.opencorporates.com/v0.4/companies/search?q={urllib.parse.quote(keywords + ' ' + location)}"
        headers = {"User-Agent": "SalesAIAgent/1.0 (contact@iksatech.com)"}
        results = []
        async with httpx.AsyncClient(headers=headers, timeout=6.0) as client:
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    companies = data.get("results", {}).get("companies", [])
                    for c_entry in companies[:limit]:
                        c = c_entry.get("company", {})
                        comp_name = c.get("name")
                        if comp_name:
                            # REAL-ONLY: pas de fabrication de website. OpenCorporates ne fournit
                            # pas systématiquement un site web officiel ; on laisse None si absent.
                            results.append({
                                "first_name": None,
                                "last_name": comp_name,
                                "company": comp_name,
                                "job_title": None,
                                "email": None,
                                "phone": None,
                                "industry": c.get("company_type", "Registre Officiel B2B"),
                                "company_size": None,
                                "location": f"{location}, {country}",
                                "country": country,
                                "website": None,
                                "linkedin_url": None,
                                "notes": f"Registre OpenCorporates (#{c.get('company_number')})",
                                "source": "opencorporates",
                            })
            except Exception as e:
                print(f"[OpenCorporates] Erreur : {e}")
        return results


async def get_cached_search_results(query_str: str) -> Optional[List[Dict[str, Any]]]:
    """Récupère les résultats de recherche en cache Redis."""
    try:
        r = await get_redis_client()
        q_hash = hashlib.sha256(query_str.encode()).hexdigest()
        cached = await r.get(f"search_cache:{q_hash}")
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None


async def set_cached_search_results(query_str: str, results: List[Dict[str, Any]], ttl: int = 3600) -> None:
    """Enregistre les résultats de recherche dans Redis avec TTL."""
    try:
        r = await get_redis_client()
        q_hash = hashlib.sha256(query_str.encode()).hexdigest()
        await r.set(f"search_cache:{q_hash}", json.dumps(results), ex=ttl)
    except Exception:
        pass
