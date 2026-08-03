"""
Table SQL prospect_analysis pour enregistrer les diagnostics de l'Analyse IA (Module 2).
"""
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, func
from app.shared.database import Base


class ProspectAnalysisSQL(Base):
    """Stocke le diagnostic d'analyse digitale d'un prospect."""

    __tablename__ = "prospect_analysis"

    id = Column(String, primary_key=True, index=True)
    prospect_id = Column(String, index=True, nullable=False)
    website_url = Column(String, nullable=True)
    is_responsive = Column(Boolean, default=True)
    ssl_enabled = Column(Boolean, default=True)
    page_load_speed_score = Column(Float, default=8.0)
    detected_technologies = Column(Text, nullable=True)
    social_links = Column(Text, nullable=True)
    diagnostic_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
