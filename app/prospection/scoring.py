"""
Moteur de scoring et qualification des prospects.
"""

from typing import Optional
from app.prospection.models import ProspectRead


class ProspectScorer:
    """
    Calcule un score de 0 à 100 pour chaque prospect.
    Basé sur : complétude du profil, industrie cible, taille entreprise, signaux d'achat.
    """

    # Critères pondérés
    WEIGHTS = {
        "email": 20,
        "phone": 10,
        "linkedin_url": 10,
        "company": 15,
        "job_title": 10,
        "industry": 10,
        "company_size": 10,
        "location": 5,
        "notes": 10,
    }

    # Industries prioritaires
    TARGET_INDUSTRIES = {"SaaS", "Tech", "Finance", "Retail", "E-commerce"}

    def compute_score(self, prospect: ProspectRead) -> float:
        """Calcule le score d'un prospect (0–100)."""
        score = 0.0
        # mode='json' garantit que HttpUrl est converti en str (Pydantic v2)
        data = prospect.model_dump(mode="json")

        # Score de complétude
        for field, weight in self.WEIGHTS.items():
            if data.get(field):
                score += weight

        # Bonus industrie cible
        if prospect.industry and prospect.industry in self.TARGET_INDUSTRIES:
            score = min(score + 15, 100)

        return round(score, 2)

    def classify(self, score: float) -> str:
        """Classifie le prospect selon son score."""
        if score >= 80:
            return "hot"
        elif score >= 50:
            return "warm"
        else:
            return "cold"
