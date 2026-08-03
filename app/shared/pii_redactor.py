"""
Module de rédaction PII (Personally Identifiable Information) avec Microsoft Presidio.
Anonymise les emails, numéros de téléphone (marocains +212/06/07), cartes d'identité (CIN) et noms.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger("sales_ai.safety.pii")


class PIIRedactor:
    """Anonymiseur PII utilisant Microsoft Presidio avec fallback Regex ultra-performant."""

    def __init__(self):
        self.analyzer = None
        self.anonymizer = None

    def _init_presidio(self):
        if self.analyzer is not None:
            return
        try:
            import spacy
            if spacy.util.is_package("en_core_web_lg") or spacy.util.is_package("en_core_web_sm"):
                from presidio_analyzer import AnalyzerEngine
                from presidio_anonymizer import AnonymizerEngine

                self.analyzer = AnalyzerEngine()
                self.anonymizer = AnonymizerEngine()
                logger.info("Microsoft Presidio Analyzer et Anonymizer initialisés avec succès.")
            else:
                logger.info("Modèle spacy non pré-téléchargé. Anonymisation par Regex ultra-rapide active.")
        except Exception as e:
            logger.warning(f"Presidio non chargé ({e}). Fallback regex PII actif.")

    def sanitize(self, text: str) -> str:
        """
        Anonymise le texte en remplaçant les données personnelles par des tokens anonymes.
        """
        if not text:
            return ""

        redacted_text = text

        # 1. Utilisation de Presidio si disponible
        if self.analyzer and self.anonymizer:
            try:
                results = self.analyzer.analyze(text=text, entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON"], language="en")
                anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
                redacted_text = anonymized.text
            except Exception as e:
                logger.warning(f"Erreur d'anonymisation Presidio : {e}")

        # 2. Fallback Regex pour spécificités marocaines (CIN, Téléphones +212, Emails)
        # Phone numbers: +2126..., 06..., 07..., +212 6...
        redacted_text = re.sub(
            r'(\+212|0)([5-7])\d{8}|\b0[5-7]\d{8}\b',
            '[PHONE_REDACTED]',
            redacted_text
        )

        # Email addresses
        redacted_text = re.sub(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            '[EMAIL_REDACTED]',
            redacted_text
        )

        # Moroccan CIN (Card ID): e.g. AB123456, C123456
        redacted_text = re.sub(
            r'\b[A-Za-z]{1,2}\d{5,7}\b',
            '[CIN_REDACTED]',
            redacted_text
        )

        return redacted_text


# Singleton global
pii_redactor = PIIRedactor()
