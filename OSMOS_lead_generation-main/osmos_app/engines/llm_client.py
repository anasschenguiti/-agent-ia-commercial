import os
import requests

def call_llm(prompt: str, temperature: float = 0.0, timeout: float = 60.0) -> str:
    """Calls the LLM provider configured via LLM_PROVIDER (ollama by default, or groq),
    mirroring the switch already used by the Hub's actions.py. Returns the raw text
    response. Raises RuntimeError on failure; callers translate that into their own
    domain-specific exceptions."""
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()

    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY", "")
        model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
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

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3:8b",
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        raise RuntimeError(f"Ollama inaccessible ou en erreur : {e}")
