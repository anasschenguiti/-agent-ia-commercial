"""
Service de gestion des relances automatiques (J0, J3, J7, J15).
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Depends

from app.shared.database import get_db
from app.prospection.models_sql import ProspectSQL, ProspectStatus
from app.conversation.models_sql import MessageSQL
from app.communication.email_client import EmailClient


class FollowUpService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db
        self.email_client = EmailClient()

    async def get_pending_followups(self, simulate_days: int = 0) -> List[Dict[str, Any]]:
        """
        Analyse la base pour identifier l'état des relances de chaque prospect.
        Le paramètre `simulate_days` décale fictivement la date actuelle dans le futur.
        """
        # 1. Récupérer tous les prospects non clos
        stmt = select(ProspectSQL).where(
            ProspectSQL.status.in_([ProspectStatus.NEW, ProspectStatus.CONTACTED, ProspectStatus.IN_PROGRESS])
        )
        result = await self.db.execute(stmt)
        prospects = result.scalars().all()

        followups = []
        now = datetime.now(timezone.utc) + timedelta(days=simulate_days)

        for p in prospects:
            # 2. Récupérer l'historique des messages du prospect
            msg_stmt = select(MessageSQL).where(MessageSQL.prospect_id == p.id).order_by(MessageSQL.timestamp.asc())
            msg_result = await self.db.execute(msg_stmt)
            messages = msg_result.scalars().all()

            state = "J0_PENDING"
            action = "Envoyer premier message (J0)"
            last_message_date = None
            elapsed_days = 0

            if not messages:
                # Aucun message échangé
                state = "J0_PENDING"
                action = "Envoyer premier message (J0)"
            else:
                latest = messages[-1]
                last_message_date = latest.timestamp
                # S'assurer que le timestamp est timezone-aware
                if last_message_date.tzinfo is None:
                    last_message_date = last_message_date.replace(tzinfo=timezone.utc)
                
                elapsed = now - last_message_date
                elapsed_days = elapsed.days

                if latest.role == "user":
                    state = "REPLIED"
                    action = "Réponse reçue : Traiter manuellement"
                else:
                    # Dernier message envoyé par l'assistant, calculer l'étape suivante
                    assistant_msgs = [m for m in messages if m.role == "assistant"]
                    count = len(assistant_msgs)

                    if count == 1:
                        if elapsed_days >= 3:
                            state = "J3_PENDING"
                            action = "Envoyer relance J3"
                        else:
                            state = "J3_WAITING"
                            action = f"En attente J3 (encore {3 - elapsed_days} jours)"
                    elif count == 2:
                        if elapsed_days >= 4:
                            state = "J7_PENDING"
                            action = "Envoyer relance J7"
                        else:
                            state = "J7_WAITING"
                            action = f"En attente J7 (encore {4 - elapsed_days} jours)"
                    elif count == 3:
                        if elapsed_days >= 8:
                            state = "J15_PENDING"
                            action = "Envoyer relance J15"
                        else:
                            state = "J15_WAITING"
                            action = f"En attente J15 (encore {8 - elapsed_days} jours)"
                    else:
                        state = "COMPLETED"
                        action = "Cycle de relances terminé"

            followups.append({
                "prospect_id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "company": p.company,
                "email": p.email,
                "status": p.status,
                "state": state,
                "action": action,
                "last_message_date": last_message_date.isoformat() if last_message_date else None,
                "elapsed_days": elapsed_days
            })

        return followups

    async def trigger_followup(self, prospect_id: str) -> Dict[str, Any]:
        """
        Déclenche la relance du prospect et enregistre le message correspondant.
        """
        # 1. Charger le prospect
        stmt = select(ProspectSQL).where(ProspectSQL.id == prospect_id)
        result = await self.db.execute(stmt)
        prospect = result.scalar_one_or_none()
        if not prospect:
            return {"status": "error", "detail": "Prospect non trouvé"}

        # 2. Déterminer l'état actuel de la relance (sans décalage)
        followups = await self.get_pending_followups(simulate_days=0)
        p_info = next((f for f in followups if f["prospect_id"] == prospect_id), None)
        if not p_info:
            return {"status": "error", "detail": "Prospect non éligible aux relances"}

        state = p_info["state"]
        if "WAITING" in state or state == "COMPLETED" or state == "REPLIED":
            return {"status": "warning", "detail": f"Aucune relance urgente requise (État actuel: {state})"}

        # 3. Rédiger le brouillon
        drafts = {
            "J0_PENDING": f"Bonjour {prospect.first_name}, ravi d'entrer en contact. J'ai découvert votre activité chez {prospect.company} et je serais enchanté d'échanger sur vos défis actuels.",
            "J3_PENDING": f"Bonjour {prospect.first_name}, je me permets de faire suite à mon précédent message. Auriez-vous 10 minutes à accorder à notre sujet cette semaine ?",
            "J7_PENDING": f"Bonjour {prospect.first_name}, je reviens vers vous concernant notre proposition. L'IA permet d'optimiser l'acquisition client pour des entreprises comme {prospect.company}.",
            "J15_PENDING": f"Bonjour {prospect.first_name}, c'est ma dernière tentative pour vous joindre. Si le sujet de l'IA n'est pas prioritaire, aucun souci. Au plaisir d'échanger plus tard !"
        }
        message_content = drafts.get(state, f"Bonjour {prospect.first_name}, je fais suite à notre échange.")

        # 4. Insérer le message en base de données
        new_msg = MessageSQL(
            session_id=prospect.id,
            prospect_id=prospect.id,
            role="assistant",
            content=message_content
        )
        self.db.add(new_msg)

        # 5. Mettre à jour le statut du prospect
        prospect.status = ProspectStatus.CONTACTED
        await self.db.commit()

        # 6. Envoyer le mail simulé
        if prospect.email:
            self.email_client.send(
                to=prospect.email,
                subject=f"Prise de contact — IKSATECH" if state == "J0_PENDING" else "Suivi d'échange — IKSATECH",
                body_html=f"<p>{message_content}</p>"
            )

        return {
            "status": "success",
            "state_triggered": state,
            "message_sent": message_content,
            "prospect_id": prospect_id
        }
