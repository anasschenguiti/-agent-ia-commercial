"""
Tâches Celery pour les relances automatiques J0/J3/J7/J15.
"""

from datetime import datetime, timedelta
from app.tasks.celery_app import celery_app
from app.communication.email_client import EmailClient
from app.communication.whatsapp_client import WhatsAppClient


FOLLOWUP_DAYS = [0, 3, 7, 15]


@celery_app.task
def check_and_send_followups() -> dict:
    """
    Vérifie les prospects nécessitant une relance et les planifie via Celery.
    Appelé toutes les 24h via Celery Beat.
    """
    import asyncio
    from app.shared.database import AsyncSessionLocal
    from app.prospection.followup_service import FollowUpService

    async def _run():
        async with AsyncSessionLocal() as db:
            service = FollowUpService(db=db)
            pending_list = await service.get_pending_followups(simulate_days=0)
            sent_count = 0
            for item in pending_list:
                state = item.get("state", "")
                if state.endswith("_PENDING"):
                    day_val = 0
                    if "J3" in state: day_val = 3
                    elif "J7" in state: day_val = 7
                    elif "J15" in state: day_val = 15

                    send_followup_email.delay(
                        prospect_id=item["prospect_id"],
                        email=item["email"],
                        name=item["first_name"],
                        day=day_val
                    )
                    sent_count += 1
            return {"checked": len(pending_list), "dispatched": sent_count}

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def send_followup_email(
    self, prospect_id: str, email: str, name: str, day: int
) -> dict:
    """
    Envoie un email de relance pour un prospect donné.
    
    Args:
        prospect_id: Identifiant du prospect
        email: Adresse email du prospect
        name: Prénom du prospect
        day: Jour de relance (0, 3, 7 ou 15)
    """
    try:
        client = EmailClient()
        success = client.send_followup(to=email, day=day, prospect_name=name)
        status = "sent" if success else "failed"
        return {
            "prospect_id": prospect_id,
            "day": day,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def send_followup_whatsapp(
    self, prospect_id: str, phone: str, name: str, day: int
) -> dict:
    """Envoie une relance WhatsApp."""
    import asyncio
    try:
        client = WhatsAppClient()
        message = f"Bonjour {name}, je fais suite à notre échange (J{day})."
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(client.send_text(to=phone, message=message))
        return {
            "prospect_id": prospect_id,
            "day": day,
            "channel": "whatsapp",
            "result": result,
        }
    except Exception as exc:
        raise self.retry(exc=exc)
