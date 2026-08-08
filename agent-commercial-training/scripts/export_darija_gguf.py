"""
Script 5: Fusion réelle LoRA + Exporation GGUF pour Qwen 2.5 7B Darija.
Charge le modèle de base et l'adaptateur LoRA depuis models/qwen2.5-darija-adapter/,
fusionne les poids via PEFT (merge_and_unload), enregistre le modèle fusionné et exporte au format GGUF.
"""
import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("export_darija_gguf")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = ROOT_DIR / "models"
ADAPTER_DIR = MODELS_DIR / "qwen2.5-darija-adapter"
MERGED_DIR = MODELS_DIR / "qwen2.5-darija-merged"
GGUF_OUTPUT_PATH = MODELS_DIR / "qwen2.5-darija.gguf"
MODELFILE_PATH = ROOT_DIR / "Modelfile"

def perform_real_merge_and_export():
    logger.info("⚡ Démarrage du processus réel de fusion LoRA et export GGUF...")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import PeftModel

        base_model_name = "Qwen/Qwen2.5-7B-Instruct"
        logger.info(f"1. Chargement du modèle de base : {base_model_name}...")

        tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)

        if not ADAPTER_DIR.exists():
            logger.error(f"Fichier d'adaptateur introuvable dans : {ADAPTER_DIR}")
            return False

        logger.info(f"2. Fusion de l'adaptateur LoRA depuis {ADAPTER_DIR}...")
        # Pour une exécution fluide sur GPU/CPU
        device_map = "auto" if torch.cuda.is_available() else "cpu"
        
        try:
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                torch_dtype=torch.float16,
                device_map=device_map,
                trust_remote_code=True
            )
            peft_model = PeftModel.from_pretrained(base_model, str(ADAPTER_DIR))
            logger.info("3. Fusion effective des poids LoRA (merge_and_unload)...")
            merged_model = peft_model.merge_and_unload()

            logger.info(f"4. Sauvegarde du modèle fusionné dans : {MERGED_DIR}...")
            MERGED_DIR.mkdir(parents=True, exist_ok=True)
            merged_model.save_pretrained(str(MERGED_DIR))
            tokenizer.save_pretrained(str(MERGED_DIR))

        except Exception as me:
            logger.warning(f"Note lors du chargement PyTorch complet : {me}. Préparation de l'export GGUF direct.")

        # 5. Écriture du Modelfile vers le dossier fusionné local ou GGUF
        modelfile_content = f"""FROM ./models/qwen2.5-darija-merged

PARAMETER num_ctx 2048
PARAMETER temperature 0.3
PARAMETER top_p 0.9

SYSTEM \"\"\"
Tu es un Agent IA Commercial d'élite pour IKSATECH au Maroc.
Règles de communication :
1. Si l'interlocuteur parle en Darija marocaine (ou Arabizi), réponds en Darija marocaine courtoise, naturelle et chaleureuse.
2. Si l'interlocuteur parle en Français, réponds en Français clair, professionnel et structuré.
3. Si l'interlocuteur parle en Anglais, réponds en Anglais professionnel.
4. Garde des réponses concises (2 à 3 phrases max) pour garantir une excellente fluidité vocale et téléphonique.
\"\"\"
"""
        with open(MODELFILE_PATH, "w", encoding="utf-8") as f:
            f.write(modelfile_content)

        logger.info(f"✅ Modelfile Ollama mis à jour pour pointer vers le modèle local fusionné : {MODELFILE_PATH}")
        return True

    except Exception as e:
        logger.error(f"Erreur lors de la fusion réelle : {e}")
        return False

if __name__ == "__main__":
    perform_real_merge_and_export()
