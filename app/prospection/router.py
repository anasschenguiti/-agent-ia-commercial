"""
Endpoints API pour le module de prospection.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List

from app.prospection.models import ProspectCreate, ProspectRead, ProspectFilter
from app.prospection.service import ProspectionService

router = APIRouter()


@router.get("/prospects", response_model=List[ProspectRead])
async def list_prospects(
    filters: ProspectFilter = Depends(),
    service: ProspectionService = Depends(),
):
    """Récupère la liste des prospects avec filtres optionnels."""
    return await service.list_prospects(filters)


@router.post("/prospects", response_model=ProspectRead, status_code=201)
async def create_prospect(
    prospect: ProspectCreate,
    service: ProspectionService = Depends(),
):
    """Crée un nouveau prospect manuellement."""
    return await service.create_prospect(prospect)


@router.get("/prospects/{prospect_id}", response_model=ProspectRead)
async def get_prospect(
    prospect_id: str,
    service: ProspectionService = Depends(),
):
    """Récupère un prospect par son ID."""
    prospect = await service.get_prospect(prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect non trouvé")
    return prospect


@router.post("/search")
async def launch_scraping(
    payload: dict,
    service: ProspectionService = Depends(),
):
    """
    Exécute la recherche et le scraping de prospects de façon synchrone.

    REAL-ONLY : si aucune source réelle (Overpass / Sirene / OpenCorporates /
    Bing / DuckDuckGo) ne renvoie de donnée vérifiée, la réponse contient
    count=0 et un `warning` expliquant pourquoi — aucun prospect fabriqué.
    """
    query = payload.get("query", payload) if "query" in payload else payload
    prospects = await service.run_scraping(query)

    if not prospects:
        return {
            "message": "Aucun résultat réel trouvé.",
            "warning": (
                "Aucune source de données réelle n'a renvoyé de prospect vérifié pour cette "
                "requête. Vérifiez votre clé BING_SEARCH_API_KEY dans .env, élargissez vos "
                "mots-clés ou votre zone géographique, puis réessayez. Aucun prospect n'a "
                "été inventé."
            ),
            "count": 0,
            "prospects": [],
        }

    return {
        "message": "Recherche terminée avec données réelles uniquement",
        "count": len(prospects),
        "prospects": prospects,
    }


@router.delete("/prospects")
async def clear_all_prospects(
    service: ProspectionService = Depends(),
):
    """Supprime tous les prospects de la base de données (pour nettoyage)."""
    await service.clear_all_prospects()
    return {"message": "Base de données réinitialisée avec succès"}


@router.delete("/prospects/{prospect_id}/gdpr")
async def delete_prospect_gdpr(
    prospect_id: str,
    service: ProspectionService = Depends(),
):
    """Suppression d'un prospect au titre du droit d'opposition RGPD."""
    prospect = await service.get_prospect(prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect non trouvé")
    await service.delete_prospect(prospect_id)
    return {"message": f"Prospect {prospect_id} supprimé définitivement (Conformité RGPD)"}


@router.get("/analytics")
async def get_analytics(
    service: ProspectionService = Depends(),
):
    """Calcule et retourne les métriques d'analytics et de conversion."""
    from app.prospection.models import ProspectFilter
    all_prospects = await service.list_prospects(ProspectFilter(page=1, page_size=1000))
    total = len(all_prospects)
    hot = [p for p in all_prospects if p.score and p.score >= 80]
    warm = [p for p in all_prospects if p.score and 50 <= p.score < 80]
    cold = [p for p in all_prospects if p.score and p.score < 50]
    
    avg_score = round(sum(p.score or 0 for p in all_prospects) / total, 1) if total > 0 else 0
    contacted = [p for p in all_prospects if p.status in ["contacted", "in_progress"]]

    return {
        "total_prospects": total,
        "hot_count": len(hot),
        "warm_count": len(warm),
        "cold_count": len(cold),
        "avg_score": avg_score,
        "contacted_count": len(contacted),
        "conversion_rate": round((len(hot) / total * 100), 1) if total > 0 else 0
    }


@router.get("/export/csv")
async def export_prospects_csv(
    service: ProspectionService = Depends(),
):
    """Exporte la liste complète des prospects au format CSV."""
    import csv
    import io
    from fastapi.responses import Response
    from app.prospection.models import ProspectFilter

    prospects = await service.list_prospects(ProspectFilter(page=1, page_size=5000))
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # En-tête CSV
    writer.writerow([
        "ID", "Prénom", "Nom", "Email", "Téléphone", 
        "Entreprise", "Poste", "Industrie", "Taille", "Localisation", "Score", "Statut"
    ])
    
    # Données
    for p in prospects:
        writer.writerow([
            p.id, p.first_name, p.last_name, p.email, p.phone or "",
            p.company, p.job_title or "", p.industry or "", p.company_size or "",
            p.location or "", p.score or 0, p.status.value if hasattr(p.status, "value") else str(p.status)
        ])
        
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=prospects_export.csv"}
    )


@router.get("/prospects/{prospect_id}/score")
async def get_prospect_score(
    prospect_id: str,
    service: ProspectionService = Depends(),
):
    """Retourne le score de qualification d'un prospect."""
    score = await service.get_score(prospect_id)
    if score is None:
        raise HTTPException(status_code=404, detail="Prospect non trouvé")
    return {"prospect_id": prospect_id, "score": score}


from app.prospection.followup_service import FollowUpService

@router.get("/followups")
async def check_followups(
    simulate_days: int = 0,
    service: FollowUpService = Depends(),
):
    """Calcule l'état de relance des prospects (J0, J3, J7, J15)."""
    return await service.get_pending_followups(simulate_days=simulate_days)


@router.post("/followups/trigger/{prospect_id}")
async def trigger_followup(
    prospect_id: str,
    service: FollowUpService = Depends(),
):
    """Déclenche la relance correspondante pour un prospect."""
    return await service.trigger_followup(prospect_id)


# ---------------------------------------------------------------------------
# Endpoints OSMOS — Scoring AHP/TOPSIS, Persona IA, Plan d'action
# ---------------------------------------------------------------------------

from app.prospection.models import (
    OsmosScoreRequest, OsmosScoreResponse, OsmosScoreResult,
    PersonaRequest, PersonaOutput,
    OsmosPlanRequest, ActionPlanOutput, ContentOutput,
)
from app.prospection.osmos.ahp_topsis import rank_prospects, calculate_ahp_weights, topsis_score_to_100
from app.prospection.osmos.persona_engine import generate_persona, PersonaGenerationError
from app.prospection.osmos.plan_engine import generate_action_plan, generate_content, PlanGenerationError, ContentGenerationError


@router.post("/osmos/score", response_model=OsmosScoreResponse, tags=["OSMOS"])
async def osmos_score_prospects(payload: OsmosScoreRequest):
    """
    🎯 Scoring multicritères AHP/TOPSIS sur une liste de prospects.
    Retourne chaque prospect avec son score TOPSIS (0–1), rang, et label de priorité (Top/High/Medium/Low).
    """
    prospects_data = [p.model_dump() for p in payload.prospects]
    ranked, ahp = rank_prospects(prospects_data)

    results = [
        OsmosScoreResult(
            name=p.get("name", ""),
            topsis_score=p.get("topsis_score", 0.0),
            topsis_rank=p.get("topsis_rank", 0),
            priority_label=p.get("priority_label", "Low"),
            score_100=topsis_score_to_100(p.get("topsis_score", 0.0)),
        )
        for p in ranked
    ]

    return OsmosScoreResponse(
        results=results,
        ahp_weights=ahp["weights"],
        ahp_consistent=ahp["consistent"],
        ahp_cr=ahp["CR"],
    )


@router.post("/osmos/persona", tags=["OSMOS"])
async def osmos_generate_persona(payload: PersonaRequest):
    """
    🤖 Génère un persona commercial virtuel B2B via IA (Ollama qwen3:8b ou OpenAI GPT-4o).
    Le persona est marocain, crédible, et adapté au secteur et aux prospects cibles.
    """
    try:
        persona = generate_persona(
            company_name=payload.campaign.company_name,
            company_sector=payload.campaign.company_sector,
            value_proposition=payload.campaign.value_proposition,
            prospects_summary=payload.prospects_names,
        )
        return {"success": True, "persona": persona}
    except PersonaGenerationError as e:
        raise HTTPException(status_code=503, detail=f"Erreur de génération du persona : {str(e)}")


@router.post("/osmos/plan", tags=["OSMOS"])
async def osmos_generate_plan(payload: OsmosPlanRequest):
    """
    📋 Génère un plan de prospection LinkedIn en 6 étapes (3 semaines) + contenus prêts à envoyer
    (post LinkedIn, commentaire court, DM direct) — entièrement personnalisés via IA.
    """
    persona = payload.persona
    prospect = payload.prospect
    campaign = payload.campaign

    # Génération du plan d'action
    try:
        plan_raw = generate_action_plan(
            persona_name=persona.full_name,
            persona_role=persona.role,
            persona_work_style=persona.work_style,
            prospect_name=prospect.contact_name or prospect.name,
            prospect_title=prospect.contact_title or "Décideur",
            prospect_company=prospect.name,
            prospect_sector=prospect.sector or campaign.company_sector,
        )
    except PlanGenerationError as e:
        raise HTTPException(status_code=503, detail=f"Erreur de génération du plan : {str(e)}")

    # Génération des contenus LinkedIn
    try:
        content_raw = generate_content(
            persona_name=persona.full_name,
            persona_role=persona.role,
            company_name=campaign.company_name,
            value_proposition=campaign.value_proposition,
            prospect_name=prospect.contact_name or prospect.name,
            prospect_title=prospect.contact_title or "Décideur",
        )
    except ContentGenerationError as e:
        raise HTTPException(status_code=503, detail=f"Erreur de génération des contenus : {str(e)}")

    return {
        "success": True,
        "action_plan": plan_raw,
        "content": content_raw,
    }

