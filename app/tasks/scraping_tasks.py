"""
Tâches Celery pour le scraping asynchrone de prospects.
"""

from app.tasks.celery_app import celery_app
from app.prospection.scraper import ProspectScraper
from app.prospection.scoring import ProspectScorer


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_prospects(self, query: dict) -> dict:
    """
    Tâche de scraping asynchrone.
    Lance la recherche de prospects et persiste les résultats.
    """
    import asyncio
    try:
        scraper = ProspectScraper()
        scorer = ProspectScorer()

        try:
            prospects = asyncio.run(scraper.search(query))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                prospects = loop.run_until_complete(scraper.search(query))
            finally:
                loop.close()

        results = []
        for p in prospects:
            score = scorer.compute_score(p)  # type: ignore
            results.append({**p, "score": score})

        return {"count": len(results), "query": query, "status": "success"}
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task
def score_all_prospects() -> dict:
    """Recalcule les scores de tous les prospects non scorés."""
    # TODO: récupérer depuis la BDD et mettre à jour
    return {"status": "success", "updated": 0}
