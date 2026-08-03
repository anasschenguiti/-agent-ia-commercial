"""
Tests unitaires pour le module de scoring.
"""

import pytest
from app.prospection.scoring import ProspectScorer
from app.prospection.models import ProspectRead, ProspectStatus
from datetime import datetime


@pytest.fixture
def scorer():
    return ProspectScorer()


@pytest.fixture
def full_prospect():
    return ProspectRead(
        id="test-001",
        first_name="Jean",
        last_name="Dupont",
        email="jean.dupont@company.com",
        phone="+33612345678",
        company="TechCorp",
        job_title="CTO",
        linkedin_url="https://www.linkedin.com/in/jean-dupont",  # URL complète requise par Pydantic v2
        industry="SaaS",
        company_size="50-200",
        location="Paris",
        notes="Intéressé par notre offre",
        status=ProspectStatus.NEW,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def test_score_complete_prospect(scorer, full_prospect):
    score = scorer.compute_score(full_prospect)
    assert score > 50, "Un prospect complet doit avoir un score > 50"


def test_score_target_industry_bonus(scorer, full_prospect):
    # Enlever un champ pour éviter de saturer la note à 100
    incomplete_prospect = full_prospect.model_copy(update={"notes": None})
    score_saas = scorer.compute_score(incomplete_prospect)
    prospect_other = incomplete_prospect.model_copy(update={"industry": "Unknown"})
    score_other = scorer.compute_score(prospect_other)
    assert score_saas > score_other, "Une industrie cible doit donner un bonus"


def test_classify_hot(scorer):
    assert scorer.classify(85) == "hot"


def test_classify_warm(scorer):
    assert scorer.classify(60) == "warm"


def test_classify_cold(scorer):
    assert scorer.classify(30) == "cold"
