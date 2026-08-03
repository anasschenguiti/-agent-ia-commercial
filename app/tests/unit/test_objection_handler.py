"""
Tests unitaires pour le gestionnaire d'objections.
"""

import pytest
from app.conversation.objection_handler import ObjectionHandler


@pytest.fixture
def handler():
    return ObjectionHandler()


def test_detect_price_objection(handler):
    assert handler.detect("C'est trop cher pour nous") == "price"


def test_detect_timing_objection(handler):
    assert handler.detect("Ce n'est pas le bon moment") == "timing"


def test_detect_competitor_objection(handler):
    assert handler.detect("On travaille déjà avec un fournisseur") == "competitor"


def test_detect_no_objection(handler):
    assert handler.detect("Très intéressant, je veux en savoir plus") is None


def test_handle_returns_string(handler):
    response = handler.handle("C'est trop cher")
    assert isinstance(response, str)
    assert len(response) > 0
