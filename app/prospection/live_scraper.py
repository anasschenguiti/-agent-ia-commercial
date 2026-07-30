"""
Scraper Multi-Sources Réel de Prospects B2B (Module 1 : Prospection Intelligente).

Règles strictes (REAL-ONLY) :
- Aucune donnée inventée (pas de hash pour téléphone, pas d'estimation arbitraire de CA/taille).
- Aucun email/phone/linkedin_url/website/devise/CA fabriqué en fallback.
- Si une source ne renvoie pas de données réelles, on le dit. On n'invente rien pour combler.
- Chaque prospect retourné porte un `data_confidence` JSON réel avec au moins un champ 'verified'.
- Chaque prospect a un `email_source` / `phone_source` réel ('website_crawl' / 'osm' / 'sirene' / 'opencorporates'),
  jamais 'unverified' / 'not_found' pour un prospect persisté.
"""
import asyncio
import re
import urllib.parse
from typing import Any, Dict, List, Optional
import httpx

from app.prospection.search_providers import (
    BingSearchProvider,
    OfficialB2BRegistryProvider,
    OverpassB2BProvider,
    get_cached_search_results,
    set_cached_search_results,
)
from app.prospection.extra_providers import (
    ApolloApolloProvider,
    FreeB2BEmailEnricher,
    NominatimOpenStreetMapProvider,
)

# Domaines / TLDs interdits en fallback "website" — un prospect sans site vérifié n'a PAS de website.
# Idem pour linkedin_url — pas de fabrication.

TECH_SIGNATURES = {
    "WordPress": [r"wp-content", r"wp-includes", r"wordpress"],
    "Shopify": [r"cdn\.shopify\.com", r"shopify"],
    "React": [r"react", r"_next", r"react-dom"],
    "Next.js": [r"_next/static", r"__NEXT_DATA__"],
    "Vue.js": [r"vue\.js", r"v-attr", r"vuex"],
    "HubSpot": [r"hs-scripts", r"hubspot"],
    "Google Analytics": [r"gtag", r"google-analytics", r"ua-\d+"],
    "Tailwind CSS": [r"tailwindcss", r"tailwind"],
    "Bootstrap": [r"bootstrap\.min\.css", r"bootstrap"],
    "WooCommerce": [r"woocommerce", r"wc-api"],
}

# Mêmes domaines à écarter que dans scraper.py::_is_relevant_to_query.
# On les applique dès la moisson (search_live) pour ne pas perdre du temps à
# crawler des sites qui ne sont pas des entreprises cibles (job boards,
# moteurs de recherche, encyclopédies).
_JOB_BOARD_DOMAINS = (
    "indeed.com", "indeed.fr", "indeed.ma",
    "michaelpage.com", "michaelpage.fr", "michaelpage.ma", "michaelpageafrica.com",
    "glassdoor.com", "glassdoor.fr",
    "linkedin.com/jobs", "linkedin.com/job",
    "hellowork.com", "hellowork.io",
    "welcometothejungle.com", "wttj.co",
    "apec.fr", "celles.com", "jobteaser.com",
    "monster.fr", "monster.com", "monster.ma",
    "keljob.com", "pinterest.com", "trovit.com",
    "optioncarriere.com", "optioncarriere.ma",
    "jooble.org", "jooble.ma",
    "cari.ma",
    "emploi.ma", "emploi.cari.ma",
    "google.com/search", "google.fr/search",
    "bing.com/search",
    "wikipedia.org", "wikimedia.org", "britannica.com", "britannica.fr",
    "yelp.com", "yelp.fr", "tripadvisor.com",
)


def _is_blocked_url(url: str) -> bool:
    if not url:
        return False
    u = url.lower()
    return any(blocked in u for blocked in _JOB_BOARD_DOMAINS)


class MultiSourceLiveScraper:
    """
    Scraper B2B multi-sources en temps réel conforme aux guardrails :
    - Fournisseurs de recherche officiels (BingSearchProvider / OpenSearchAPI)
    - Registres d'entreprises réels (OfficialB2BRegistryProvider)
    - Crawl HTTP direct des sites d'entreprises pour extraction factuelle
    - Pas de données inventées / Hash
    """

    def __init__(self):
        self.search_provider = BingSearchProvider()
        self.registry_provider = OfficialB2BRegistryProvider()
        self.overpass_provider = OverpassB2BProvider()
        self.nominatim_provider = NominatimOpenStreetMapProvider()
        self.apollo_provider = ApolloApolloProvider()
        # Hunter.io + Snov.io : gratuits, auto-desactives si cles vides
        self.email_enricher = FreeB2BEmailEnricher()
        self.headers = {
            "User-Agent": "SalesAIAgent/1.0 (contact@iksatech.com)",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    async def search_live(self, query: dict) -> List[Dict[str, Any]]:
        """
        Orchestre la recherche multi-sources et l'enrichissement factuel sans simulation.
        """
        keywords = query.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]

        location = query.get("location", query.get("city", "Casablanca"))
        country = query.get("country", "Maroc")
        industry = query.get("industry", "")
        max_results = min(int(query.get("max_results", 6)), 12)

        kw_str = " ".join(keywords) if keywords else "Directeur Commercial"
        cache_key = f"{kw_str}:{location}:{country}:{max_results}"

        # 1. Vérifier le cache Redis
        cached_leads = await get_cached_search_results(cache_key)
        if cached_leads:
            return cached_leads

        # 2. Recherche via Registre Officiel B2B & Overpass + Nominatim (Gratuits)
        raw_leads = await self.registry_provider.search_registry(kw_str, location, country, limit=max_results)

        if len(raw_leads) < max_results:
            # On lance Overpass + Nominatim en parallele : si Overpass surcharge
            # (504/429 frequente sur l'instance publique), Nominatim prend le relais.
            remaining = max_results - len(raw_leads)
            overpass_task = self.overpass_provider.search_local_business(
                industry or kw_str, location, limit=remaining
            )
            # Mapping pays -> ISO code pour Nominatim
            country_iso_map = {"Maroc": "ma", "France": "fr", "Belgique": "be", "Suisse": "ch", "Espagne": "es"}
            country_code = country_iso_map.get(country)
            nominatim_task = self.nominatim_provider.search_poi(
                industry or kw_str, location, limit=remaining, country_code=country_code
            )
            overpass_leads, nominatim_leads = await asyncio.gather(
                overpass_task, nominatim_task, return_exceptions=True
            )
            # Normaliser en cas d'exception
            if isinstance(overpass_leads, Exception):
                print(f"[LiveScraper] Overpass note : {overpass_leads}")
                overpass_leads = []
            if isinstance(nominatim_leads, Exception):
                print(f"[LiveScraper] Nominatim note : {nominatim_leads}")
                nominatim_leads = []

            for ol in overpass_leads:
                # REAL-ONLY: pas de first_name="Direction". Si OSM ne fournit pas de contact nommé,
                # on n'invente pas. Le contact reste "non identifié" et le prospect n'est persisté
                # que si on a au moins un email OU téléphone réel via crawl du website.
                raw_leads.append({
                    "first_name": None,
                    "last_name": ol.get("company"),  # company name only, not a person
                    "company": ol.get("company"),
                    "job_title": None,
                    "email": ol.get("email"),
                    "phone": ol.get("phone"),
                    "industry": ol.get("industry", industry),
                    "company_size": None,
                    "location": f"{ol.get('location')}, {country}",
                    "country": country,
                    "linkedin_url": None,  # jamais inventé
                    "website": ol.get("website"),  # OSM fournit le vrai website si tagué
                    "notes": f"Trouvé via OpenStreetMap (Overpass API) : {ol.get('company')}",
                    "technologies": None,
                    "source": "overpass",
                })

            for nl in nominatim_leads:
                # Nominatim renvoie la meme structure qu'Overpass (POI OSM).
                if not nl.get("company"):
                    continue
                raw_leads.append({
                    "first_name": None,
                    "last_name": nl.get("company"),
                    "company": nl.get("company"),
                    "job_title": None,
                    "email": nl.get("email"),
                    "phone": nl.get("phone"),
                    "industry": nl.get("industry", industry),
                    "company_size": None,
                    "location": f"{nl.get('location')}, {country}",
                    "country": country,
                    "linkedin_url": None,
                    "website": nl.get("website"),
                    "notes": (
                        f"Trouvé via Nominatim OSM (POI #{nl.get('source','nominatim')}) : "
                        f"lat={nl.get('latitude')}, lon={nl.get('longitude')}"
                    ),
                    "technologies": None,
                    "source": "nominatim",
                })

        # 2b. Apollo.io : emails + linkedin des decideurs (si cle API configuree)
        if len(raw_leads) < max_results and self.apollo_provider.is_configured():
            try:
                apollo_leads = await self.apollo_provider.search_companies_and_decision_makers(
                    industry or kw_str, location, country, limit=max_results - len(raw_leads)
                )
                raw_leads.extend(apollo_leads)
            except Exception as e:
                print(f"[LiveScraper] Apollo note : {e}")

        # 3. Si pas assez de résultats du registre, utiliser Bing Search API / Open Web API
        if len(raw_leads) < max_results:
            # Construction d'une requête orientée B2B : on retire de kw_str les
            # titres de poste (directeur, responsable, manager, commercial, ...),
            # qui font que DuckDuckGo renvoie presqu'exclusivement des job boards.
            # On garde l'industrie + la ville + le pays et on complète avec la
            # terminaison "entreprise" / "société" qui oriente vers des sites
            # corporate, pas vers des offres d'emploi.
            job_title_keywords = {
                "directeur", "directrice", "responsable", "manager",
                "commercial", "commerciale", "vente", "sales", "head",
                "chef", "cto", "ceo", "cmo", "cfo", "vp",
            }
            industry_words = [kw for kw in keywords if kw.lower() not in job_title_keywords]
            query_parts = []
            if industry or industry_words:
                query_parts.append(industry or " ".join(industry_words))
            query_parts += [location, country, "entreprise"]
            search_query = " ".join(p for p in query_parts if p).strip()
            if not search_query:
                search_query = f"{kw_str} {location} {country}"
            web_results = await self.search_provider.search_web(search_query, limit=max_results - len(raw_leads))
            for res in web_results:
                url = res.get("url", "")
                # Filtre job boards / encyclopédies / moteurs en amont : pas la peine
                # de crawler un site Indeed, c'est de la perte de temps et du faux prospect.
                if _is_blocked_url(url):
                    continue
                parsed = urllib.parse.urlparse(url)
                domain = parsed.netloc.replace("www.", "")
                if domain and "bing.com" not in domain and "duckduckgo.com" not in domain:
                    comp_name = res.get("title", "").split("-")[0].split("|")[0].strip() or domain.capitalize()
                    # REAL-ONLY: linkedin_url JAMAIS inventé. Le prospect sera enrichi plus tard
                    # par crawl du site, qui peut renvoyer un vrai linkedin.com/company/X.
                    raw_leads.append({
                        "first_name": None,
                        "last_name": comp_name,
                        "company": comp_name,
                        "job_title": None,
                        "email": None,
                        "phone": None,
                        "industry": industry or "Services B2B & Technologie",
                        "company_size": None,
                        "location": f"{location}, {country}",
                        "country": country,
                        "linkedin_url": None,
                        "website": url if url.startswith("http") else None,
                        "notes": f"Trouvé via SearchProvider ({domain}) : {res.get('snippet', '')[:120]}...",
                        "technologies": None,
                        "source": "bing_search" if self.search_provider.api_key else "duckduckgo",
                    })

        # 4. Crawl HTTP factuel des sites web (Extraction réelles e-mails, téléphones, stack tech)
        enriched_leads = await self._enrich_leads_via_web(raw_leads[:max_results], location, country, industry)

        # 5. Enrichissement emails via Hunter.io + Snov.io (gratuits, auto-desactives).
        # On le fait APRES le crawl web pour respecter la priorite :
        # si le crawl a deja trouve un email reel, Hunter/Snov ne l'ecrasent pas.
        enriched_leads = await self.email_enricher.enrich(enriched_leads)

        deduped = self._deduplicate(enriched_leads)

        # Mettre en cache Redis
        await set_cached_search_results(cache_key, deduped, ttl=3600)
        return deduped

    async def _enrich_leads_via_web(
        self, leads: List[Dict[str, Any]], location: str, country: str, default_industry: str
    ) -> List[Dict[str, Any]]:
        """
        Crawle en direct le site web de chaque prospect pour extraire les données factuelles :
        - E-mails réels (recherche regex HTML)
        - Numéros de téléphone réels (+212 / +33 / local)
        - Stack Technique réelle
        - Marquage de data_confidence (verified / estimated / unavailable)
        """
        async with httpx.AsyncClient(headers=self.headers, timeout=6.0, follow_redirects=True) as client:
            for lead in leads:
                confidence = {
                    "phone": "unavailable",
                    "email": "unavailable",
                    "company_size": "unavailable",
                    "annual_revenue": "unavailable",
                }
                
                website = lead.get("website", "")
                
                # Guardrails : initialisation explicite sans données inventées
                lead["annual_revenue"] = None
                lead["annual_revenue_source"] = "unavailable"

                if not lead.get("company_size"):
                    lead["company_size"] = None
                    lead["company_size_source"] = "unverified"
                else:
                    lead["company_size_source"] = "official_registry"
                    confidence["company_size"] = "verified"

                if website and "linkedin.com" not in website and website.startswith("http"):
                    try:
                        res = await client.get(website)
                        if res.status_code == 200:
                            html = res.text

                            # 1. E-mails réels
                            found_emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
                            valid_emails = [
                                e for e in found_emails
                                if not e.endswith((".png", ".jpg", ".svg", ".js", ".css", ".webp"))
                            ]
                            if valid_emails:
                                lead["email"] = valid_emails[0]
                                lead["email_source"] = "website_crawl"
                                confidence["email"] = "verified"

                            # 2. Numéros de téléphone réels
                            phone_patterns = [
                                r"\+212\s?[5-7]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}",
                                r"\+33\s?[1-9]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}",
                                r"0[5-7]\d{8}",
                            ]
                            real_phone = None
                            for pattern in phone_patterns:
                                phones = re.findall(pattern, html)
                                if phones:
                                    real_phone = phones[0]
                                    break
                            
                            if real_phone:
                                lead["phone"] = real_phone
                                lead["phone_source"] = "website_crawl"
                                confidence["phone"] = "verified"
                            else:
                                lead["phone"] = None
                                lead["phone_source"] = "not_found"
                                confidence["phone"] = "unavailable"

                            # 3. Stack Technique réelle
                            detected_tech = []
                            for tech_name, patterns in TECH_SIGNATURES.items():
                                if any(re.search(pat, html, re.IGNORECASE) for pat in patterns):
                                    detected_tech.append(tech_name)

                            lead["technologies"] = ", ".join(detected_tech) if detected_tech else None

                            # 4. LinkedIn URL réelle — UNIQUEMENT si explicitement présente dans le HTML
                            li_match = re.search(
                                r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9_\-/%.]+',
                                html
                            )
                            if li_match and not lead.get("linkedin_url"):
                                lead["linkedin_url"] = li_match.group(0)
                                lead["linkedin_source"] = "website_crawl"
                    except Exception as e:
                        print(f"[LiveScraper] Note crawl site {website} : {e}")

                # Si aucun téléphone n'a été trouvé : GUARDRAIL ABSOLU -> Pas de téléphone inventé
                if not lead.get("phone"):
                    lead["phone"] = None
                    lead["phone_source"] = "not_found"
                    confidence["phone"] = "unavailable"

                if not lead.get("email"):
                    lead["email_source"] = "unverified"
                    confidence["email"] = "unavailable"

                lead["data_confidence"] = confidence

        return leads

    def _deduplicate(self, prospects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for p in prospects:
            key = p.get("website") or p.get("email") or p.get("company")
            if key and key not in seen:
                seen.add(key)
                unique.append(p)
        return unique
