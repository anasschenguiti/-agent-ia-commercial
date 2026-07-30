"""
Modèles SQLAlchemy pour la prospection.
"""

from sqlalchemy import Column, String, Float, Text, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from app.shared.database import Base


class ProspectStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    IN_PROGRESS = "in_progress"
    QUALIFIED = "qualified"
    LOST = "lost"
    WON = "won"


class ProspectSQL(Base):
    """Représente un prospect dans la base de données PostgreSQL."""
    
    __tablename__ = "prospects"

    id = Column(String, primary_key=True, index=True)
    # REAL-ONLY: first_name / last_name peuvent être NULL — certaines sources (Overpass,
    # Sirene, OpenCorporates) ne renvoient qu'un nom d'entreprise + email/website.
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    location = Column(String, nullable=True)
    country = Column(String, nullable=True)
    annual_revenue = Column(String, nullable=True)
    technologies = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    data_confidence = Column(Text, nullable=True)  # Store JSON representation
    phone_source = Column(String, nullable=True)
    email_source = Column(String, nullable=True)
    company_size_source = Column(String, nullable=True)
    annual_revenue_source = Column(String, nullable=True)
    date_collecte = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    base_legale = Column(String, default="Intérêt Légitime (Prospection B2B)", nullable=True)
    status = Column(
        SQLEnum(ProspectStatus, name="prospect_status_enum", inherit_schema=True),
        default=ProspectStatus.NEW,
        nullable=False,
    )
    score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
