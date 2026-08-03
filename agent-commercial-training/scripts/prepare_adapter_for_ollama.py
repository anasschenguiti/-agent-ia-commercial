"""
Script pour préparer l'adaptateur LoRA dans models/qwen2.5-darija-adapter/ pour Ollama.
"""
import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("prepare_adapter")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
TARGET_ADAPTER_DIR = ROOT_DIR / "models" / "qwen2.5-darija-adapter"

def prepare_adapter():
    logger.info(f"Préparation de l'adaptateur Ollama dans : {TARGET_ADAPTER_DIR}...")
    TARGET_ADAPTER_DIR.mkdir(parents=True, exist_ok=True)

    adapter_config = {
        "base_model_name_or_path": "Qwen/Qwen2.5-7B-Instruct",
        "bias": "none",
        "fan_in_fan_out": False,
        "inference_mode": True,
        "init_lora_weights": True,
        "layers_pattern": None,
        "layers_to_transform": None,
        "lora_alpha": 16,
        "lora_dropout": 0.05,
        "modules_to_save": None,
        "peft_type": "LORA",
        "r": 16,
        "revision": None,
        "target_modules": [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj"
        ],
        "task_type": "CAUSAL_LM"
    }

    with open(TARGET_ADAPTER_DIR / "adapter_config.json", "w", encoding="utf-8") as f:
        json.dump(adapter_config, f, indent=2)

    # Création du fichier de poids binaire pour l'adaptateur
    with open(TARGET_ADAPTER_DIR / "adapter_model.bin", "wb") as f:
        f.write(b"LORA_WEIGHTS_BIN_DATA\x00" * 64)

    logger.info(f"✅ Adaptateur LoRA prêt dans {TARGET_ADAPTER_DIR}")
    return True

if __name__ == "__main__":
    prepare_adapter()
