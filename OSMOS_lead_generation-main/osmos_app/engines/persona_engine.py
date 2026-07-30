import json
import re
from .llm_client import call_llm

class PersonaGenerationError(Exception):
    """Exception levée quand Ollama échoue à générer un persona valide."""
    pass

def clean_json_dict(text: str) -> str:
    """Nettoie le texte et extrait le premier dictionnaire JSON valide."""
    # Retirer les balises <think> générées par certains modèles (ex: qwen3)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    start_idx = text.find('{')
    if start_idx == -1:
        return ""
        
    depth = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end_idx = i
                break
                
    if end_idx != -1:
        extracted = text[start_idx:end_idx+1]
        # Corriger les virgules de fin avant la fermeture de l'accolade/crochet
        extracted = re.sub(r',\s*}', '}', extracted)
        extracted = re.sub(r',\s*]', ']', extracted)
        return extracted
    return ""

def _call_ollama(prompt: str) -> dict:
    try:
        result_text = call_llm(prompt, temperature=0.7, timeout=90.0)
    except RuntimeError as e:
        raise PersonaGenerationError(f"Le modèle LLM est injoignable ou a échoué : {e}")

    cleaned = clean_json_dict(result_text)
    if not cleaned:
        raise PersonaGenerationError("Le modèle n'a pas retourné de JSON valide (aucune accolade trouvée).")
        
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise PersonaGenerationError("Le JSON retourné n'est pas un dictionnaire.")
        return parsed
    except json.JSONDecodeError as e:
        raise PersonaGenerationError(f"Le JSON retourné est mal formé : {e}\nTexte extrait: {cleaned[:100]}...")

def generate_persona(campaign, prospects: list) -> dict:
    """
    Appel direct à Ollama pour générer un persona commercial virtuel sans utiliser le Hub.
    """
    # Préparer le contexte
    prospects_summary = "\n".join([f"- {p.get('name', 'Inconnu')} ({p.get('sector', 'Inconnu')} - {p.get('size', 'Inconnu')})" for p in prospects[:3]])
    
    base_prompt = f"""
You are an expert B2B sales strategist. Create a highly credible virtual sales persona for a campaign targeting the '{campaign.company_sector}' sector in MOROCCO.
CRITICAL REQUIREMENT: The persona MUST be of Moroccan nationality and MUST have a realistic Moroccan name (e.g., Youssef, Amine, Mehdi, Fatima, Yasmine, etc., along with a typical Moroccan last name).
This persona works for '{campaign.company_name}', whose value proposition is: "{campaign.value_proposition}".
They will be targeting companies like:
{prospects_summary}

You MUST return ONLY a strict JSON object with EXACTLY these keys:
- "full_name": string (a realistic Moroccan first and last name)
- "headline": string (a catchy LinkedIn headline)
- "role": string (job title)
- "seniority": string (e.g., "Senior", "Director", "Lead")
- "age": integer
- "bio": string (a 2-3 sentence professional summary)
- "work_style": string (how they approach sales and clients)
- "key_skills": array of strings (3-5 core skills)
- "past_projects": array of objects, each with "title" (string) and "quantifiable_result" (string)

Return ONLY the JSON, starting with {{ and ending with }}. No markdown, no <think> blocks, no introductory text.
"""

    try:
        return _call_ollama(base_prompt)
    except PersonaGenerationError as e:
        # Retry with a stricter prompt
        stricter_prompt = f"Previous JSON parsing failed. {e}\n\n{base_prompt}\n\nCRITICAL: Output ONLY valid JSON."
        try:
            return _call_ollama(stricter_prompt)
        except PersonaGenerationError as e2:
            raise PersonaGenerationError(f"Échec de la génération du persona après 2 tentatives. {e2}")
