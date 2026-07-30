"""
Scraper de prospects intelligent via IA (Ollama qwen3:8b) & Scoring AHP/TOPSIS.
Génère et extrait de réels profils de décideurs B2B selon la localisation et les mots-clés.

REAL-ONLY CONTRACT :
- Aucune fabrication de contact, d'email, de téléphone, de LinkedIn URL ou de website.
- Si une prospection ne renvoie pas de données réelles (sources vides, échecs réseau),
  le service retourne [] et l'API renvoie une warning explicite.
- Score : un prospect sans données réelles suffisantes pour le scoring est REJETÉ,
  pas noté 75/100 par défaut.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, List

from app.prospection.osmos.ahp_topsis import build_scoring_inputs, rank_prospects, topsis_score_to_100
from app.prospection.osmos.llm_client import call_llm, clean_json_block


from app.prospection.live_scraper import MultiSourceLiveScraper


# --- REAL-ONLY validation ----------------------------------------------------

# Au moins un de ces champs doit avoir une valeur RÉELLE pour qu'un prospect
# soit persisté. Sans cela, c'est une coquille vide générée par une source qui
# n'a renvoyé qu'un nom d'entreprise.
_REQUIRED_REAL_CONTACT_FIELDS = ("email", "phone", "website")

# Domaines à rejeter même s'ils matchent les mots-clés. Quand une source
# Open-Web (DuckDuckGo/Bing) renvoie une page qui parle du sujet mais qui n'est
# PAS une entreprise cible (job board, agrégateur d'offres, moteur de recherche,
# encyclopédie, réseau social), on l'écarte. Sans ce filtre, la base se remplit
# de prospects=None sur des URLs indeed.com / michaelpage.fr / etc.
_BLOCKED_DOMAINS = (
    # Job boards / agrégateurs d'offres
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
    "cari.ma", "emploi.cari.ma", "emploi.ma",
    # Moteurs de recherche / portails génériques
    "google.com/search", "google.fr/search",
    "bing.com/search",
    # Encyclopédies / listes génériques non-cibles
    "wikipedia.org", "wikimedia.org", "britannica.com", "britannica.fr",
    "yelp.com", "yelp.fr", "tripadvisor.com",
)

# Sources autorisées pour phone / email — si la valeur n'est pas 'verified' ou
# si la source n'est pas listée, on rejette.
_REAL_EMAIL_SOURCES = {"website_crawl", "osm", "sirene", "opencorporates"}
_REAL_PHONE_SOURCES = {"website_crawl", "osm", "sirene", "opencorporates"}
_REAL_LINKEDIN_SOURCES = {"website_crawl"}

_EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_PHONE_REGEX = re.compile(r"^(\+|00)?[0-9\s\-\.\(\)]{6,}$")
_LINKEDIN_REGEX = re.compile(r"^https?://(?:www\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9_\-/%.]+$")


def _is_real_prospect(p: Dict[str, Any]) -> bool:
    """
    Vérifie qu'un prospect porte au moins une donnée de contact RÉELLE.
    Renvoie False si le prospect est une coquille vide (juste un nom d'entreprise
    sans aucun moyen de le contacter).
    """
    has_email = bool(p.get("email")) and _EMAIL_REGEX.match(p["email"])
    has_phone = bool(p.get("phone")) and _PHONE_REGEX.match(str(p["phone"]).strip())
    has_website = bool(p.get("website")) and str(p["website"]).startswith("http")

    if not (has_email or has_phone or has_website):
        return False

    # Si on prétend avoir un email, il doit avoir une source réelle.
    if has_email and p.get("email_source") not in _REAL_EMAIL_SOURCES:
        return False
    # Idem pour téléphone.
    if has_phone and p.get("phone_source") not in _REAL_PHONE_SOURCES:
        return False
    # Idem pour linkedin.
    if p.get("linkedin_url") and (
        not _LINKEDIN_REGEX.match(p["linkedin_url"])
        or p.get("linkedin_source") not in _REAL_LINKEDIN_SOURCES
    ):
        return False
    # Le company doit être non-vide (sinon, ce n'est même pas un prospect).
    if not p.get("company"):
        return False
    return True


def _is_relevant_to_query(p: Dict[str, Any], query_keywords: List[str]) -> bool:
    """
    Filtre de pertinence : un prospect venant d'une API floue (OpenCorporates)
    doit avoir AU MOINS UN mot-clé de la requête présent dans son nom, industrie
    ou notes. Sans cela, OpenCorporates renvoie du bruit (fuzzy match) et la base
    se remplit de prospects sans rapport.

    Filtre supplémentaire : on rejette aussi les domaines "non-cibles"
    (job boards, agrégateurs, moteurs de recherche, encyclopédies). Ces pages
    matchent les mots-clés mais ne sont PAS des entreprises prospectables.
    """
    website = (p.get("website") or "").lower()
    notes = (p.get("notes") or "").lower()
    snippet = (p.get("snippet") or "").lower()
    haystack_url = f"{website} {notes} {snippet}"

    for blocked in _BLOCKED_DOMAINS:
        if blocked in haystack_url:
            return False

    if not query_keywords:
        return True  # pas de mots-clés => on garde
    haystack = " ".join([
        str(p.get("company") or ""),
        str(p.get("industry") or ""),
        str(p.get("notes") or ""),
    ]).lower()
    return any(kw.lower().strip() in haystack for kw in query_keywords if kw.strip())


def _has_enough_data_for_scoring(p: Dict[str, Any]) -> bool:
    """
    Pour scorer, on a besoin d'au moins un signal métier réel :
    - industrie fournie par la source
    - localisation vérifiée
    - taille d'entreprise (Sirene, Overpass)
    - website ou stack technique crawlée
    Sans aucun de ces signaux, le score est vide de sens : on rejette.
    """
    industry = (p.get("industry") or "").strip()
    location = (p.get("location") or "").strip()
    company_size = (p.get("company_size") or "").strip()
    has_real_website = bool(p.get("website")) and str(p["website"]).startswith("http")
    has_real_tech = bool(p.get("technologies")) and p["technologies"] != "HTML5/Standard"
    return bool(industry or location or company_size or has_real_website or has_real_tech)


class ProspectScraper:
    """
    Scraper B2B Multi-Sources Réel :
    - Web Scraping en direct (Overpass / Sirene / OpenCorporates / Bing / DuckDuckGo)
    - Extraction d'emails, téléphones, détection de la Stack Technique sur les sites réels
    - Qualification et Scoring AHP/TOPSIS
    """

    def __init__(self):
        self.live_scraper = MultiSourceLiveScraper()

    async def search(self, query: dict) -> List[Dict[str, Any]]:
        """
        Orchestre le scraping multi-sources en temps réel et le scoring TOPSIS.
        Retourne UNIQUEMENT des prospects avec données réelles (voir _is_real_prospect).
        """
        keywords = query.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]

        location = query.get("location", "Casablanca")
        max_results = min(int(query.get("max_results", 6)), 12)
        kw_str = ", ".join(keywords) if keywords else "Directeur Commercial"

        # 1. Scraping multi-sources réel
        try:
            raw_prospects = await self.live_scraper.search_live(query)
        except Exception as e:
            print(f"[Scraper Live] Erreur live scraper ({e}), 0 résultat — aucune fabrication.")
            return []

        if not raw_prospects:
            return []

        # 2. Filtre REAL-ONLY : on retire les coquilles vides avant tout scoring.
        real_prospects = [p for p in raw_prospects if _is_real_prospect(p)]
        # Filtre de pertinence : OpenCorporates fait du fuzzy match et renvoie du bruit
        # quand les keywords sont absents du nom/industrie — on écarte.
        real_prospects = [p for p in real_prospects if _is_relevant_to_query(p, keywords)]
        if not real_prospects:
            return []

        # 3. Construire les 5 critères AHP/TOPSIS pour chaque prospect RÉEL
        for p in real_prospects:
            scoring_inputs = build_scoring_inputs(p)
            p.update(scoring_inputs)

        # 4. Calculer le score AHP/TOPSIS 5x5 sur les prospects réels uniquement
        ranked, _ = rank_prospects(real_prospects)

        # 5. Filtrer à nouveau : un prospect sans assez de données pour scorer
        # n'a pas le droit d'avoir un score — il est écarté.
        scored_prospects = [p for p in ranked if _has_enough_data_for_scoring(p)]

        final_prospects = []
        for p in scored_prospects:
            # Score issu du calcul TOPSIS réel — pas de default 0.75.
            topsis_raw = p.get("topsis_score")
            if topsis_raw is None:
                continue
            p_score = topsis_score_to_100(float(topsis_raw))
            p["score"] = p_score
            tech_info = f" | Tech: {p['technologies']}" if p.get("technologies") else ""
            p["notes"] = (
                f"Scraping Live Web ({location}){tech_info} — TOPSIS Rank #{p.get('topsis_rank', 1)}"
            )
            final_prospects.append(p)

        return self._deduplicate(final_prospects)


    def _deduplicate(self, prospects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for p in prospects:
            key = p.get("email") or p.get("website") or f"{p.get('first_name')}_{p.get('company')}"
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique
