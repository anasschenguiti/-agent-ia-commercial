"""
Router FastAPI pour le Module 2 : Analyse IA (POST /api/analysis/{prospect_id}).
"""
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.database import get_db
from app.prospection.models_sql import ProspectSQL
from app.analysis.models_sql import ProspectAnalysisSQL
from app.analysis.website_analyzer import WebsiteAnalyzer
from app.analysis.diagnostic_generator import DiagnosticGenerator

router = APIRouter(prefix="/api/analysis", tags=["Module 2 : Analyse IA"])

analyzer = WebsiteAnalyzer()
generator = DiagnosticGenerator()


@router.post("/{prospect_id}")
async def analyze_prospect(prospect_id: str, db: AsyncSession = Depends(get_db)):
    """Exécute l'audit web factuel et génère le diagnostic d'analyse IA pour un prospect."""
    stmt = select(ProspectSQL).where(ProspectSQL.id == prospect_id)
    res = await db.execute(stmt)
    prospect = res.scalar_one_or_none()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect non trouvé")

    # 1. Audit web factuel
    signals = await analyzer.analyze(prospect.website or "")

    # 2. Génération du diagnostic factuel
    diag_text = generator.generate_diagnostic(prospect.company or "L'entreprise", signals)

    # 3. Enregistrement en base de données
    analysis_entry = ProspectAnalysisSQL(
        id=str(uuid.uuid4()),
        prospect_id=prospect_id,
        website_url=signals.website_url,
        is_responsive=signals.is_responsive,
        ssl_enabled=signals.ssl_enabled,
        page_load_speed_score=signals.page_load_speed_score,
        detected_technologies=", ".join(signals.detected_technologies),
        social_links=", ".join(signals.social_links),
        diagnostic_text=diag_text,
    )

    # Mettre à jour les notes du prospect avec le diagnostic
    prospect.notes = f"{prospect.notes or ''} | Diagnostic IA: {diag_text}"[:500]

    db.add(analysis_entry)
    await db.commit()
    await db.refresh(analysis_entry)

    return {
        "id": analysis_entry.id,
        "prospect_id": prospect_id,
        "signals": signals.model_dump(),
        "diagnostic": diag_text,
        "created_at": analysis_entry.created_at,
    }


@router.get("/{prospect_id}")
async def get_prospect_analysis(prospect_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère les diagnostics d'analyse IA d'un prospect."""
    stmt = select(ProspectAnalysisSQL).where(ProspectAnalysisSQL.prospect_id == prospect_id).order_by(ProspectAnalysisSQL.created_at.desc())
    res = await db.execute(stmt)
    entries = res.scalars().all()
    return entries
