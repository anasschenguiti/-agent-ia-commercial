"""
Script 2 & 3: Formatage et équilibrage du jeu de données (Darija + Français B2B).
Convertit les paires Darija-Anglais d'atlasia et 3000 répliques B2B Commerciales Françaises/Darija
au format Chat JSONL (system/user/assistant) dans data/processed/train_darija_fr.jsonl.
"""
import os
import json
import random
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("format_darija")

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_FILE = BASE_DIR / "data" / "raw" / "darija_english.json"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_JSONL = PROCESSED_DIR / "train_darija_fr.jsonl"

SYSTEM_PROMPT = (
    "Tu es un conseiller commercial d'élite pour IKSATECH au Maroc.\n"
    "Tu réponds naturellement en Darija marocaine courtoise quand on s'adresse à toi en Darija ou Arabizi, "
    "et en Français clair, chaleureux et professionnel quand on s'adresse à toi en Français."
)

# Dialogue commercial B2B Français & Darija marocaine d'élite
FRENCH_B2B_SAMPLES = [
    ("Bonjour, quels sont vos tarifs pour un site web ?", "Bonjour ! Chez IKSATECH, la création de site web sur-mesure commence à partir de 4 900 DH. Nous serions ravis d'échanger 15 minutes avec vous pour adapter notre devis à vos besoins."),
    ("Vos tarifs sont trop chers par rapport à la concurrence.", "Nous comprenons votre préoccupation budgétaire. Chez IKSATECH, nos tarifs incluent l'intégration d'agents IA, l'optimisation SEO et un suivi dédié pour garantir un fort retour sur investissement."),
    ("Pouvez-vous créer un chatbot WhatsApp pour mon entreprise ?", "Absolument ! Nos chatbots WhatsApp intelligents automatiseront la prise de rendez-vous et le support client 24/7. Souhaitez-vous planifier une démo de 15 minutes ?"),
    ("Combien de temps faut-il pour livrer un projet ?", "En général, nos projets web et IA sont livrés en 2 à 4 semaines selon la complexité des fonctionnalités souhaitées."),
    ("Est-ce que vous développez des applications mobiles ?", "Oui, nos experts développent des applications mobiles iOS et Android performantes et synchronisées avec vos systèmes CRM."),
    ("Salam, bch7al kayklaf site web ?", "Salam ! Marhaba bik f IKSATECH. Site web sur-mesure dialna t3awwal 4 900 DH. Wach bghiti ndiro m3ak court échange dial 15 min باش nchoufo l'mkaniyyat dialk ?"),
    ("Kifach t9dro t3awnona f l'automatisation ?", "Marhaba bik ! Notre équipe intègre des agents IA et automatismes CRM pour tripler votre productivité commerciale. N7am 15 min m3a l'expert ?")
]

def format_dataset():
    logger.info("Début du formatage du jeu de données Darija + Français...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    formatted_records = []

    # 1. Chargement des paires Darija atlasia
    if RAW_FILE.exists():
        logger.info(f"Chargement des données Darija brutes depuis : {RAW_FILE}")
        with open(RAW_FILE, "r", encoding="utf-8") as f:
            raw_darija = json.load(f)

        # On filtre les paires non vides et valides (10 000 exemples)
        valid_darija = [item for item in raw_darija if item.get("darija") and item.get("english")]
        sample_darija = random.sample(valid_darija, min(10000, len(valid_darija)))

        for item in sample_darija:
            eng = item.get("english", "").strip()
            dar = item.get("darija", "").strip()
            formatted_records.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": eng},
                    {"role": "assistant", "content": dar}
                ]
            })
        logger.info(f"Formaté {len(sample_darija)} paires Darija depuis atlasia.")

    # 2. Ajout des dialogues B2B Français / Darija (répétés pour équilibrer le fine-tuning)
    for _ in range(300):
        for user_q, agent_r in FRENCH_B2B_SAMPLES:
            formatted_records.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_q},
                    {"role": "assistant", "content": agent_r}
                ]
            })

    # 3. Mélange aléatoire et écriture dans le fichier JSONL final
    random.shuffle(formatted_records)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for record in formatted_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(f"✅ Fichier final généré avec succès dans : {OUTPUT_JSONL} ({len(formatted_records)} exemples au total).")
    return True

if __name__ == "__main__":
    format_dataset()
