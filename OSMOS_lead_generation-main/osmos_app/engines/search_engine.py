import json
import re
from typing import List, Dict, Any
from .hub_client import HubClient, HubHumanInterventionRequired, HubConnectionError
from .llm_client import call_llm

class ExtractionError(Exception):
    """Exception levée quand le Hub échoue à extraire des prospects réels."""
    pass

def clean_json_list(text: str) -> str:
    """Extrait une liste JSON du texte brut."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    start_idx = text.find('[')
    if start_idx == -1:
        return ""
    
    depth = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                end_idx = i
                break
                
    if end_idx != -1:
        extracted = text[start_idx:end_idx+1]
        extracted = re.sub(r',\s*}', '}', extracted)
        extracted = re.sub(r',\s*]', ']', extracted)
        return extracted
    return ""

def parse_prospects_with_ollama(raw_text: str) -> List[Dict[str, Any]]:
    prompt = (
        "You are an expert data extractor. Extract the list of companies and their decision-maker contacts from the following text.\n"
        "You MUST return ONLY a valid JSON array of objects. Each object MUST have EXACTLY these keys:\n"
        "- 'name': string (Company name)\n"
        "- 'sector': string\n"
        "- 'size': string\n"
        "- 'linkedin_url': string (Company URL)\n"
        "- 'contact_name': string or null (Name of the decision-maker. Must be null if no qualified contact is found)\n"
        "- 'contact_title': string or null\n"
        "- 'contact_seniority': string or null\n"
        "- 'contact_linkedin_url': string or null\n"
        "- 'recent_activity_signal': string or null\n"
        "- 'no_qualified_contact_found': boolean (true if no decision-maker was found, false otherwise)\n"
        "- 'sector_fit': integer (1 to 10)\n"
        "- 'size_score': integer (1 to 10)\n"
        "- 'accessibility': integer (1 to 10 - score based on the contact's seniority and reachability)\n"
        "- 'recent_activity': integer (1 to 10)\n\n"
        f"Text to parse:\n{raw_text}\n\n"
        "Return ONLY the JSON array (starting with '[' and ending with ']'), no markdown, no explanation."
    )
    
    try:
        result_text = call_llm(prompt, temperature=0.0)
    except RuntimeError as e:
        raise ExtractionError(f"Le parsing LLM a échoué : {e}")

    cleaned = clean_json_list(result_text)
    if not cleaned:
        raise ExtractionError("Le modèle n'a pas retourné un JSON valide contenant les prospects.")
        
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, list):
            raise ExtractionError("Le JSON retourné n'est pas une liste.")
        if len(parsed) == 0:
            raise ExtractionError("Le JSON retourné est vide (aucune entreprise trouvée).")
            
        return parsed
    except json.JSONDecodeError as e:
        raise ExtractionError(f"Le JSON retourné est mal formé : {e}")

def find_prospects_for_campaign(campaign, hub_client: HubClient) -> List[Dict[str, Any]]:
    """
    Pilote le Hub pour chercher de réels prospects sur LinkedIn liés à la campagne.
    Ne retourne QUE des prospects réels avec leurs contacts qualifiés. Lève ExtractionError en cas de problème.
    """
    prompt = (
        f"1. Search LinkedIn for companies in the '{campaign.company_sector}' sector, similar to '{campaign.company_name}'.\n"
        f"2. For each of up to 5 companies found, identify a specific decision-maker or influencer contact (e.g., Director, VP, Head of, Senior Manager, Founder, C-level). DO NOT extract junior, intern, or unrelated administrative roles.\n"
        f"3. Extract the company details (name, sector, size, LinkedIn URL) AND the contact details (name, exact title, visible seniority, individual LinkedIn URL, and any recent activity signal like a post or job change).\n"
        f"4. Estimate 4 scores out of 10 for the company/contact: sector_fit, size_score, accessibility (based on contact seniority), recent_activity.\n"
        f"5. If no qualified decision-maker is found for a company, state clearly that no qualified contact was found.\n"
        f"Return the data."
    )
    
    try:
        steps = hub_client.generate_plan(prompt)
        hub_client.run_agent(prompt, steps)
        status = hub_client.wait_for_completion(timeout=600.0)
        
        if status.get("error"):
            raise ExtractionError(f"Erreur d'exécution du Hub : {status['error']}")
            
        raw_text = status.get("extracted_content") or status.get("final_result", "")
        if not raw_text:
            raise ExtractionError("L'agent n'a rien extrait depuis LinkedIn.")
            
        prospects = parse_prospects_with_ollama(raw_text)
        return prospects
        
    except HubHumanInterventionRequired as e:
        raise ExtractionError(f"Intervention humaine requise, extraction annulée : {e.question}")
    except HubConnectionError as e:
        raise ExtractionError("Le Hub est injoignable. Assurez-vous qu'il est bien démarré.")
    except Exception as e:
        if isinstance(e, ExtractionError):
            raise
        raise ExtractionError(f"Erreur inattendue lors de l'extraction : {str(e)}")
