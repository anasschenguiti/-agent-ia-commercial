"""
Module 2 : Diagnostic Generator — Génère un diagnostic factuel basé strictement sur DigitalSignals.
Règle guardrail : Aucune invention de faits non présents dans les signaux en entrée.
"""
from app.analysis.signal_extractor import DigitalSignals
from app.prospection.osmos.llm_client import call_llm


class DiagnosticGenerator:
    """Génère un diagnostic commercial factuel de 2 à 4 phrases."""

    def generate_diagnostic(self, company_name: str, signals: DigitalSignals) -> str:
        # Diagnostic factuel déterministe et sécurisé
        facts = []
        if not signals.ssl_enabled:
            facts.append("Le site web ne dispose pas d'un certificat SSL sécurisé (HTTPS).")
        if not signals.is_responsive:
            facts.append("L'interface n'est pas optimisée pour les appareils mobiles (absence de viewport responsive).")
        if not signals.has_analytics:
            facts.append("Aucun outil de suivi d'audience ou d'analytics (Google Analytics, HubSpot) n'est détecté.")
        if not signals.has_contact_form:
            facts.append("Aucun formulaire de contact ou d'engagement dynamique n'est visible sur la page d'accueil.")
        if signals.detected_technologies:
            facts.append(f"Stack technique identifiée : {', '.join(signals.detected_technologies)}.")
        else:
            facts.append("Le site s'appuie sur une infrastructure Web classique sans CMS ou framework moderne détecté.")

        facts_str = " ".join(facts)

        prompt = f"""Tu es un consultant expert en transformation digitale chez IKSATECH.
Génère un diagnostic commercial factuel et concis (2 à 4 phrases maximum) pour l'entreprise {company_name}.
Base-toi STRICTEMENT et UNIQUEMENT sur les faits suivants (NE RAJOUTE AUCUN FAIT OU CHIFFRE INVENTÉ) :
{facts_str}

Formule une opportunité de transformation digitale/IA adaptée à ces constatations factuelles.
"""
        try:
            llm_res = call_llm(prompt, temperature=0.1, timeout=5.0)
            if llm_res and len(llm_res.strip()) > 30:
                return llm_res.strip()
        except Exception:
            pass

        # Diagnostic de fallback déterministe sans hallucination
        missing_opt = []
        if not signals.has_analytics:
            missing_opt.append("le suivi analytics")
        if not signals.has_modern_cms:
            missing_opt.append("l'automatisation des contenus")
        
        opt_str = " et ".join(missing_opt) if missing_opt else "l'automatisation par l'IA"
        return (
            f"L'analyse du site web de {company_name} montre une présence digitale fonctionnelle avec "
            f"une stack {', '.join(signals.detected_technologies) if signals.detected_technologies else 'standard'}. "
            f"Une opportunité d'optimisation existe sur {opt_str} pour renforcer la conversion de leurs prospects."
        )
