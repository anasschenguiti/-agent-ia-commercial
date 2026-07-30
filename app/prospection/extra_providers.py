"""
Providers additionnels pour la prospection B2B (100% gratuits).

Sources integrees :
- NominatimOpenStreetMapProvider : POI geolocalises (cafes, restaurants, etc.)
  Endpoint : https://nominatim.openstreetmap.org/search
  Limite : 1 req/s + User-Agent obligatoire.

- ApolloApolloProvider : Plan gratuit verrouille depuis 2024. Conserve comme
  stub auto-desactive (renvoie 0 si 403). A reactivrer si tu prends un plan
  payant un jour.

- HunterDomainProvider : 25 calls/mois gratuits sur hunter.io.
  Endpoint : https://api.hunter.io/v2/domain-search
  Pour chaque site web connu, recupere les emails publics (CEO, CFO,
  contact@, etc.) avec score de confiance.

- SnovioProvider : 50 credits/mois gratuits sur snov.io.
  Endpoint : https://api.snov.io/v2/
  Alternative a Hunter, surtout utile pour .ma, .fr, .eu.

- FreeB2BEmailEnricher : combine Hunter + Snov + crawl web pour maximiser
  la couverture des emails de decideurs sans aucune depense.

REAL-ONLY : aucun email/phone/website/linkedin n'est invente.
"""

import asyncio
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

from app.shared.config import settings


class NominatimOpenStreetMapProvider:
    """
    Recherche de POI via Nominatim OpenStreetMap.
    API REST simple : q=<recherche>&format=json. Endpoint different d'Overpass,
    souvent disponible quand Overpass surcharge.
    """

    ENDPOINT = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        self.headers = {
            "User-Agent": "SalesAIAgent/1.0 (contact@iksatech.com)",
            "Accept": "application/json",
        }

    async def search_poi(
        self,
        keywords: str,
        location: str,
        limit: int = 5,
        country_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params = {
            "q": " ".join(p for p in [keywords.strip(), location.strip()] if p),
            "format": "jsonv2",
            "limit": str(limit),
            "addressdetails": "1",
            "extratags": "1",
            "namedetails": "1",
        }
        if country_code:
            params["countrycodes"] = country_code.lower()

        results: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
            try:
                res = await client.get(self.ENDPOINT, params=params)
                if res.status_code == 200:
                    data = res.json()
                    for poi in data[:limit]:
                        extratags = poi.get("extratags") or {}
                        namedetails = poi.get("namedetails") or {}
                        name = (
                            namedetails.get("name")
                            or poi.get("display_name", "").split(",")[0].strip()
                        )
                        if not name:
                            continue
                        website = extratags.get("website") or extratags.get("contact:website") or extratags.get("url")
                        phone = extratags.get("phone") or extratags.get("contact:phone")
                        email = extratags.get("email") or extratags.get("contact:email")
                        results.append({
                            "company": name,
                            "website": website,
                            "phone": phone,
                            "email": email,
                            "industry": poi.get("type") or poi.get("class") or keywords,
                            "location": location,
                            "latitude": poi.get("lat"),
                            "longitude": poi.get("lon"),
                            "source": "nominatim",
                        })
            except Exception as e:
                print(f"[NominatimProvider] Erreur : {e}")
        return results


class ApolloApolloProvider:
    """
    Provider Apollo.io. Plan gratuit verrouille depuis 2024 : les endpoints
    /mixed_companies et /people/match retournent 403 meme avec cle gratuite.

    Comportement : auto-desactive si on recoit 403. Si jamais tu passes en plan
    payant un jour, reutilise cette classe directement.
    """

    BASE_URL = "https://api.apollo.io/api/v1"
    COMPANY_ENDPOINT = f"{BASE_URL}/mixed_companies/search"
    PEOPLE_ENDPOINT = f"{BASE_URL}/people/search"

    def __init__(self):
        self.api_key = getattr(settings, "APOLLO_API_KEY", "") or ""
        self._disabled_for_plan = False

    def is_configured(self) -> bool:
        return bool(self.api_key) and not self._disabled_for_plan

    async def search_companies_and_decision_makers(
        self,
        keywords: str,
        location: str,
        country: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []

        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }

        results: List[Dict[str, Any]] = []
        decision_maker_titles = [
            "CEO", "Founder", "Owner",
            "CTO", "CMO", "CFO", "COO",
            "VP of Sales", "VP Sales",
            "Directeur General", "Directeur Commercial",
            "Director of Sales", "Head of Sales",
        ]

        company_payload: Dict[str, Any] = {
            "q_keywords": keywords,
            "person_locations": [location],
            "person_country": country,
            "page": 1,
            "per_page": limit,
            "organization_num_employees_ranges": ["1,10", "11,20", "21,50", "51,100", "101,200", "201,500"],
        }

        async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
            try:
                res = await client.post(self.COMPANY_ENDPOINT, json=company_payload)
                if res.status_code == 403:
                    self._disabled_for_plan = True
                    print(f"[ApolloProvider] Plan gratuit : endpoint verrouille. La cle reste en .env mais le provider est desactive. Fallback sur Hunter.io / Snov.io.")
                    return []
                if res.status_code != 200:
                    print(f"[ApolloProvider] Companies endpoint -> {res.status_code}: {res.text[:200]}")
                    return []

                data = res.json()
                companies = data.get("organizations", []) or data.get("accounts", [])
                if not companies:
                    return []

                for comp in companies[:limit]:
                    org_name = comp.get("name")
                    if not org_name:
                        continue
                    domain = comp.get("primary_domain") or comp.get("website_url")
                    base_prospect = {
                        "first_name": None,
                        "last_name": org_name,
                        "company": org_name,
                        "job_title": None,
                        "email": None,
                        "phone": None,
                        "industry": comp.get("industry") or keywords,
                        "company_size": comp.get("estimated_num_employees"),
                        "location": f"{location}, {country}",
                        "country": country,
                        "linkedin_url": comp.get("linkedin_url"),
                        "website": f"https://{domain}" if domain and not str(domain).startswith("http") else domain,
                        "notes": f"Apollo.io (company: {org_name})",
                        "source": "apollo",
                    }
                    people_payload = {
                        "q_keywords": org_name,
                        "person_titles": decision_maker_titles,
                        "person_locations": [location],
                        "page": 1,
                        "per_page": 1,
                    }
                    try:
                        pres = await client.post(self.PEOPLE_ENDPOINT, json=people_payload)
                        if pres.status_code == 200:
                            pdata = pres.json()
                            people = pdata.get("people", []) or pdata.get("contacts", [])
                            if people:
                                p0 = people[0]
                                base_prospect.update({
                                    "first_name": p0.get("first_name"),
                                    "last_name": p0.get("last_name"),
                                    "job_title": p0.get("title"),
                                    "email": p0.get("email"),
                                    "email_source": "apollo" if p0.get("email") else None,
                                    "linkedin_url": p0.get("linkedin_url") or base_prospect["linkedin_url"],
                                    "linkedin_source": "apollo" if p0.get("linkedin_url") else None,
                                })
                    except Exception as e:
                        print(f"[ApolloProvider] People lookup note : {e}")

                    results.append(base_prospect)
                    await asyncio.sleep(0.25)

            except Exception as e:
                print(f"[ApolloProvider] Erreur : {e}")

        return results


def _extract_domain(url: str) -> Optional[str]:
    """Extrait le domain nu (ex: 'webcom.ma') depuis une URL."""
    url = (url or "").strip()
    if not url:
        return None
    if "://" not in url:
        url = "http://" + url
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc or parsed.path
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


class HunterDomainProvider:
    """
    Provider Hunter.io - Recherche d'emails par domaine.

    Free tier : 25 recherches/mois, 50 verifications/mois.
    Inscription : email + password sur https://hunter.io (delivrance immediate
    de la cle API dans le dashboard).

    Endpoint : /v2/domain-search?domain=<domaine>&api_key=<cle>
    Retourne : jusqu'a 10 emails associes au domaine avec score de confiance
    (0-100) et type (generic / personal).

    REAL-ONLY : Hunter ne renvoie QUE des emails crawles sur le web
    (site corporate, signatures email publiques). Aucun email invente.
    """

    ENDPOINT = "https://api.hunter.io/v2/domain-search"

    def __init__(self):
        self.api_key = getattr(settings, "HUNTER_API_KEY", "") or ""

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def enrich_prospects_with_emails(
        self,
        prospects: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return prospects

        priority_patterns = [
            "ceo", "cmo", "cto", "cfo", "coo",
            "founder", "fondateur", "president",
            "directeur", "directrice", "director",
            "sales", "commercial",
            "contact", "info", "hello",
        ]

        async with httpx.AsyncClient(
            headers={"User-Agent": "SalesAIAgent/1.0 (contact@iksatech.com)"},
            timeout=8.0,
        ) as client:
            for p in prospects:
                if p.get("email") and p.get("email_source") in {"website_crawl", "sirene", "snov"}:
                    continue
                website = p.get("website")
                if not website:
                    continue
                domain = _extract_domain(website)
                if not domain:
                    continue

                try:
                    params = {"domain": domain, "api_key": self.api_key, "limit": 10}
                    res = await client.get(self.ENDPOINT, params=params)
                    if res.status_code != 200:
                        if res.status_code == 429:
                            print(f"[Hunter] Rate limit atteint, skip {domain}")
                            break
                        continue

                    data = res.json()
                    hunter_data = data.get("data") or {}
                    emails = hunter_data.get("emails") or []
                    if not emails:
                        continue

                    chosen = None
                    for pattern in priority_patterns:
                        for e in emails:
                            value = (e.get("value") or "").lower()
                            position = (e.get("position") or "").lower()
                            department = (e.get("department") or "").lower()
                            if pattern in value or pattern in position or pattern in department:
                                chosen = e
                                break
                        if chosen:
                            break
                    if not chosen:
                        chosen = emails[0]

                    hunter_email = chosen.get("value")
                    if hunter_email:
                        score = chosen.get("confidence", 0)
                        if score >= 50 or chosen.get("type") == "generic":
                            p["email"] = hunter_email
                            p["email_source"] = "hunter"
                            if not p.get("first_name") and chosen.get("first_name"):
                                p["first_name"] = chosen.get("first_name")
                            if not p.get("last_name") and chosen.get("last_name"):
                                p["last_name"] = chosen.get("last_name")
                            if not p.get("job_title") and chosen.get("position"):
                                p["job_title"] = chosen.get("position")

                except Exception as e:
                    print(f"[Hunter] Erreur pour {domain}: {e}")

                await asyncio.sleep(0.4)

        return prospects


class SnovioProvider:
    """
    Provider Snov.io - Alternative a Hunter.io.

    Free tier : 50 credits/mois.
    Inscription : email + password sur https://snov.io.
    Cle API dans Settings > API.

    Endpoints utilises :
    - /v2/domain-search : liste les emails associes a un domaine
    """

    BASE_URL = "https://api.snov.io/v2"

    def __init__(self):
        self.api_key = getattr(settings, "SNOVIO_API_KEY", "") or ""

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def enrich_prospects_with_emails(
        self,
        prospects: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return prospects

        async with httpx.AsyncClient(
            headers={"User-Agent": "SalesAIAgent/1.0 (contact@iksatech.com)"},
            timeout=8.0,
        ) as client:
            for p in prospects:
                if p.get("email") and p.get("email_source") in {"website_crawl", "sirene", "hunter"}:
                    continue
                website = p.get("website")
                if not website:
                    continue
                domain = _extract_domain(website)
                if not domain:
                    continue

                try:
                    data = {
                        "access_token": self.api_key,
                        "domain": domain,
                        "type": "all",
                        "limit": 5,
                    }
                    res = await client.post(
                        f"{self.BASE_URL}/domain-search", data=data
                    )
                    if res.status_code != 200:
                        if res.status_code == 429:
                            print(f"[Snov] Rate limit atteint, skip {domain}")
                            break
                        continue

                    result = res.json()
                    emails_data = result.get("emails") or []
                    if not emails_data:
                        continue

                    first = emails_data[0]
                    email = first.get("email")
                    if email:
                        p["email"] = email
                        p["email_source"] = "snov"
                        if not p.get("first_name") and first.get("firstName"):
                            p["first_name"] = first.get("firstName")
                        if not p.get("last_name") and first.get("lastName"):
                            p["last_name"] = first.get("lastName")
                        if not p.get("job_title") and first.get("position"):
                            p["job_title"] = first.get("position")

                except Exception as e:
                    print(f"[Snov] Erreur pour {domain}: {e}")

                await asyncio.sleep(0.4)

        return prospects


class FreeB2BEmailEnricher:
    """
    Combine Hunter.io + Snov.io (gratuits) pour maximiser la couverture des
    emails de decideurs SANS depense. Le crawl web (deja integre dans
    live_scraper) reste la source principale.

    Ordre de priorite sur un meme prospect :
    1. Email deja trouve par crawl web (source=website_crawl) - inchange
    2. Hunter.io (25 calls/mois, gratuit)
    3. Snov.io (50 credits/mois, gratuit)
    4. Pas d'invention : si rien, prospect garde email=None
    """

    def __init__(self):
        self.hunter = HunterDomainProvider()
        self.snov = SnovioProvider()

    async def enrich(self, prospects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.hunter.is_configured():
            prospects = await self.hunter.enrich_prospects_with_emails(prospects)
        if self.snov.is_configured():
            prospects = await self.snov.enrich_prospects_with_emails(prospects)
        return prospects
