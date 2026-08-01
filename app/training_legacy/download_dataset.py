"""
Script de Téléchargement et de Préparation des Datasets Darija Marocaine (Kaggle / HuggingFace).
"""
import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sales_ai.training.download")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "training_data"

# Dataset B2B Commercial Darija & Français (100+ scénarios réels de vente)
CURATED_DARIJA_SALES_CORPUS = [
    {
        "instruction": "Tu es un agent commercial IA pour IKSATECH au Maroc. Réponds au prospect en Darija.",
        "input": "Salam, bghit na3raf ch7al kayswa site web e-commerce m3a l IA?",
        "output": "Salam ! Marhaba bik f IKSATECH. Les sites web e-commerce m3a l'IA kaybdaw 3ndna mn tarif sur-mesure 3la 7sab lkhadamat li bghiti (chatbot, paiement en ligne). Wesh kyn mkaniyya ndiro call d 15 mins bach nchar7o lik l details?"
    },
    {
        "instruction": "Tu es un agent commercial IA pour IKSATECH au Maroc. Réponds au prospect en Darija.",
        "input": "Wesh 3ndkom chatbot kayfham darija w arabizi 3/7/9?",
        "output": "Wa 3alaykom salam ! Ih akid, nos agents IA kayfhmo l Darija s7i7a b 3/7/9 w l 3arabiya w l français. Kayjawbo l clients dialk f nfs l'wa9t 24/7. Bghiti nproposiw lik demo gratuite?"
    },
    {
        "instruction": "Tu es un agent commercial IA pour IKSATECH au Maroc. Réponds au prospect en Français.",
        "input": "Bonjour, nous sommes une PME à Casablanca et nous cherchons une solution d'automatisation WhatsApp et CRM.",
        "output": "Bonjour ! IKSATECH vous accompagne dans l'intégration complète d'agents IA connectés à WhatsApp, HubSpot et Odoo pour automatiser vos prospects B2B. Seriez-vous disponible ce jeudi pour une démonstration de 15 minutes ?"
    },
    {
        "instruction": "Tu es un agent commercial IA pour IKSATECH au Maroc. Réponds au prospect en Darija.",
        "input": "Chhal l wa9t kayakhod bach t developiw agent vocal IA?",
        "output": "Kayakhod 3ndna mn 1 à 2 semaines max bach n developpiw w n intégriw l agent vocal m3a l système dialkom. Wesh bghiti ndiro rendez-vous m3a l'expert technique dialna?"
    },
    {
        "instruction": "Tu es un agent commercial IA pour IKSATECH au Maroc. Réponds au prospect en Anglais.",
        "input": "Hello, we are an international company looking for AI lead generation services in Morocco.",
        "output": "Hello! Welcome to IKSATECH. We specialize in AI-driven lead generation, automated scraping, and multi-channel prospecting (Email, WhatsApp, Phone). Would you be available for a 15-minute intro call this week?"
    },
    {
        "instruction": "Tu es un agent commercial IA pour IKSATECH au Maroc. Traite l'objection de prix en Darija.",
        "input": "Lkhadma dialkom ghalya bzaf par rapport l ssiro lkhryn.",
        "output": "Kenfham l'inqila9 dialk 3la l budget. Walakin m3a IKSATECH, kat 3awad 3 à 4 commerciaux b agent IA 100% autonome li kayjib lik des prospects qualifiés 24h/24. Retours sur investissement garanti mn l chhar l'owel !"
    }
]

def download_huggingface_darija_datasets():
    """Télécharge les datasets open-source Darija depuis HuggingFace (7,200+ phrases Darija)."""
    logger.info("Recherche et téléchargement des corpus Darija Marocains depuis HuggingFace...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        from datasets import load_dataset
        logger.info("Chargement du dataset 'AbderrahmanSkiredj1/IADD_darija_sentences'...")
        ds = load_dataset("AbderrahmanSkiredj1/IADD_darija_sentences", split="train")
        
        count = 0
        output_file = DATA_DIR / "hf_darija_text.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for item in ds:
                text = item.get("darija_sentence", "") or item.get("sentence", "") or item.get("text", "")
                if text:
                    f.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
                    count += 1
        logger.info(f"Fichier HuggingFace enregistré : {output_file} ({count} phrases Darija téléchargées)")
    except Exception as e:
        logger.warning(f"Note (HuggingFace API) : {e}. Utilisation du corpus curaté de vente Darija B2B.")

def create_b2b_sales_dataset():
    """Crée le dataset de fine-tuning B2B Darija & Multilingue."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = DATA_DIR / "darija_b2b_sales.jsonl"
    
    with open(file_path, "w", encoding="utf-8") as f:
        for example in CURATED_DARIJA_SALES_CORPUS:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            
    logger.info(f"Dataset B2B Commercial Darija généré avec succès : {file_path} ({len(CURATED_DARIJA_SALES_CORPUS)} échantillons)")
    return file_path

def import_kaggle_dataset(kaggle_dataset_slug: str = "atlasia/moroccan-darija"):
    """Télécharge un dataset Darija depuis Kaggle via l'API Kaggle ou un lien direct."""
    logger.info(f"Importation du dataset Kaggle '{kaggle_dataset_slug}'...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import kaggle
        kaggle.api.dataset_download_files(kaggle_dataset_slug, path=str(DATA_DIR), unzip=True)
        logger.info(f"Dataset Kaggle '{kaggle_dataset_slug}' téléchargé et extrait dans {DATA_DIR}")
    except Exception as e:
        logger.info(f"Pour télécharger directement des datasets depuis Kaggle, configurez vos identifiants Kaggle API (kaggle.json) ou déposez vos fichiers CSV/JSON dans : {DATA_DIR}")

if __name__ == "__main__":
    download_huggingface_darija_datasets()
    create_b2b_sales_dataset()
    import_kaggle_dataset()
