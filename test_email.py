import asyncio
import os
import sys

# Ensure the app module can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.communication.email_client import EmailClient
from app.shared.config import settings

def test():
    subject = "Opportunité de collaboration — {company}"
    content = "Bonjour {first_name},\n\nJ'ai remarqué votre travail chez {company} en tant que {job_title}. Nos solutions d'intelligence artificielle permettent d'automatiser et d'optimiser votre prospection commerciale de 40%.\n\nSeriez-vous disponible pour un court échange cette semaine ?\n\nCordialement,\nL'équipe commerciale."

    # Remplace les variables courantes par des données fictives pour le test
    dummy_data = {
        "{first_name}": "Jean",
        "{last_name}": "Dupont",
        "{company}": "Entreprise Fictive",
        "{job_title}": "Directeur",
    }
    for key, value in dummy_data.items():
        subject = subject.replace(key, value)
        content = content.replace(key, value)

    html_content = content.replace("\n", "<br>")

    print("Subject:", subject)
    client = EmailClient()
    success = client.send(
        to="salahmanaa18@gmail.com",
        subject=subject,
        body_html=f"<p>{html_content}</p>",
        body_text=content
    )
    if success:
        print("Envoi réussi selon le client SMTP !")
    else:
        print("Échec de l'envoi.")

if __name__ == "__main__":
    test()
