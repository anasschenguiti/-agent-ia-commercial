"""
Gestionnaire d'objections commerciales.
Détecte et répond aux objections courantes dans une conversation de vente.
"""

from typing import Dict, Optional


class ObjectionHandler:
    """
    Détecte et traite les objections commerciales classiques :
    - Prix trop élevé
    - Pas le bon moment
    - Déjà un fournisseur
    - Besoin de réfléchir
    - Manque de confiance
    """

    OBJECTION_PATTERNS: Dict[str, list] = {
        "price": [
            "trop cher", "budget", "prix", "coût", "on n'a pas les moyens",
            "c'est cher", "expensive", "too expensive",
        ],
        "timing": [
            "pas le bon moment", "plus tard", "revenir", "rappeler",
            "pas maintenant", "dans quelques mois",
        ],
        "competitor": [
            "déjà un fournisseur", "on travaille avec", "concurrent", "autre solution",
            "fournisseur", "prestataire",
        ],
        "think": [
            "réfléchir", "je dois voir", "je reviens", "laissez-moi le temps",
        ],
        "trust": [
            "pas sûr", "preuve", "référence", "témoignage", "qui êtes-vous",
        ],
    }

    REPONSES: Dict[str, str] = {
        "price": (
            "Je comprends que le budget est une préoccupation. "
            "Parlons de la valeur que vous allez obtenir et du ROI sur 6 mois..."
        ),
        "timing": (
            "C'est tout à fait compréhensible. "
            "Puis-je vous demander ce qui vous permettrait de vous lancer plus sereinement ?"
        ),
        "competitor": (
            "Super ! Qu'est-ce qui vous plaît ou vous manque dans votre solution actuelle ? "
            "Je pourrai vous montrer comment nous nous différencions."
        ),
        "think": (
            "Bien sûr, c'est une décision importante. "
            "Quels sont les points sur lesquels vous souhaitez réfléchir ?"
        ),
        "trust": (
            "Tout à fait normal. Je peux vous partager des études de cas "
            "et vous mettre en contact avec des clients similaires à vous."
        ),
    }

    def detect(self, message: str) -> Optional[str]:
        """
        Détecte le type d'objection dans le message.
        Retourne la clé de l'objection ou None.
        """
        message_lower = message.lower()
        for objection_type, patterns in self.OBJECTION_PATTERNS.items():
            if any(pattern in message_lower for pattern in patterns):
                return objection_type
        return None

    def handle(self, message: str, context: str = "") -> str:
        """Retourne une réponse adaptée à l'objection détectée."""
        objection_type = self.detect(message)
        if objection_type:
            return self.REPONSES.get(objection_type, self._default_response())
        return self._default_response()

    def _default_response(self) -> str:
        return "Je comprends votre point de vue. Pouvez-vous m'en dire plus ?"
