"""
Module 2 : Signal Extractor — Modèle Pydantic DigitalSignals.
"""
from typing import List, Optional
from pydantic import BaseModel


class DigitalSignals(BaseModel):
    website_url: str
    is_responsive: bool = True
    ssl_enabled: bool = True
    page_load_speed_score: float = 8.0  # 1-10
    detected_technologies: List[str] = []
    social_links: List[str] = []
    has_contact_form: bool = False
    has_analytics: bool = False
    has_modern_cms: bool = False
    notes: Optional[str] = None
