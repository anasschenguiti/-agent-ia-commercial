"""
Script 1: Téléchargement du Dataset Darija (atlasia/darija_english).
Télécharge les paires Darija-English depuis HuggingFace et enregistre le fichier brut dans data/raw/darija_english.json
"""
import os
import json
import logging
from pathlib import Path
from datasets import load_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("download_darija")

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
OUTPUT_FILE = RAW_DATA_DIR / "darija_english.json"

def download_darija_dataset():
    logger.info("Début du téléchargement du dataset atlasia/darija_english...")
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    configs = ['web_data', 'comments', 'stories', 'doda', 'transliteration']
    data_list = []

    for cfg in configs:
        try:
            logger.info(f"Téléchargement de la sous-configuration '{cfg}'...")
            ds = load_dataset("atlasia/darija_english", cfg, split="train")
            for item in ds:
                data_list.append({
                    "darija": item.get("darija", "").strip(),
                    "english": item.get("english", "").strip(),
                    "config": cfg
                })
        except Exception as e:
            logger.warning(f"Erreur lors du téléchargement de {cfg} : {e}")

    if data_list:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)

        logger.info(f"Dataset brut sauvegardé dans : {OUTPUT_FILE} ({len(data_list)} entrées au total)")
        return True
    else:
        logger.error("Aucune donnée n'a pu être téléchargée.")
        return False

if __name__ == "__main__":
    download_darija_dataset()
