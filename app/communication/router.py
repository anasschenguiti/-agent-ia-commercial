"""
Routeur FastAPI pour les canaux de communication et la gestion des templates.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends

from app.communication.templates import template_engine, MessageTemplate
from app.communication.email_client import EmailClient
from app.communication.whatsapp_client import WhatsAppClient
from app.shared.auth import get_current_user, TokenData

router = APIRouter()


@router.get("/templates")
async def list_templates(
    channel: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Liste tous les templates de messages enregistrés."""
    return template_engine.list_templates(channel=channel)


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_or_update_template(
    template: MessageTemplate,
    current_user: TokenData = Depends(get_current_user)
):
    """Crée ou met à jour un template de message."""
    saved = template_engine.save_template(template)
    return saved.model_dump()


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Supprime un template."""
    success = template_engine.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template introuvable")
    return {"message": "Template supprimé avec succès"}


@router.post("/render")
async def render_template_preview(
    payload: dict,
    current_user: TokenData = Depends(get_current_user)
):
    """Rend la prévisualisation d'un template avec les données d'un prospect."""
    template_id = payload.get("template_id")
    context = payload.get("context", {})
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id requis")

    try:
        return template_engine.render(template_id, context)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/send-test")
async def send_test_message(
    payload: dict,
    current_user: TokenData = Depends(get_current_user)
):
    """Simule ou exécute un envoi de test sur un canal donné."""
    channel = payload.get("channel", "email").lower()
    to = payload.get("to")
    subject = payload.get("subject", "Test Sales AI Agent")
    content = payload.get("content", "Ceci est un message de test.")

    if not to:
        raise HTTPException(status_code=400, detail="Destinataire (to) requis")

    # Remplace les variables courantes par des données fictives pour le test
    dummy_data = {
        "{first_name}": "Alexandre",
        "{last_name}": "Martin",
        "{company}": "Acme Corp",
        "{job_title}": "Directeur Commercial",
    }
    for key, value in dummy_data.items():
        subject = subject.replace(key, value)
        content = content.replace(key, value)

    # Convertit les retours à la ligne en balises HTML pour l'affichage dans l'email
    html_content = content.replace("\n", "<br>")

    if channel == "email":
        client = EmailClient()
        success = client.send(to=to, subject=subject, body_html=f"<p>{html_content}</p>", body_text=content)
        if not success:
            raise HTTPException(status_code=400, detail="Échec de l'envoi de l'email via SMTP. Vérifiez vos identifiants.")
        return {"channel": "email", "status": "sent", "to": to}
    
    elif channel == "whatsapp":
        client = WhatsAppClient()
        result = await client.send_text(to=to, message=content)
        return {"channel": "whatsapp", "status": "sent", "result": result}
    
    elif channel == "linkedin":
        from app.communication.linkedin_client import LinkedInClient
        client = LinkedInClient()
        result = await client.send_message(recipient_urn=to, message=content)
        return {"channel": "linkedin", "status": "sent", "result": result}

    raise HTTPException(status_code=400, detail=f"Canal inconnu: {channel}")
