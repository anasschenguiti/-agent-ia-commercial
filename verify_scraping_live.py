"""Audit live manuel du module prospection contre de vraies APIs publiques.
ASCII-only pour compatibilite console Windows cp1252.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.prospection.live_scraper import MultiSourceLiveScraper
from app.prospection.scraper import ProspectScraper
from app.prospection.search_providers import (
    OverpassB2BProvider,
    OfficialB2BRegistryProvider,
    BingSearchProvider,
)


async def test_provider(name, coro):
    print()
    print("=" * 70)
    print(" TEST: " + name)
    print("=" * 70)
    try:
        result = await coro
        print("  -> %d resultat(s)" % len(result))
        for i, r in enumerate(result[:3], 1):
            comp = (r.get("company", "N/A") or "")[:55]
            print("    [%d] %s" % (i, comp))
            print("        email=%r phone=%r" % (r.get("email"), r.get("phone")))
            website = r.get("website", "")
            if website:
                print("        website=%s..." % str(website)[:50])
            else:
                print("        website=None")
            print("        source=%r linkedin=%s" % (r.get("source"), "OUI" if r.get("linkedin_url") else "non"))
        return result
    except Exception as e:
        print("  ERREUR: %s: %s" % (type(e).__name__, e))
        return []


async def main():
    print("AUDIT LIVE - Module Prospection")
    print("Aucune fabrication : si les APIs ne renvoient rien, on le dit.")
    print()

    # 1. Overpass (OpenStreetMap) - 100% gratuit, donnees reelles
    overpass = OverpassB2BProvider()
    await test_provider(
        "Overpass - Casablanca / web (OpenStreetMap)",
        overpass.search_local_business("web", "Casablanca", limit=5),
    )

    await test_provider(
        "Overpass - Casablanca / consulting (OpenStreetMap)",
        overpass.search_local_business("consulting", "Casablanca", limit=5),
    )

    await test_provider(
        "Overpass - Paris / agency (OpenStreetMap)",
        overpass.search_local_business("agency", "Paris", limit=5),
    )

    # 2. Registre B2B officiel
    registry = OfficialB2BRegistryProvider()
    await test_provider(
        "Sirene FR - Paris / conseil",
        registry._search_sirene_france("conseil", "Paris", limit=3),
    )

    await test_provider(
        "OpenCorporates - Casablanca / tech",
        registry._search_opencorporates("tech", "Casablanca", "Maroc", limit=3),
    )

    # 3. Moteur de recherche : fallback DuckDuckGo HTML
    bing = BingSearchProvider()
    await test_provider(
        "BingSearchProvider (fallback DuckDuckGo HTML)",
        bing.search_web("Directeur Commercial Casablanca Maroc", limit=4),
    )

    # 4. Orchestration multi-sources end-to-end
    print()
    print("=" * 70)
    print(" TEST: MultiSourceLiveScraper - orchestration complete (Casablanca)")
    print("=" * 70)
    live = MultiSourceLiveScraper()
    query_casa = {
        "keywords": ["directeur", "commercial"],
        "location": "Casablanca",
        "country": "Maroc",
        "max_results": 5,
    }
    raw = await live.search_live(query_casa)
    print("  -> %d leads enrichis" % len(raw))
    for i, p in enumerate(raw[:5], 1):
        comp = (p.get("company", "?") or "?")[:50]
        contact_parts = []
        if p.get("email"):
            contact_parts.append("email=%s" % p["email"])
        if p.get("phone"):
            contact_parts.append("phone=%s" % p["phone"])
        if p.get("website"):
            contact_parts.append("website=%s..." % str(p["website"])[:35])
        contact_parts.append("linkedin=%s" % ("OUI" if p.get("linkedin_url") else "non"))
        if p.get("technologies"):
            contact_parts.append("tech=%s" % p["technologies"][:25])

        print("    [%d] %s" % (i, comp))
        print("        %s" % " | ".join(contact_parts))
        dc = p.get("data_confidence", {})
        print("        data_confidence: email=%s phone=%s size=%s" % (
            dc.get("email"), dc.get("phone"), dc.get("company_size")
        ))
        print("        sources: email_source=%r phone_source=%r" % (
            p.get("email_source"), p.get("phone_source")
        ))

    # 5. REAL-ONLY via ProspectScraper
    print()
    print("=" * 70)
    print(" TEST: ProspectScraper.search() - Paris (REAL-ONLY + AHP/TOPSIS)")
    print("=" * 70)
    scraper = ProspectScraper()
    ranked = await scraper.search({
        "keywords": ["consulting"],
        "location": "Paris",
        "country": "France",
        "max_results": 3,
    })
    print("  -> %d prospects scores (REAL-ONLY, AHP/TOPSIS)" % len(ranked))
    for i, p in enumerate(ranked[:3], 1):
        comp = (p.get("company", "?") or "?")[:45]
        score = p.get("score", 0)
        rank = p.get("topsis_rank", "?")
        website = str(p.get("website", ""))[:50] if p.get("website") else "None"
        print("    [%d] %s -> %.1f/100 (rank #%s)" % (i, comp, score, rank))
        print("        website=%s" % website)
        ind = (p.get("industry", "?") or "?")[:60]
        print("        industry=%s" % ind)
        sb = p.get("score_breakdown", {})
        if sb:
            print("        score_breakdown: %s" % sb)

    # 6. Test anti-fabrication : requete impossible
    print()
    print("=" * 70)
    print(" TEST: Anti-fabrication - requete impossible (doit retourner 0)")
    print("=" * 70)
    impossible = await scraper.search({
        "keywords": ["zzzz-nonexistent-keyword-zzzz"],
        "location": "Antarctique",
        "country": "Antarctique",
        "max_results": 5,
    })
    if len(impossible) == 0:
        print("  -> 0 prospect(s) - CONFORME REAL-ONLY (aucune fabrication)")
    else:
        print("  -> %d prospect(s) - PROBLEME : du contenu invente ?" % len(impossible))


if __name__ == "__main__":
    asyncio.run(main())
