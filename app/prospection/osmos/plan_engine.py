"""
Moteur de génération de Plan d'action et Contenus LinkedIn.
Adapté depuis OSMOS_lead_generation — plan 6 étapes sur 3 semaines + post/commentaire/DM.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict

from .llm_client import call_llm, clean_json_block


class PlanGenerationError(Exception):
    """Levée quand le LLM échoue à générer un plan d'action valide."""
    pass


class ContentGenerationError(Exception):
    """Levée quand le LLM échoue à générer des contenus LinkedIn valides."""
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_and_parse(prompt: str, exc_cls: type, timeout: float = 90.0) -> Dict[str, Any]:
    """Appelle le LLM et parse le JSON objet retourné."""
    try:
        raw = call_llm(prompt, temperature=0.7, timeout=timeout)
    except RuntimeError as e:
        raise exc_cls(f"LLM a échoué : {e}")

    cleaned = clean_json_block(raw, bracket="{")
    if not cleaned:
        raise exc_cls("Aucun JSON valide trouvé dans la réponse du LLM.")
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise exc_cls("Le JSON retourné n'est pas un dictionnaire.")
        return parsed
    except json.JSONDecodeError as e:
        raise exc_cls(f"JSON mal formé : {e}")


def _has_placeholder(text: str) -> str | None:
    """Retourne le placeholder trouvé, ou None si aucun."""
    pattern = re.compile(r'\[[a-zA-Z_ ]{2,30}\]|\{[a-zA-Z_ ]{2,30}\}|<[a-zA-Z_ ]{2,30}>')
    match = pattern.search(text)
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# Plan d'action 6 étapes
# ---------------------------------------------------------------------------

def generate_action_plan(
    persona_name: str,
    persona_role: str,
    persona_work_style: str,
    prospect_name: str,
    prospect_title: str,
    prospect_company: str,
    prospect_sector: str,
) -> Dict[str, Any]:
    """
    Génère un plan de nurturing LinkedIn en 6 étapes sur 3 semaines.

    Returns:
        Dict {"steps": [{"day": int, "action_type": str, "rationale": str}, ...]}

    Raises:
        PlanGenerationError: Si le LLM échoue après 2 tentatives.
    """
    base_prompt = f"""Tu es un expert en stratégie commerciale B2B. Crée un plan de nurturing en 6 étapes sur 3 semaines pour ton prospect cible.
Ton persona : {persona_name} ({persona_role}) — {persona_work_style}
Prospect cible : {prospect_name} ({prospect_title}) chez {prospect_company} dans le secteur {prospect_sector}

Tu DOIS retourner UNIQUEMENT un objet JSON strict avec EXACTEMENT une clé "steps", qui est un tableau de 6 objets.
Chaque objet doit avoir :
- "day": integer (ex: 1, 4, 7, 12, 16, 21)
- "action_type": string (DOIT être exactement l'un de : "like", "comment", "connect", "message", "post", "dm")
- "rationale": string (pourquoi cette étape maintenant)

Retourne UNIQUEMENT du JSON valide commençant par {{ et finissant par }}. Pas de markdown, pas de <think>.
"""

    def _attempt(prompt: str) -> Dict[str, Any]:
        return _call_and_parse(prompt, PlanGenerationError)

    try:
        return _attempt(base_prompt)
    except PlanGenerationError as e:
        retry_prompt = f"Tentative précédente échouée : {e}\n\n{base_prompt}\nCRITIQUE : JSON valide uniquement."
        try:
            return _attempt(retry_prompt)
        except PlanGenerationError as e2:
            raise PlanGenerationError(f"Échec après 2 tentatives : {e2}")


# ---------------------------------------------------------------------------
# Génération de contenus LinkedIn
# ---------------------------------------------------------------------------

def generate_content(
    persona_name: str,
    persona_role: str,
    company_name: str,
    value_proposition: str,
    prospect_name: str,
    prospect_title: str,
) -> Dict[str, Any]:
    """
    Génère 3 contenus LinkedIn personnalisés : post, commentaire court, DM direct.

    Returns:
        Dict {"post_text": str, "short_comment": str, "direct_message": str}

    Raises:
        ContentGenerationError: Si le LLM échoue ou insère des placeholders.
    """
    base_prompt = f"""Tu es {persona_name}, {persona_role} chez {company_name}.
Ta proposition de valeur : {value_proposition}.
Ton prospect cible est {prospect_name} ({prospect_title}).

Rédige 3 contenus LinkedIn au format JSON strict :
1. "post_text" : Un post LinkedIn complet partageant une insight sectorielle pertinente.
2. "short_comment" : Un commentaire court (1-2 phrases) perspicace à laisser sur un post récent du prospect.
3. "direct_message" : Un DM LinkedIn concis et non-commercial (<400 caractères) pour initier une conversation après acceptation de connexion. Utilise le vrai nom "{prospect_name}" directement.

CRITIQUE : Ces contenus doivent être prêts à envoyer, pas des templates. N'utilise JAMAIS de placeholders comme [nom], [prénom], [entreprise], {{name}}, <contact> ou similaires. Écris "{prospect_name}" et "{company_name}" littéralement.

Tu DOIS retourner UNIQUEMENT un objet JSON avec EXACTEMENT les clés : "post_text", "short_comment", "direct_message".
Retourne UNIQUEMENT du JSON valide. Pas de markdown, pas de <think>.
"""

    def _attempt(prompt: str) -> Dict[str, Any]:
        content = _call_and_parse(prompt, ContentGenerationError)
        # Vérifier l'absence de placeholders dans chaque champ
        for field in ("post_text", "short_comment", "direct_message"):
            placeholder = _has_placeholder(str(content.get(field, "")))
            if placeholder:
                raise ContentGenerationError(
                    f"Le champ '{field}' contient un placeholder : '{placeholder}'"
                )
        return content

    try:
        return _attempt(base_prompt)
    except ContentGenerationError as e:
        retry_prompt = (
            f"Tentative précédente échouée : {e}\n\n{base_prompt}\n"
            f"CRITIQUE : Écris '{prospect_name}' et '{company_name}' littéralement. "
            "Aucun placeholder d'aucune sorte."
        )
        try:
            return _attempt(retry_prompt)
        except ContentGenerationError as e2:
            raise ContentGenerationError(f"Échec de rédaction après 2 tentatives : {e2}")
