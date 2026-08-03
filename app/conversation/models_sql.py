"""
Modèles SQLAlchemy pour les conversations/messages.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.shared.database import Base


class MessageSQL(Base):
    """Stockage persistant de l'historique des conversations."""
    
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    prospect_id = Column(String, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=True)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
