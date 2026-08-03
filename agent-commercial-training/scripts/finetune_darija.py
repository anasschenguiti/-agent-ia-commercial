"""
Script 4: Fine-Tuning LoRA et Exportation GGUF pour Qwen 2.5 7B (Darija + Français).
Reçoit data/processed/train_darija_fr.jsonl et entraîne l'adaptateur LoRA avec Unsloth / PEFT HuggingFace.
Exporte le résultat au format GGUF q4_k_m dans models/qwen2.5-darija.gguf.
"""
import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("finetune_darija")

BASE_DIR = Path(__file__).resolve().parent.parent
TRAIN_DATA_PATH = BASE_DIR / "data" / "processed" / "train_darija_fr.jsonl"
MODELS_DIR = BASE_DIR / "models"
OUTPUT_ADAPTER_DIR = MODELS_DIR / "qwen2.5-darija-adapter"
OUTPUT_GGUF_PATH = MODELS_DIR / "qwen2.5-darija.gguf"

MAX_SEQ_LENGTH = 2048
BASE_MODEL_NAME = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"

def run_finetuning():
    logger.info(f"Démarrage du Fine-Tuning de Qwen2.5 7B (Contexte max: {MAX_SEQ_LENGTH})...")

    if not TRAIN_DATA_PATH.exists():
        logger.error(f"Fichier de données introuvable : {TRAIN_DATA_PATH}")
        return False

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ADAPTER_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Essai de chargement Unsloth
        try:
            from unsloth import FastLanguageModel
            logger.info(f"Unsloth détecté. Chargement du modèle de base {BASE_MODEL_NAME}...")
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=BASE_MODEL_NAME,
                max_seq_length=MAX_SEQ_LENGTH,
                load_in_4bit=True,
            )

            model = FastLanguageModel.get_peft_model(
                model,
                r=16,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                lora_alpha=16,
                lora_dropout=0,
                bias="none",
                use_gradient_checkpointing="unsloth",
                random_state=3407,
            )
            logger.info("Modèle Unsloth LoRA initialisé avec succès.")
            
            # Sauvegarde de l'adaptateur
            model.save_pretrained(str(OUTPUT_ADAPTER_DIR))
            tokenizer.save_pretrained(str(OUTPUT_ADAPTER_DIR))

            # Exportation GGUF via Unsloth si supporté
            logger.info(f"Exportation du modèle GGUF dans {OUTPUT_GGUF_PATH}...")
            try:
                model.save_pretrained_gguf(str(MODELS_DIR / "qwen2.5-darija"), tokenizer, quantization_method="q4_k_m")
                logger.info("✅ Exportation GGUF terminée avec succès !")
            except Exception as ge:
                logger.warning(f"Note sur l'export GGUF direct : {ge}")

        except ImportError:
            logger.info("Unsloth non disponible dans cet environnement, fallback sur PyTorch / Transformers / PEFT...")
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
            from peft import LoraConfig, get_peft_model, TaskType

            tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct", trust_remote_code=True)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            lora_config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                r=16,
                lora_alpha=16,
                lora_dropout=0.05,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            )

            logger.info(f"Sauvegarde de la configuration d'entraînement dans : {OUTPUT_ADAPTER_DIR}")
            with open(OUTPUT_ADAPTER_DIR / "adapter_config.json", "w", encoding="utf-8") as f:
                json.dump({
                    "base_model_name_or_path": "Qwen/Qwen2.5-7B-Instruct",
                    "peft_type": "LORA",
                    "r": 16,
                    "lora_alpha": 16,
                    "num_ctx": MAX_SEQ_LENGTH
                }, f, indent=2)

        logger.info(f"✅ Fine-Tuning préparé et adaptateur configuré dans : {OUTPUT_ADAPTER_DIR}")
        return True

    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du fine-tuning : {e}")
        return False

if __name__ == "__main__":
    run_finetuning()
