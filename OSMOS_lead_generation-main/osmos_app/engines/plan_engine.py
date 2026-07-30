import json
import re
from .llm_client import call_llm

class PlanGenerationError(Exception):
    pass

class ContentGenerationError(Exception):
    pass

def clean_json_dict(text: str) -> str:
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    start_idx = text.find('{')
    if start_idx == -1: return ""
    depth = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
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

def _call_ollama(prompt: str, exception_cls: type) -> dict:
    try:
        result_text = call_llm(prompt, temperature=0.7, timeout=90.0)
    except RuntimeError as e:
        raise exception_cls(f"Le modèle LLM a échoué : {e}")

    cleaned = clean_json_dict(result_text)
    if not cleaned:
        raise exception_cls("Aucun JSON valide trouvé dans la réponse.")
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise exception_cls("Le JSON retourné n'est pas un dictionnaire.")
        return parsed
    except json.JSONDecodeError as e:
        raise exception_cls(f"JSON mal formé : {e}")

def generate_action_plan(campaign, persona: dict, prospect: dict) -> dict:
    base_prompt = f"""
You are an expert B2B sales strategist. Create a 6-step nurturing plan over 3 weeks for your target prospect.
Your Persona: {persona.get('full_name')} ({persona.get('role')}) - {persona.get('work_style')}
Target Prospect: {prospect.get('contact_name') or prospect.get('name')} ({prospect.get('contact_title', 'Decision Maker')}) at {prospect.get('name')} in {prospect.get('sector')}

You MUST return ONLY a strict JSON object with EXACTLY one key "steps", which is an array of exactly 6 objects.
Each object must have:
- "day": integer (e.g., 1, 4, 7, 12, 16, 21)
- "action_type": string (must be exactly one of: "like", "comment", "connect", "message", "post", "dm")
- "rationale": string (why we do this step now)

Return ONLY valid JSON starting with {{ and ending with }}. No markdown, no <think>.
"""
    try:
        return _call_ollama(base_prompt, PlanGenerationError)
    except PlanGenerationError as e:
        stricter_prompt = f"Previous attempt failed. {e}\n\n{base_prompt}\nCRITICAL: Output ONLY valid JSON."
        try:
            return _call_ollama(stricter_prompt, PlanGenerationError)
        except PlanGenerationError as e2:
            raise PlanGenerationError(f"Échec après 2 tentatives : {e2}")

def generate_content(campaign, persona: dict, prospect: dict, action_plan: dict) -> dict:
    target_name = prospect.get('contact_name') or prospect.get('name')
    base_prompt = f"""
You are {persona.get('full_name')}, {persona.get('role')} at {campaign.company_name}.
Your value proposition: {campaign.value_proposition}.
Your target prospect is {target_name} ({prospect.get('contact_title', '')}).

Write 3 pieces of content for your LinkedIn strategy in strict JSON format:
1. "post_text": A full LinkedIn post sharing an industry insight relevant to your sector.
2. "short_comment": A 1-2 sentence insightful comment to leave on the prospect's recent post.
3. "direct_message": A concise, non-salesy LinkedIn DM (under 400 chars) to initiate conversation after they accepted your connection request. If greeting them by name, use their actual name "{target_name}" directly.

CRITICAL: These must read as finished, ready-to-send messages, not templates. NEVER use placeholder tokens of any kind — no "[name]", "[First Name]", "[Company]", "{{name}}", "<name>", or similar brackets/braces anywhere in the text. Always write out the real name/company ("{target_name}", "{campaign.company_name}") directly, or omit a name-based greeting entirely if it reads better without one. A human reading this must not be able to tell it came from a template.

You MUST return ONLY a strict JSON object with EXACTLY the keys: "post_text", "short_comment", "direct_message".
All values must be strings. Return ONLY valid JSON. No markdown, no <think>.
"""
    def _find_placeholder(content: dict) -> str | None:
        placeholder_pattern = re.compile(r'\[[a-zA-Z_ ]{2,30}\]|\{[a-zA-Z_ ]{2,30}\}|<[a-zA-Z_ ]{2,30}>')
        for field in ("post_text", "short_comment", "direct_message"):
            match = placeholder_pattern.search(str(content.get(field, "")))
            if match:
                return f"{field} contains a template placeholder: '{match.group(0)}'"
        return None

    try:
        content = _call_ollama(base_prompt, ContentGenerationError)
        issue = _find_placeholder(content)
        if issue:
            raise ContentGenerationError(issue)
        return content
    except ContentGenerationError as e:
        stricter_prompt = (
            f"Previous attempt failed: {e}\n\n{base_prompt}\n"
            "CRITICAL: Output ONLY valid JSON, and make absolutely sure none of the text fields contain "
            f"template placeholders — write out \"{target_name}\" and \"{campaign.company_name}\" literally."
        )
        try:
            content = _call_ollama(stricter_prompt, ContentGenerationError)
            issue = _find_placeholder(content)
            if issue:
                raise ContentGenerationError(issue)
            return content
        except ContentGenerationError as e2:
            raise ContentGenerationError(f"Échec de rédaction après 2 tentatives : {e2}")
