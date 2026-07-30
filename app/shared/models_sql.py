"""
Modèles SQLAlchemy partagés (ex: Utilisateurs).
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.shared.database import Base


class UserSQL(Base):
    """Représente un utilisateur (ex: commercial accédant au dashboard)."""
    
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
