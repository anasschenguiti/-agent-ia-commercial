"""
Module 2 : Website Analyzer — Scrape et extrait les signaux digitaux factuels du prospect.
"""
import re
import urllib.parse
from typing import Dict, Any
import httpx
from app.analysis.signal_extractor import DigitalSignals

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


class WebsiteAnalyzer:
    """Analyse les performances et la maturité digitale d'un site d'entreprise."""

    async def analyze(self, url: str) -> DigitalSignals:
        if not url or not url.startswith("http"):
            return DigitalSignals(
                website_url=url or "N/A",
                is_responsive=False,
                ssl_enabled=False,
                page_load_speed_score=3.0,
                detected_technologies=[],
                notes="Site web indisponible ou non renseigné."
            )

        headers = {"User-Agent": "SalesAIAgent/1.0 (contact@iksatech.com)"}
        ssl_enabled = url.startswith("https://")
        
        async with httpx.AsyncClient(headers=headers, timeout=8.0, follow_redirects=True) as client:
            try:
                res = await client.get(url)
                if res.status_code == 200:
                    html = res.text
                    
                    # 1. Détection Stack Tech
                    techs = []
                    for tech_name, patterns in TECH_SIGNATURES.items():
                        if any(re.search(pat, html, re.IGNORECASE) for pat in patterns):
                            techs.append(tech_name)

                    # 2. Liens réseaux sociaux
                    social_patterns = [r"linkedin\.com", r"facebook\.com", r"twitter\.com", r"instagram\.com"]
                    socials = []
                    for pat in social_patterns:
                        matches = re.findall(r"https?://(?:www\.)?" + pat + r"/[a-zA-Z0-9_-]+", html)
                        if matches:
                            socials.extend(matches[:1])

                    # 3. Signaux formulaires & analytics
                    has_form = bool(re.search(r"<form", html, re.IGNORECASE))
                    has_analytics = "Google Analytics" in techs or "gtag" in html or "analytics" in html
                    is_responsive = "viewport" in html.lower() or "responsive" in html.lower() or "bootstrap" in html.lower() or "tailwind" in html.lower()
                    has_modern_cms = any(t in techs for t in ["WordPress", "Next.js", "Shopify", "React"])

                    speed_score = 9.0 if (has_analytics and is_responsive) else (7.0 if is_responsive else 4.0)

                    return DigitalSignals(
                        website_url=url,
                        is_responsive=is_responsive,
                        ssl_enabled=ssl_enabled,
                        page_load_speed_score=speed_score,
                        detected_technologies=techs,
                        social_links=socials,
                        has_contact_form=has_form,
                        has_analytics=has_analytics,
                        has_modern_cms=has_modern_cms,
                        notes=f"Audit effectué avec succès ({len(techs)} technologies détectées)."
                    )
            except Exception as e:
                print(f"[WebsiteAnalyzer] Erreur audit {url} : {e}")

        return DigitalSignals(
            website_url=url,
            is_responsive=False,
            ssl_enabled=ssl_enabled,
            page_load_speed_score=4.0,
            detected_technologies=[],
            notes="Erreur d'accès lors de l'audit HTTP du site web."
        )
