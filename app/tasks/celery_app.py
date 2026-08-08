"""
Configuration et initialisation de l'application Celery.
"""

from celery import Celery
from app.shared.config import settings

celery_app = Celery(
    "sales_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.scraping_tasks",
        "app.tasks.followup_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
    # Retry policy par défaut
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Beat schedule (tâches périodiques)
    beat_schedule={
        "check-followups-every-morning": {
            "task": "app.tasks.followup_tasks.check_and_send_followups",
            "schedule": 86400.0,  # toutes les 24h
        },
    },
)
