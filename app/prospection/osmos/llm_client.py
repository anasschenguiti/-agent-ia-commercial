"""
Client LLM unifié : Ollama (qwen3:8b) par défaut, OpenAI en fallback, Groq en option.
Adapté depuis OSMOS_lead_generation pour l'architecture FastAPI du projet.
"""
import os
import re
import requests
from typing import Optional


def call_llm(prompt: str, temperature: float = 0.0, timeout: float = 60.0) -> str:
    """
    Appelle le provider LLM configuré.
    Ordre de priorité :
    1. Ollama local (qwen3:8b) — par défaut si disponible
    2. OpenAI GPT-4o — si OPENAI_API_KEY est configuré et Ollama indisponible
    3. Groq — si LLM_PROVIDER=groq

    Retourne le texte brut de la réponse.
    Lève RuntimeError en cas d'échec.
    """
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()

    # --- Groq ---
    if provider == "groq":
        return _call_groq(prompt, temperature, timeout)

    # --- OpenAI explicite ---
    if provider == "openai":
        return _call_openai(prompt, temperature, timeout)

    # --- Ollama (défaut) avec fallback OpenAI ---
    try:
        return _call_ollama(prompt, temperature, timeout)
    except RuntimeError as ollama_err:
        # Fallback vers OpenAI si Ollama est indisponible
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key and not openai_key.startswith("sk-your"):
            try:
                return _call_openai(prompt, temperature, timeout)
            except RuntimeError as openai_err:
                raise RuntimeError(
                    f"Ollama indisponible ({ollama_err}) ET OpenAI a échoué ({openai_err})"
                )
        raise RuntimeError(
            f"Ollama indisponible : {ollama_err}. "
            "Configurez OPENAI_API_KEY dans .env pour utiliser OpenAI en fallback."
        )


def _call_ollama(prompt: str, temperature: float, timeout: float) -> str:
    """Appelle Ollama local (qwen3:8b)."""
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "system": "You are an ultra-fast B2B JSON API generator. Output ONLY a valid JSON structure. Do NOT output <think> tags or explanations.",
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1024},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Ollama n'est pas démarré (connexion refusée sur port 11434).")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Ollama a dépassé le timeout de {timeout}s.")
    except Exception as e:
        raise RuntimeError(f"Erreur Ollama : {e}")


def _call_openai(prompt: str, temperature: float, timeout: float) -> str:
    """Appelle OpenAI GPT-4o."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-your"):
        raise RuntimeError("OPENAI_API_KEY non configuré dans .env.")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"] or ""
    except Exception as e:
        raise RuntimeError(f"OpenAI inaccessible ou en erreur : {e}")


def _call_groq(prompt: str, temperature: float, timeout: float) -> str:
    """Appelle Groq."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    model = os.environ.get("GROQ_MODEL", "llama3-70b-8192")
    if not api_key:
        raise RuntimeError("LLM_PROVIDER=groq mais GROQ_API_KEY est manquant dans .env.")
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"] or ""
    except Exception as e:
        raise RuntimeError(f"Groq inaccessible ou en erreur : {e}")


def clean_json_block(text: str, bracket: str = "{") -> str:
    """
    Utilitaire partagé : retire les balises <think>...</think> et extrait
    le premier bloc JSON valide (objet ou tableau).
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    closing = "}" if bracket == "{" else "]"
    start_idx = text.find(bracket)
    if start_idx == -1:
        return ""
    depth = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] == bracket:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                end_idx = i
                break
    if end_idx == -1:
        return ""
    extracted = text[start_idx : end_idx + 1]
    extracted = re.sub(r",\s*}", "}", extracted)
    extracted = re.sub(r",\s*]", "]", extracted)
    return extracted
