"""
Test unitaire — A3 : Scoring AHP/TOPSIS 5 critères du Cahier des Charges et score_breakdown.
"""
from app.prospection.osmos.ahp_topsis import (
    build_scoring_inputs,
    calculate_ahp_weights,
    rank_prospects,
    CRITERIA_NAMES
)


def test_ahp_5_criteria_weights():
    res = calculate_ahp_weights()
    assert len(res["weights"]) == 5
    assert res["criteria"] == CRITERIA_NAMES
    assert res["consistent"] is True


def test_build_scoring_inputs_sources():
    prospect = {
        "industry": "SaaS B2B Tech",
        "annual_revenue": "2M - 10M MAD",
        "website": "https://example.com",
        "technologies": "WordPress, React",
        "linkedin_url": "https://linkedin.com/company/example",
        "location": "Casablanca"
    }
    inputs = build_scoring_inputs(prospect)
    assert inputs["activite_compatible"] == 9.0
    assert inputs["budget_potentiel"] == 8.5
    assert inputs["presence_digitale"] == 9.0
    assert inputs["croissance"] == 8.0
    assert inputs["localisation"] == 8.5
    assert "scoring_sources" in inputs


def test_rank_prospects_score_breakdown():
    prospects = [
        {"company": "CompA", "industry": "Tech", "website": "https://compa.ma"},
        {"company": "CompB", "industry": "Autre", "website": ""}
    ]
    ranked, ahp_res = rank_prospects(prospects)
    assert len(ranked) == 2
    top = ranked[0]
    assert "score_breakdown" in top
    assert "activite_compatible" in top["score_breakdown"]
    assert "presence_digitale" in top["score_breakdown"]
