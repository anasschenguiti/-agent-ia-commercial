"""
Gestionnaire de templates de messages multicanaux (Email, WhatsApp, LinkedIn).
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class MessageTemplate(BaseModel):
    id: str
    channel: str  # email, whatsapp, linkedin
    name: str
    subject: Optional[str] = None
    content: str


# Templates par défaut du système
DEFAULT_TEMPLATES: Dict[str, MessageTemplate] = {
    "email_intro": MessageTemplate(
        id="email_intro",
        channel="email",
        name="Email de Premier Contact (J0)",
        subject="Opportunité de collaboration — {company}",
        content="Bonjour {first_name},\n\nJ'ai remarqué votre travail chez {company} en tant que {job_title}. Nos solutions d'intelligence artificielle permettent d'automatiser et d'optimiser votre prospection commercial de 40%.\n\nSeriez-vous disponible pour un court échange cette semaine ?\n\nCordialement,\nL'équipe commerciale."
    ),
    "email_followup_j3": MessageTemplate(
        id="email_followup_j3",
        channel="email",
        name="Email de Relance J3",
        subject="Re: Opportunité de collaboration — {company}",
        content="Bonjour {first_name},\n\nJe me permets de revenir vers vous concernant mon précédent message. Avez-vous eu l'occasion de le consulter ?\n\nJe serais ravi de vous présenter une courte démonstration adaptée à {company}.\n\nBien cordialement."
    ),
    "whatsapp_intro": MessageTemplate(
        id="whatsapp_intro",
        channel="whatsapp",
        name="Message WhatsApp d'Accroche",
        subject=None,
        content="Bonjour {first_name} ! 👋 Je suis l'assistant commercial d'IKSATECH. J'ai vu que vous dirigiez l'équipe chez {company}. Auriez-vous 5 min pour échanger sur vos enjeux actuels ?"
    ),
    "linkedin_intro": MessageTemplate(
        id="linkedin_intro",
        channel="linkedin",
        name="InMail LinkedIn Connexion",
        subject="Connexion — {company}",
        content="Bonjour {first_name}, ravi de vous ajouter à mon réseau professionnel. En tant que {job_title} chez {company}, vos perspectives d'innovation m'intéressent beaucoup !"
    )
}


class TemplateEngine:
    """Moteur de rendu et de gestion des templates."""

    def __init__(self):
        self.templates = dict(DEFAULT_TEMPLATES)

    def list_templates(self, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retourne la liste des templates enregistrés."""
        results = []
        for t in self.templates.values():
            if channel is None or t.channel.lower() == channel.lower():
                results.append(t.model_dump())
        return results

    def get_template(self, template_id: str) -> Optional[MessageTemplate]:
        """Récupère un template par son identifiant."""
        return self.templates.get(template_id)

    def save_template(self, template: MessageTemplate) -> MessageTemplate:
        """Ajoute ou met à jour un template."""
        self.templates[template.id] = template
        return template

    def delete_template(self, template_id: str) -> bool:
        """Supprime un template."""
        if template_id in self.templates:
            del self.templates[template_id]
            return True
        return False

    def render(self, template_id: str, context: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Rend un template avec les variables fournies (ex: prospect_info)."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} introuvable.")

        safe_context = {
            "first_name": context.get("first_name", "prospect"),
            "last_name": context.get("last_name", ""),
            "company": context.get("company", "votre entreprise"),
            "job_title": context.get("job_title", "Responsable"),
            "score": str(context.get("score", 50))
        }

        rendered_subject = None
        if template.subject:
            rendered_subject = template.subject.format(**safe_context)

        rendered_content = template.content.format(**safe_context)

        return {
            "channel": template.channel,
            "subject": rendered_subject,
            "content": rendered_content
        }


# Instance unique partagée
template_engine = TemplateEngine()
