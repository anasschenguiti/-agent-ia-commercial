import os
import json
import requests
import re
from typing import Dict, Any

from .hub_client import HubClient, HubHumanInterventionRequired, HubConnectionError
from .llm_client import call_llm

def clean_json(text: str) -> str:
    """Removes <think>...</think> tags and attempts to extract a JSON object from text."""
    # Remove <think>...</think> completely
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Try to find JSON structure by brace depth
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
        # Clean up trailing commas
        extracted = re.sub(r',\s*}', '}', extracted)
        extracted = re.sub(r',\s*]', ']', extracted)
        return extracted
    return ""

def call_ollama(prompt: str) -> str:
    """Calls the configured LLM provider (Ollama by default, or Groq via LLM_PROVIDER=groq)."""
    try:
        return call_llm(prompt, temperature=0.1)
    except RuntimeError as e:
        print(f"[LLM Error] {e}")
        return ""

def parse_with_ollama(raw_text: str, retry: bool = False) -> Dict[str, Any]:
    """Uses Ollama to parse raw text into JSON."""
    format_instructions = (
        "You must return ONLY a strict JSON object with EXACTLY these 5 keys: "
        "'sector', 'size', 'description', 'value_proposition', 'linkedin_url'. "
        "Do not include markdown blocks, just the JSON string."
    )
    if retry:
        format_instructions += " PREVIOUS ATTEMPT FAILED. YOU MUST ONLY RETURN VALID JSON NO OTHER TEXT."
        
    prompt = f"Extract the following company information into JSON:\n\n{raw_text}\n\n{format_instructions}"
    
    result = call_ollama(prompt)
    if not result:
        raise ValueError("Ollama returned empty response.")
        
    cleaned = clean_json(result)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        if not retry:
            return parse_with_ollama(raw_text, retry=True)
        raise ValueError(f"Failed to parse JSON after retry: {e}")

def get_fallback_dict(reason: str) -> Dict[str, str]:
    """Returns a safe fallback dict and logs the reason."""
    print(f"⚠️ [FALLBACK UTILISÉ] Raison: {reason}")
    return {
        "sector": "Non déterminé (Fallback)",
        "size": "Inconnue (Fallback)",
        "description": f"Extraction indisponible. Raison : {reason}",
        "value_proposition": "Impossible de déterminer la proposition de valeur.",
        "linkedin_url": "https://linkedin.com/company/fallback"
    }

def extract_company_info(company_name: str, hub_client: HubClient, use_real_actionneur: bool, linkedin_email: str = None, linkedin_password: str = None) -> dict:
    if not use_real_actionneur:
        return get_fallback_dict("use_real_actionneur=False (Mode Simulé)")
        
    if not linkedin_email or not linkedin_password:
        return get_fallback_dict("Credentials LinkedIn requis pour l'extraction réelle")
        
    try:
        # 1. Ask Hub to generate a plan
        prompt = f"1. Log into LinkedIn ({linkedin_email} / {linkedin_password}). 2. Call the search_linkedin_company macro with company_name='{company_name}'. 3. Extract: sector, size, description, value proposition, URL."
        steps = hub_client.generate_plan(prompt)
        
        # 2. Run agent
        hub_client.run_agent(prompt, steps)
        
        # 3. Wait for completion
        status = hub_client.wait_for_completion(timeout=600.0)
        
        if status.get("error"):
            return get_fallback_dict(f"Erreur du Hub: {status['error']}")
            
        # The content should be in final_result or extracted_content
        raw_text = status.get("final_result") or status.get("extracted_content", "")
        if not raw_text:
            return get_fallback_dict("Le Hub n'a retourné aucun contenu exploitable.")
            
        if isinstance(raw_text, list):
            raw_text = "\n".join(str(item) for item in raw_text)
            
        # 4. Use Ollama to parse
        try:
            parsed_json = parse_with_ollama(raw_text)
            # Ensure keys exist
            for key in ["sector", "size", "description", "value_proposition", "linkedin_url"]:
                if key not in parsed_json:
                    parsed_json[key] = "Non renseigné"
            return parsed_json
        except Exception as e:
            return get_fallback_dict(f"Erreur parsing Ollama: {str(e)}")
            
    except HubHumanInterventionRequired as e:
        return get_fallback_dict(f"Intervention humaine requise: {str(e)}")
    except HubConnectionError as e:
        return get_fallback_dict(f"Erreur de connexion au Hub: {str(e)}")
    except Exception as e:
        return get_fallback_dict(f"Erreur inattendue: {str(e)}")
