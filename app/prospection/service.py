"""
Logique métier du module de prospection.
"""

import json
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.prospection.models import (
    ProspectCreate,
    ProspectRead,
    ProspectFilter,
    ProspectStatus,
)
from app.prospection.models_sql import ProspectSQL
from app.prospection.scraper import ProspectScraper
from app.prospection.scoring import ProspectScorer
from app.shared.database import get_db


class ProspectionService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db
        self.scraper = ProspectScraper()
        self.scorer = ProspectScorer()

    async def list_prospects(self, filters: ProspectFilter) -> List[ProspectRead]:
        """Récupère les prospects filtrés depuis la base de données."""
        stmt = select(ProspectSQL)
        
        if filters.status:
            stmt = stmt.where(ProspectSQL.status == filters.status)
        if filters.industry:
            stmt = stmt.where(ProspectSQL.industry.ilike(f"%{filters.industry}%"))
        if filters.min_score is not None:
            stmt = stmt.where(ProspectSQL.score >= filters.min_score)
        if filters.max_score is not None:
            stmt = stmt.where(ProspectSQL.score <= filters.max_score)
            
        # Tri du plus récent au plus ancien
        stmt = stmt.order_by(ProspectSQL.created_at.desc())

        # Pagination
        offset = (filters.page - 1) * filters.page_size
        stmt = stmt.offset(offset).limit(filters.page_size)
        
        result = await self.db.execute(stmt)
        prospects_db = result.scalars().all()
        
        return [ProspectRead.model_validate(p) for p in prospects_db]

    async def create_prospect(self, prospect: ProspectCreate, initial_score: Optional[float] = None) -> ProspectRead:
        """Crée un nouveau prospect en base."""
        temp_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        temp_prospect = ProspectRead(
            id=temp_id,
            **prospect.model_dump(),
            status=ProspectStatus.NEW,
            created_at=now,
            updated_at=now,
        )
        score = initial_score if initial_score is not None else self.scorer.compute_score(temp_prospect)
        
        db_prospect = ProspectSQL(
            id=temp_id,
            first_name=prospect.first_name,
            last_name=prospect.last_name,
            email=prospect.email,
            phone=prospect.phone,
            company=prospect.company,
            job_title=prospect.job_title,
            linkedin_url=prospect.linkedin_url,
            website=prospect.website,
            industry=prospect.industry,
            company_size=prospect.company_size,
            location=prospect.location,
            country=prospect.country,
            annual_revenue=prospect.annual_revenue,
            technologies=prospect.technologies,
            notes=prospect.notes,
            status=ProspectStatus.NEW,
            score=score,
        )
        
        self.db.add(db_prospect)
        await self.db.commit()
        await self.db.refresh(db_prospect)
        
        return ProspectRead.model_validate(db_prospect)

    async def get_prospect(self, prospect_id: str) -> Optional[ProspectRead]:
        """Récupère un prospect par son ID."""
        stmt = select(ProspectSQL).where(ProspectSQL.id == prospect_id)
        result = await self.db.execute(stmt)
        db_prospect = result.scalar_one_or_none()
        if not db_prospect:
            return None
        return ProspectRead.model_validate(db_prospect)

    async def get_score(self, prospect_id: str) -> Optional[float]:
        """Calcule ou récupère le score d'un prospect."""
        prospect = await self.get_prospect(prospect_id)
        if not prospect:
            return None
        return self.scorer.compute_score(prospect)

    async def run_scraping(self, query: dict) -> List[ProspectRead]:
        """
        Lance le scraping et sauvegarde UNIQUEMENT les prospects avec données réelles.

        REAL-ONLY CONTRACT : Si le scraper ne renvoie aucun prospect ayant au moins
        un email/phone/website RÉEL (et non inventé), aucun prospect n'est persisté.
        On remonte au routeur une liste vide et un message explicite.
        """
        raw_prospects = await self.scraper.search(query)
        created = []

        if not raw_prospects:
            print("[ProspectionService] Aucun prospect réel trouvé pour cette requête.")
            return created

        valid_keys = {
            "first_name", "last_name", "email", "phone", "company",
            "job_title", "linkedin_url", "website", "industry",
            "company_size", "location", "country", "annual_revenue",
            "technologies", "notes", "phone_source", "email_source",
            "linkedin_source", "company_size_source", "annual_revenue_source",
            "base_legale",
        }

        for raw in raw_prospects:
            # On ne persiste JAMAIS un prospect sans score TOPSIS réel calculé.
            raw_score = raw.get("score")
            if raw_score is None:
                print(f"[ProspectionService] Prospect ignoré (pas de score réel): {raw.get('company')}")
                continue

            # Garde-fou final : pas d'email inventé en base.
            if raw.get("email") and raw.get("email_source") not in ("website_crawl", "osm", "sirene", "opencorporates"):
                print(f"[ProspectionService] Email à source non vérifiée écarté: {raw.get('email')}")
                raw["email"] = None

            clean_raw = {k: v for k, v in raw.items() if k in valid_keys and v is not None and v != ""}
            if raw.get("data_confidence"):
                clean_raw["data_confidence"] = json.dumps(raw["data_confidence"])

            try:
                if clean_raw.get("email"):
                    stmt = select(ProspectSQL).where(ProspectSQL.email == clean_raw["email"])
                    res = await self.db.execute(stmt)
                    existing = res.scalar_one_or_none()
                    if existing:
                        created.append(ProspectRead.model_validate(existing))
                        continue

                prospect = await self.create_prospect(ProspectCreate(**clean_raw), initial_score=raw_score)
                created.append(prospect)
            except Exception as e:
                await self.db.rollback()
                print(f"[ProspectionService] Ingestion prospect ignorée : {e}")

        return created

    async def clear_all_prospects(self) -> None:
        """Supprime tous les prospects de la base de données."""
        stmt = delete(ProspectSQL)
        await self.db.execute(stmt)
        await self.db.commit()
