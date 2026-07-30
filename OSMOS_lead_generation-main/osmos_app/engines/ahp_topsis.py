import numpy as np
import re

def safe_float(val, default=5.0):
    try:
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip()
        # Remove "/10" or similar trailing fractions
        val_str = val_str.split('/')[0].strip()
        # Find first number in string (supporting commas as decimals)
        match = re.search(r'[-+]?\d*\.?\d+', val_str.replace(',', '.'))
        if match:
            return float(match.group())
        return default
    except Exception:
        return default

def calculate_ahp_weights():
    """
    Calcule les poids AHP pour les 4 critères : 
    1. Sector Fit (Fit sectoriel)
    2. Size Score (Taille)
    3. Accessibility (Accessibilité)
    4. Recent Activity (Activité récente)
    """
    # Matrice de comparaison par paires fixe pour la démo
    # Ordre : Sector Fit, Size, Accessibility, Activity
    matrix = np.array([
        [1.0, 3.0, 5.0, 7.0],
        [1/3, 1.0, 3.0, 5.0],
        [1/5, 1/3, 1.0, 3.0],
        [1/7, 1/5, 1/3, 1.0]
    ])
    
    n = matrix.shape[0]
    col_sums = matrix.sum(axis=0)
    normalized = matrix / col_sums
    weights = normalized.mean(axis=1)
    
    # Calcul du Consistency Ratio (CR)
    aw = np.dot(matrix, weights)
    lambda_max = np.mean(aw / weights)
    ci = (lambda_max - n) / (n - 1)
    # Random Index (RI) pour n=4 est ~0.90
    ri = 0.90
    cr = ci / ri
    
    consistent = bool(cr < 0.1)
    
    return {
        "weights": weights.tolist(),
        "CR": float(cr),
        "consistent": consistent
    }

def rank_prospects(prospects: list[dict]) -> list[dict]:
    """
    Prend des prospects réels, applique TOPSIS en utilisant les poids AHP calculés,
    et retourne les prospects enrichis avec le score TOPSIS et le classement.
    """
    if not prospects:
        return []

    ahp_result = calculate_ahp_weights()
    weights = np.array(ahp_result["weights"])
    
    # Extraire la matrice de décision
    decision_matrix = []
    for p in prospects:
        sf = safe_float(p.get("sector_fit", 5))
        ss = safe_float(p.get("size_score", 5))
        acc = safe_float(p.get("accessibility", 5))
        act = safe_float(p.get("recent_activity", 5))
        decision_matrix.append([sf, ss, acc, act])
        
    decision_matrix = np.array(decision_matrix)
    
    # Si un seul prospect, on le met automatiquement en Top
    if len(decision_matrix) == 1:
        prospects[0]["topsis_score"] = 1.0
        prospects[0]["topsis_rank"] = 1
        prospects[0]["priority_label"] = "Top"
        return prospects, ahp_result

    # 1. Normalisation vectorielle
    sq_sum = np.sqrt((decision_matrix ** 2).sum(axis=0))
    # Éviter division par zéro
    sq_sum[sq_sum == 0] = 1.0
    normalized_matrix = decision_matrix / sq_sum
    
    # 2. Pondération
    weighted_matrix = normalized_matrix * weights
    
    # 3. Solutions idéales (pour des critères à maximiser)
    ideal_best = weighted_matrix.max(axis=0)
    ideal_worst = weighted_matrix.min(axis=0)
    
    # 4. Distances
    dist_best = np.sqrt(((weighted_matrix - ideal_best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((weighted_matrix - ideal_worst) ** 2).sum(axis=1))
    
    # 5. Closeness Coefficient (CC)
    denominator = dist_best + dist_worst
    denominator[denominator == 0] = 1e-10
    cc = dist_worst / denominator
    
    # Enrichir les prospects
    for i, p in enumerate(prospects):
        p["topsis_score"] = float(cc[i])
        
    # Trier par score décroissant
    prospects.sort(key=lambda x: x["topsis_score"], reverse=True)
    
    # Assigner le rang et l'étiquette
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
