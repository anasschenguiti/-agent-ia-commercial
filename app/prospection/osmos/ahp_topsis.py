"""
Moteur de scoring AHP/TOPSIS — Aligné sur les 5 critères du Cahier des Charges :
1. activite_compatible
2. budget_potentiel
3. presence_digitale
4. croissance
5. localisation
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
import numpy as np


def _safe_float(val: Any, default: float = 5.0) -> float:
    """Convertit une valeur quelconque en float, avec valeur par défaut."""
    try:
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip().split("/")[0].strip()
        match = re.search(r"[-+]?\d*\.?\d+", val_str.replace(",", "."))
        return float(match.group()) if match else default
    except Exception:
        return default


CRITERIA_NAMES = [
    "activite_compatible",
    "budget_potentiel",
    "presence_digitale",
    "croissance",
    "localisation",
]


def build_scoring_inputs(prospect: dict) -> dict:
    """
    Calcule les 5 critères réels du cahier des charges à partir des champs du prospect.
    Documente explicitement la source de chaque valeur.
    """
    inputs = {}
    sources = {}

    # 1. Activité compatible
    industry = (prospect.get("industry") or "").lower()
    if any(k in industry for k in ["tech", "digital", "service", "siren", "saas", "conseil", "banque"]):
        inputs["activite_compatible"] = 9.0
        sources["activite_compatible"] = "industry_target_match"
    elif industry:
        inputs["activite_compatible"] = 7.0
        sources["activite_compatible"] = "industry_general"
    else:
        inputs["activite_compatible"] = 5.0
        sources["activite_compatible"] = "default_unspecified"

    # 2. Budget potentiel
    rev = prospect.get("annual_revenue")
    size = prospect.get("company_size")
    if rev or (size and ("51" in size or "201" in size or "500" in size)):
        inputs["budget_potentiel"] = 8.5
        sources["budget_potentiel"] = "revenue_or_large_size"
    elif size:
        inputs["budget_potentiel"] = 6.5
        sources["budget_potentiel"] = "size_available"
    else:
        inputs["budget_potentiel"] = 5.0
        sources["budget_potentiel"] = "unverified_budget"

    # 3. Présence digitale
    web = prospect.get("website")
    techs = prospect.get("technologies")
    if web and techs and techs != "Web Standard":
        inputs["presence_digitale"] = 9.0
        sources["presence_digitale"] = "website_and_tech_stack"
    elif web:
        inputs["presence_digitale"] = 7.0
        sources["presence_digitale"] = "website_only"
    else:
        inputs["presence_digitale"] = 3.0
        sources["presence_digitale"] = "no_website"

    # 4. Croissance
    li = prospect.get("linkedin_url")
    if li:
        inputs["croissance"] = 8.0
        sources["croissance"] = "linkedin_active"
    else:
        inputs["croissance"] = 5.0
        sources["croissance"] = "no_linkedin"

    # 5. Localisation
    loc = (prospect.get("location") or "").lower()
    country = (prospect.get("country") or "").lower()
    if loc or country:
        inputs["localisation"] = 8.5
        sources["localisation"] = "location_verified"
    else:
        inputs["localisation"] = 5.0
        sources["localisation"] = "location_unspecified"

    # Garder rétrocompatibilité avec sector_fit, size_score, accessibility, recent_activity
    inputs["sector_fit"] = inputs["activite_compatible"]
    inputs["size_score"] = inputs["budget_potentiel"]
    inputs["accessibility"] = inputs["presence_digitale"]
    inputs["recent_activity"] = inputs["croissance"]
    inputs["scoring_sources"] = sources

    return inputs


def calculate_ahp_weights(matrix_config: Optional[List[List[float]]] = None) -> Dict[str, Any]:
    """
    Calcule les poids AHP pour les 5 critères du Cahier des Charges.
    Random Index RI = 1.12 pour n=5.
    """
    if matrix_config and len(matrix_config) == 5:
        matrix = np.array(matrix_config)
    else:
        # Matrice 5x5 de comparaison par paires
        matrix = np.array([
            [1.0,  2.0,  3.0,  4.0,  5.0],  # activite_compatible
            [1/2,  1.0,  2.0,  3.0,  4.0],  # budget_potentiel
            [1/3,  1/2,  1.0,  2.0,  3.0],  # presence_digitale
            [1/4,  1/3,  1/2,  1.0,  2.0],  # croissance
            [1/5,  1/4,  1/3,  1/2,  1.0],  # localisation
        ])

    n = matrix.shape[0]
    col_sums = matrix.sum(axis=0)
    normalized = matrix / col_sums
    weights = normalized.mean(axis=1)

    aw = np.dot(matrix, weights)
    lambda_max = float(np.mean(aw / weights))
    ci = (lambda_max - n) / (n - 1)
    ri = 1.12  # Random Index pour n=5
    cr = ci / ri

    return {
        "weights": weights.tolist(),
        "CR": float(cr),
        "consistent": bool(cr < 0.1),
        "criteria": CRITERIA_NAMES,
    }


def rank_prospects(prospects: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Applique TOPSIS avec la matrice AHP 5x5 sur les 5 critères du cahier des charges.
    Ajoute score_breakdown (dict critère -> contribution) en sortie.
    """
    if not prospects:
        return [], calculate_ahp_weights()

    # S'assurer que chaque prospect a ses 5 critères calculés via build_scoring_inputs
    for p in prospects:
        if "activite_compatible" not in p:
            p.update(build_scoring_inputs(p))

    ahp_result = calculate_ahp_weights()
    weights = np.array(ahp_result["weights"])

    decision_matrix = np.array([
        [
            _safe_float(p.get("activite_compatible", 5)),
            _safe_float(p.get("budget_potentiel", 5)),
            _safe_float(p.get("presence_digitale", 5)),
            _safe_float(p.get("croissance", 5)),
            _safe_float(p.get("localisation", 5)),
        ]
        for p in prospects
    ])

    if len(decision_matrix) == 1:
        single = prospects[0]
        single.update({
            "topsis_score": 1.0,
            "topsis_rank": 1,
            "priority_label": "Top",
            "score_breakdown": {
                name: round(float(weights[idx] * _safe_float(single.get(name, 5)) * 10), 1)
                for idx, name in enumerate(CRITERIA_NAMES)
            }
        })
        return prospects, ahp_result

    # 1. Normalisation vectorielle
    sq_sum = np.sqrt((decision_matrix ** 2).sum(axis=0))
    sq_sum[sq_sum == 0] = 1.0
    normalized = decision_matrix / sq_sum

    # 2. Pondération
    weighted = normalized * weights

    # 3. Solutions idéales
    ideal_best = weighted.max(axis=0)
    ideal_worst = weighted.min(axis=0)

    # 4. Distances euclidiennes
    dist_best = np.sqrt(((weighted - ideal_best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((weighted - ideal_worst) ** 2).sum(axis=1))

    # 5. Closeness Coefficient
    denom = dist_best + dist_worst
    denom[denom == 0] = 1e-10
    cc = dist_worst / denom

    for i, p in enumerate(prospects):
        p["topsis_score"] = float(cc[i])
        breakdown = {}
        for idx, name in enumerate(CRITERIA_NAMES):
            breakdown[name] = round(float(weights[idx] * _safe_float(p.get(name, 5)) * 10), 1)
        p["score_breakdown"] = breakdown

    prospects.sort(key=lambda x: x["topsis_score"], reverse=True)
    for i, p in enumerate(prospects):
        p["topsis_rank"] = i + 1
        score = p["topsis_score"]
        if score > 0.75:
            p["priority_label"] = "Top"
        elif score > 0.55:
            p["priority_label"] = "High"
        elif score > 0.35:
            p["priority_label"] = "Medium"
        else:
            p["priority_label"] = "Low"

    return prospects, ahp_result


def topsis_score_to_100(topsis_score: float) -> float:
    """Convertit un score TOPSIS (0–1) en score métier (0–100)."""
    return round(topsis_score * 100, 1)
