"""
Modèles Pydantic et entités pour le module de prospection.
"""

from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class ProspectStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    IN_PROGRESS = "in_progress"
    QUALIFIED = "qualified"
    LOST = "lost"
    WON = "won"


class ProspectBase(BaseModel):
    # first_name / last_name peuvent être None pour les prospects dont la source
    # (Sirene, Overpass) ne fournit que le nom d'entreprise + email/website.
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    annual_revenue: Optional[str] = None
    technologies: Optional[str] = None
    notes: Optional[str] = None
    data_confidence: Optional[Dict[str, str]] = None
    # REAL-ONLY : pas de valeur par défaut trompeuse. La source N'est "vérifiée"
    # que si une vraie source (website_crawl, osm, sirene, opencorporates) l'a remplie.
    phone_source: Optional[str] = None
    email_source: Optional[str] = None
    linkedin_source: Optional[str] = None
    company_size_source: Optional[str] = None
    annual_revenue_source: Optional[str] = None
    score_breakdown: Optional[Dict[str, float]] = None
    date_collecte: Optional[datetime] = None
    base_legale: Optional[str] = "Intérêt Légitime (Prospection B2B)"


class ProspectCreate(ProspectBase):
    pass


class ProspectRead(ProspectBase):
    id: str
    status: ProspectStatus = ProspectStatus.NEW
    score: Optional[float] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProspectFilter(BaseModel):
    status: Optional[ProspectStatus] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    page: int = 1
    page_size: int = 20


class ScrapingQuery(BaseModel):
    keywords: List[str]
    location: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[str] = None
    max_results: int = 50


# ---------------------------------------------------------------------------
# Modèles OSMOS — Scoring AHP/TOPSIS, Persona, Plan d'action
# ---------------------------------------------------------------------------

class CampaignInput(BaseModel):
    """Informations de campagne pour les moteurs OSMOS."""
    company_name: str
    company_sector: str
    value_proposition: str
    linkedin_url: Optional[str] = None


class ProspectForScoring(BaseModel):
    """Prospect enrichi avec les critères nécessaires pour le scoring AHP/TOPSIS."""
    name: str
    sector: Optional[str] = None
    size: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    sector_fit: Optional[float] = 5.0       # Score 1–10
    size_score: Optional[float] = 5.0       # Score 1–10
    accessibility: Optional[float] = 5.0   # Score 1–10
    recent_activity: Optional[float] = 5.0  # Score 1–10


class OsmosScoreRequest(BaseModel):
    """Requête pour le scoring multicritères TOPSIS."""
    prospects: List[ProspectForScoring]


class OsmosScoreResult(BaseModel):
    """Prospect enrichi après scoring TOPSIS."""
    name: str
    topsis_score: float
    topsis_rank: int
    priority_label: str   # "Top" | "High" | "Medium" | "Low"
    score_100: float      # Score converti sur 100 (compatible avec le reste du projet)


class OsmosScoreResponse(BaseModel):
    """Réponse complète du scoring TOPSIS."""
    results: List[OsmosScoreResult]
    ahp_weights: List[float]
    ahp_consistent: bool
    ahp_cr: float


class PersonaOutput(BaseModel):
    """Persona commercial généré par le LLM."""
    full_name: str
    headline: str
    role: str
    seniority: str
    age: int
    bio: str
    work_style: str
    key_skills: List[str]
    past_projects: List[dict]


class PersonaRequest(BaseModel):
    """Requête de génération de persona."""
    campaign: CampaignInput
    prospects_names: Optional[List[str]] = None  # Noms des cibles pour contextualiser


class ActionStep(BaseModel):
    """Une étape du plan de prospection."""
    day: int
    action_type: str   # "like" | "comment" | "connect" | "message" | "post" | "dm"
    rationale: str


class ActionPlanOutput(BaseModel):
    """Plan d'action LinkedIn en 6 étapes."""
    steps: List[ActionStep]


class ContentOutput(BaseModel):
    """Contenus LinkedIn générés : post, commentaire, DM."""
    post_text: str
    short_comment: str
    direct_message: str


class OsmosPlanRequest(BaseModel):
    """Requête complète pour générer plan + contenus."""
    campaign: CampaignInput
    persona: PersonaOutput
    prospect: ProspectForScoring

