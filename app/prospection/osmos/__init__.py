"""
Module OSMOS — Intégration des moteurs de prospection intelligente.
Scoring AHP/TOPSIS, Génération de Persona et Plan d'action IA.
"""
from .llm_client import call_llm
from .ahp_topsis import rank_prospects, calculate_ahp_weights
from .persona_engine import generate_persona, PersonaGenerationError
from .plan_engine import generate_action_plan, generate_content, PlanGenerationError, ContentGenerationError

__all__ = [
    "call_llm",
    "rank_prospects",
    "calculate_ahp_weights",
    "generate_persona",
    "PersonaGenerationError",
    "generate_action_plan",
    "generate_content",
    "PlanGenerationError",
    "ContentGenerationError",
]
