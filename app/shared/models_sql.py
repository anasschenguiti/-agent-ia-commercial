"""
Modeles SQLAlchemy partages (ex: Utilisateurs).
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.shared.database import Base


class UserSQL(Base):
    """Represente un utilisateur (ex: commercial accedant au dashboard)."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # Week 1 : role utilisateur ('admin' ou 'user'). Migrations Alembic
    # ajouteront la colonne en Week 2 ; en attendant, ALTER TABLE idempotent
    # via init_db (cf app/shared/database.py).
    role = Column(String, nullable=False, server_default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
