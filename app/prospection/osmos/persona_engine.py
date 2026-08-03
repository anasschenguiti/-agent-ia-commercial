"""
Moteur de génération de Persona commercial IA.
Adapté depuis OSMOS_lead_generation — utilise Ollama (qwen3:8b) ou OpenAI en fallback.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from .llm_client import call_llm, clean_json_block


class PersonaGenerationError(Exception):
    """Levée quand le LLM échoue à générer un persona valide."""
    pass


def _parse_persona_json(text: str) -> Dict[str, Any]:
    """Extrait et valide le JSON du persona depuis la réponse LLM."""
    cleaned = clean_json_block(text, bracket="{")
    if not cleaned:
        raise PersonaGenerationError(
            "Le modèle n'a pas retourné de JSON valide (aucune accolade trouvée)."
        )
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise PersonaGenerationError("Le JSON retourné n'est pas un dictionnaire.")
        return parsed
    except json.JSONDecodeError as e:
        raise PersonaGenerationError(f"JSON mal formé : {e}\nExtrait : {cleaned[:120]}...")


def generate_persona(
    company_name: str,
    company_sector: str,
    value_proposition: str,
    prospects_summary: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Génère un persona commercial virtuel B2B via le LLM.

    Args:
        company_name: Nom de l'entreprise qui prospecte.
        company_sector: Secteur d'activité ciblé.
        value_proposition: Proposition de valeur de l'entreprise.
        prospects_summary: Liste optionnelle de noms d'entreprises cibles.

    Returns:
        Dict avec : full_name, headline, role, seniority, age, bio,
                    work_style, key_skills, past_projects.

    Raises:
        PersonaGenerationError: Si le LLM échoue après 2 tentatives.
    """
    prospects_block = ""
    if prospects_summary:
        prospects_block = "Entreprises cibles :\n" + "\n".join(
            f"- {s}" for s in prospects_summary[:5]
        )

    base_prompt = f"""Tu es un expert en stratégie commerciale B2B. Crée un persona commercial virtuel crédible pour une campagne ciblant le secteur '{company_sector}' au MAROC.
EXIGENCE CRITIQUE : Le persona DOIT être de nationalité marocaine avec un prénom et nom marocains réalistes (ex: Youssef, Amine, Mehdi, Fatima, Yasmine...).
Ce persona travaille pour '{company_name}', dont la proposition de valeur est : "{value_proposition}".
{prospects_block}

Tu DOIS retourner UNIQUEMENT un objet JSON strict avec EXACTEMENT ces clés :
- "full_name": string (prénom et nom marocains réalistes)
- "headline": string (accroche LinkedIn percutante)
- "role": string (titre du poste)
- "seniority": string (ex: "Senior", "Directeur", "Lead")
- "age": integer
- "bio": string (résumé professionnel de 2-3 phrases)
- "work_style": string (approche commerciale et relationnelle)
- "key_skills": tableau de strings (3 à 5 compétences clés)
- "past_projects": tableau d'objets avec "title" (string) et "quantifiable_result" (string)

Retourne UNIQUEMENT le JSON, commençant par {{ et finissant par }}. Pas de markdown, pas de balises <think>.
"""

    def _attempt(prompt: str) -> Dict[str, Any]:
        try:
            raw = call_llm(prompt, temperature=0.7, timeout=90.0)
            return _parse_persona_json(raw)
        except RuntimeError as e:
            raise PersonaGenerationError(f"LLM injoignable : {e}")

    try:
        return _attempt(base_prompt)
    except PersonaGenerationError as e:
        # Seconde tentative avec prompt plus strict
        retry_prompt = (
            f"Tentative précédente échouée : {e}\n\n{base_prompt}\n\n"
            "CRITIQUE : Retourne UNIQUEMENT du JSON valide, rien d'autre."
        )
        try:
            return _attempt(retry_prompt)
        except PersonaGenerationError as e2:
            raise PersonaGenerationError(
                f"Échec de génération du persona après 2 tentatives. Dernière erreur : {e2}"
            )
