"""
Processor Master pour les Datasets Darija Déposés par l'Utilisateur (1.7 GB+).
Analyse les Parquets DODa, les fichiers CSV (train.csv, translation_data, grammar, tasks) et XLSX.
"""
import os
import json
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sales_ai.training.user_data")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "training_data"
DODA_DIR = DATA_DIR / "DODa" / "data"
OUTPUT_MASTER = DATA_DIR / "darija_master_corpus.jsonl"

def process_csv_and_vocab_files():
    """Traite l'ensemble des fichiers CSV de vocabulaire, grammaire et tâches Darija."""
    logger.info("Extraction des données à partir des 50+ fichiers CSV et XLSX...")
    extracted_text = []
    
    csv_files = list(DATA_DIR.glob("*.csv"))
    for csv_file in csv_files:
        try:
            logger.info(f"Lecture du fichier : {csv_file.name}...")
            # Limite les très grands CSV à 20 000 lignes pour des performances optimales
            df = pd.read_csv(csv_file, nrows=20000, on_bad_lines='skip', low_memory=False)
            
            # Recherche automatique des colonnes textuelles (darija, text, sentence, prompt, response)
            text_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["darija", "text", "sentence", "prompt", "arabic", "response", "input", "output"])]
            
            for _, row in df.iterrows():
                for col in text_cols:
                    val = str(row[col]).strip()
                    if val and val.lower() != "nan" and len(val) > 2:
                        extracted_text.append(val)
        except Exception as e:
            logger.warning(f"Erreur de lecture sur {csv_file.name} : {e}")
            
    logger.info(f"Total phrases extraites des CSVs : {len(extracted_text)}")
    return extracted_text

def process_doda_parquet_files():
    """Traite les fichiers Parquet massifs du dataset DODa (1.28 GB)."""
    logger.info("Traitement du dataset massif DODa (1.28 GB de fichiers Parquet)...")
    extracted_text = []
    
    if not DODA_DIR.exists():
        logger.warning(f"Dossier DODa non trouvé dans {DODA_DIR}")
        return []
        
    parquet_files = list(DODA_DIR.glob("*.parquet"))
    for pfile in parquet_files:
        try:
            logger.info(f"Lecture du fichier Parquet DODa : {pfile.name}...")
            df = pd.read_parquet(pfile)
            text_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["darija", "text", "sentence", "arabic", "word"])]
            
            # Prendre un échantillon représentatif de 15 000 entrées par fichier
            sample_df = df.sample(min(15000, len(df)), random_state=42) if len(df) > 15000 else df
            
            for _, row in sample_df.iterrows():
                for col in text_cols:
                    val = str(row[col]).strip()
                    if val and val.lower() != "nan" and len(val) > 2:
                        extracted_text.append(val)
        except Exception as e:
            logger.warning(f"Erreur de lecture sur {pfile.name} : {e}")
            
    logger.info(f"Total éléments extraits de DODa : {len(extracted_text)}")
    return extracted_text

def build_master_corpus():
    """Combine toutes les sources de données utilisateur dans darija_master_corpus.jsonl."""
    logger.info("--- Assemblage du Master Corpus Darija Haute de Gamme ---")
    
    csv_texts = process_csv_and_vocab_files()
    doda_texts = process_doda_parquet_files()
    
    all_texts = set(csv_texts + doda_texts)
    
    logger.info(f"Nettoyage et dédoublonnage : {len(all_texts)} phrases et règles uniques obtenues.")
    
    count = 0
    with open(OUTPUT_MASTER, "w", encoding="utf-8") as f:
        for t in all_texts:
            f.write(json.dumps({"text": t}, ensure_ascii=False) + "\n")
            count += 1
            
    logger.info(f"🚀 Master Corpus Darija créé avec succès : {OUTPUT_MASTER} ({count} échantillons réels)")
    return OUTPUT_MASTER, count

if __name__ == "__main__":
    build_master_corpus()
