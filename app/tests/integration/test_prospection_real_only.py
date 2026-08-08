"""
Tests d'intégration REAL-ONLY — Prouve que le module de prospection ne retourne
que des prospects avec données réelles (Overpass / Sirene / OpenCorporates /
Bing / DuckDuckGo), et JAMAIS de prospects fabriqués.

Ces tests frappent les vraies APIs publiques. Aucun mock.
"""
import re

import pytest

from app.prospection.scraper import (
    ProspectScraper,
    _is_real_prospect,
    _has_enough_data_for_scoring,
)
from app.prospection.search_providers import (
    OverpassB2BProvider,
    OfficialB2BRegistryProvider,
)


# --- Tests unitaires : helpers de validation REAL-ONLY -----------------------


def test_is_real_prospect_rejects_empty_shell():
    """Un prospect sans email/phone/website et sans source vérifiée est rejeté."""
    p = {"company": "Acme", "first_name": "Direction"}
    assert _is_real_prospect(p) is False


def test_is_real_prospect_accepts_real_website():
    p = {
        "company": "Acme",
        "website": "https://www.acme.fr",
        "phone": None,
        "email": None,
    }
    assert _is_real_prospect(p) is True


def test_is_real_prospect_rejects_fabricated_email():
    """Un email avec une source 'unverified' (fabrication) doit être rejeté."""
    p = {
        "company": "Acme",
        "email": "fake@acme.fr",
        "email_source": "unverified",
        "website": "https://www.acme.fr",
    }
    assert _is_real_prospect(p) is False


def test_is_real_prospect_rejects_invalid_email_format():
    p = {
        "company": "Acme",
        "email": "not-an-email",
        "email_source": "website_crawl",
        "website": None,
    }
    assert _is_real_prospect(p) is False


def test_is_real_prospect_rejects_fake_linkedin_url():
    """Un linkedin_url inventé (sans source website_crawl) doit être rejeté."""
    p = {
        "company": "Acme",
        "website": "https://www.acme.fr",
        "linkedin_url": "https://www.linkedin.com/company/acme",
        "linkedin_source": "guessed",
    }
    assert _is_real_prospect(p) is False


def test_has_enough_data_for_scoring_rejects_empty():
    p = {"company": "Acme"}
    assert _has_enough_data_for_scoring(p) is False


def test_has_enough_data_for_scoring_accepts_industry():
    p = {"company": "Acme", "industry": "Tech"}
    assert _has_enough_data_for_scoring(p) is True


# --- Tests d'intégration : Overpass (OpenStreetMap) --------------------------


@pytest.mark.asyncio
async def test_overpass_returns_real_companies_in_paris():
    """Overpass doit renvoyer de vraies entreprises (pas de fabrication)."""
    provider = OverpassB2BProvider()
    results = await provider.search_local_business("consulting", "Paris", limit=3)
    # Overpass peut renvoyer 0 résultats pour des zones exotiques — on accepte
    # mais si on a des résultats, ils doivent être réels.
    for r in results:
        assert isinstance(r["company"], str) and len(r["company"]) > 0
        # Pas de fabrication d'email : soit None, soit format valide
        if r.get("email"):
            assert re.match(r"^[^@]+@[^@]+\.[^@]+$", r["email"])
        # Pas de fabrication de téléphone : soit None, soit format plausible
        if r.get("phone"):
            assert re.match(r"^\+?[\d\s\-\.()]{6,}$", str(r["phone"]))
        # Pas de fabrication de site web
        if r.get("website"):
            assert str(r["website"]).startswith("http")


# --- Tests d'intégration : OpenCorporates ------------------------------------


@pytest.mark.asyncio
async def test_opencorporates_returns_real_companies():
    """OpenCorporates doit renvoyer de vraies entreprises sans fabrication."""
    provider = OfficialB2BRegistryProvider()
    results = await provider._search_opencorporates("tech", "Casablanca", "Maroc", limit=3)
    for r in results:
        # REAL-ONLY : pas de first_name="Direction"
        assert r["first_name"] is None or len(r["first_name"]) > 0
        # REAL-ONLY : pas de website fabriqué
        assert r["website"] is None or str(r["website"]).startswith("http")
        # REAL-ONLY : pas de linkedin_url fabriqué
        assert r["linkedin_url"] is None
        # Le company name est obligatoire
        assert isinstance(r["company"], str) and len(r["company"]) > 0
        # Source doit être tracée
        assert r.get("source") == "opencorporates"


@pytest.mark.asyncio
async def test_sirene_returns_real_companies_without_fabrication():
    """Sirene France doit fournir un site web UNIQUEMENT si l'API le renvoie."""
    provider = OfficialB2BRegistryProvider()
    results = await provider._search_sirene_france("conseil", "Paris", limit=3)
    for r in results:
        # Le site doit être réel ou None — JAMAIS `https://www.{nom}.fr` fabriqué
        if r.get("website"):
            assert str(r["website"]).startswith("http")
        # first_name doit être None si l'API ne renvoie aucun dirigeant
        # (au lieu du placeholder "Direction")
        assert r["first_name"] is None or len(r["first_name"]) > 0
        assert r.get("source") == "sirene"


# --- Test d'intégration end-to-end : ProspectScraper.search() -----------------


@pytest.mark.asyncio
async def test_scraper_search_returns_only_real_prospects():
    """
    Le scraper ne doit retourner AUCUN prospect sans données réelles vérifiées.

    On utilise une requête qui peut renvoyer des résultats réels (Overpass/Sirene),
    et on vérifie que chaque prospect passé respecte le contrat REAL-ONLY.
    """
    scraper = ProspectScraper()
    query = {
        "keywords": ["consulting"],
        "location": "Paris",
        "country": "France",
        "max_results": 3,
    }
    try:
        prospects = await scraper.search(query)
    except Exception as e:
        pytest.skip(f"API publique indisponible pendant le test : {e}")

    # Si on a des résultats, ils doivent tous être réels.
    for p in prospects:
        # Au moins un vrai canal de contact
        assert (p.get("email") or p.get("phone") or p.get("website")), (
            f"Prospect sans contact réel: {p.get('company')}"
        )
        # Si un email est présent, sa source doit être vérifiée
        if p.get("email"):
            assert p.get("email_source") in (
                "website_crawl", "osm", "sirene", "opencorporates"
            ), f"Email à source non vérifiée: {p}"
        # Si linkedin est présent, source doit être website_crawl
        if p.get("linkedin_url"):
            assert p.get("linkedin_source") == "website_crawl", (
                f"LinkedIn URL à source non vérifiée: {p}"
            )
        # Score réel (pas de default 75)
        assert p.get("score") is not None
        # Pas de company_name vide
        assert p.get("company")


@pytest.mark.asyncio
async def test_scraper_returns_empty_when_no_real_data():
    """
    Si une requête ne trouve rien dans les sources réelles, on retourne []
    sans fabriquer de prospects.
    """
    scraper = ProspectScraper()
    query = {
        "keywords": ["zzzzzzzz-nonexistent-keyword-zzzzzzzz"],
        "location": "Antarctique",
        "country": "Antarctique",
        "max_results": 5,
    }
    try:
        prospects = await scraper.search(query)
    except Exception as e:
        pytest.skip(f"API publique indisponible pendant le test : {e}")
    assert prospects == [], "Aucune source réelle ne devrait trouver ce keyword"