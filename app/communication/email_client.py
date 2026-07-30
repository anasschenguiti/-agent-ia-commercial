"""
Client Email : envoi via SMTP ou SendGrid.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from typing import List, Optional

from app.shared.config import settings


class EmailClient:
    """
    Envoi d'emails transactionnels et de prospection.
    Supporte SMTP natif et SendGrid.
    """

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL

    def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
    ) -> bool:
        """Envoie un email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = self.from_email
        msg["To"] = to
        if cc:
            msg["Cc"] = ", ".join(cc)

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_password)
                recipients = [to] + (cc or [])
                server.sendmail(self.from_email, recipients, msg.as_string())
            return True
        except Exception as e:
            print(f"[EmailClient] Erreur d'envoi : {e}")
            return False

    def send_followup(self, to: str, day: int, prospect_name: str) -> bool:
        """Envoie un email de relance (J0, J3, J7, J15)."""
        templates = {
            0: f"Bonjour {prospect_name}, je fais suite à notre échange...",
            3: f"Bonjour {prospect_name}, j'espère que tout va bien...",
            7: f"Bonjour {prospect_name}, je reviens vers vous...",
            15: f"Bonjour {prospect_name}, dernière prise de contact...",
        }
        body = templates.get(day, "Bonjour, je fais suite à notre échange.")
        return self.send(
            to=to,
            subject=f"Suivi - Jour {day}",
            body_html=f"<p>{body}</p>",
        )
