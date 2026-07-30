from engines.hub_client import HubClient

def execute_planned_action(prospect_dict: dict, plan_step: dict, content_dict: dict, hub_client: HubClient) -> dict:
    """
    Exécute une action planifiée via le HubClient de façon asynchrone (lancement).
    Retourne un dict d'état initial.
    """
    action_type = plan_step.get("action_type", "").lower()
    target_name = prospect_dict.get("contact_name") or prospect_dict.get("name")
    company_name = prospect_dict.get("name")
    
    # Construction du prompt selon le type d'action
    if action_type == "like":
        prompt = f"Find the LinkedIn profile of {target_name} at {company_name}. Find their most recent post and click the Like button."
    elif action_type == "comment":
        comment_text = content_dict.get("short_comment", "Great insights!")
        prompt = f"Find the LinkedIn profile of {target_name} at {company_name}. Find their most recent post and leave this exact comment: '{comment_text}'"
    elif action_type == "connect":
        prompt = f"Find the LinkedIn profile of {target_name} at {company_name}. Click the Connect button to send a connection request."
    elif action_type in ["message", "dm"]:
        message_text = content_dict.get("direct_message", "Hello")
        prompt = f"Go to LinkedIn messaging. Start a conversation with {target_name} at {company_name} and send this exact message: '{message_text}'"
    elif action_type == "post":
        post_text = content_dict.get("post_text", "Sharing some thoughts on the industry.")
        prompt = f"Go to your LinkedIn home feed. Create a new post with this exact text and publish it: '{post_text}'"
    else:
        prompt = f"Find {target_name} at {company_name} on LinkedIn and interact with their profile."

    # Génération du plan par l'agent Hub
    try:
        steps = hub_client.generate_plan(prompt)
    except Exception as e:
        return {
            "status": "failed",
            "result_detail": f"Erreur lors de la génération du plan par le Hub : {e}",
            "human_question": None
        }

    # Lancement de l'agent
    try:
        hub_client.run_agent(prompt, steps)
        # On ne bloque pas à attendre la fin ici dans le Web thread, on va utiliser poll_action_status dans la route
        # Wait, pour simplifier la Brique 6 sans workers asynchrones complexes (Celery), 
        # on peut bloquer l'appel pendant max 60s, ou faire le polling côté serveur.
        # Le Hub est de toute façon fait pour être requêté via status.
        # On va juste attendre le retour complet ici puisque la consigne dit "utilise generate_plan -> run_agent -> wait_for_completion".
        status_info = hub_client.wait_for_completion(timeout=300.0) # Attente max 5 min

        # Le Hub (app.py) n'expose pas de clé "status" dans /status : il expose
        # "success" (bool), "error" (str|None) et "waiting_for_help" (bool). On mappe
        # sur ces champs réels plutôt que sur une clé qui n'a jamais existé côté Hub.
        if status_info.get("waiting_for_help"):
            question = status_info.get("help_question") or "Intervention humaine requise (ex: CAPTCHA)."
            return {
                "status": "needs_human_help",
                "result_detail": "Le Hub est bloqué et attend une réponse humaine.",
                "human_question": question
            }
        elif status_info.get("success"):
            return {
                "status": "success",
                "result_detail": "Action exécutée avec succès par le Hub.",
                "human_question": None
            }
        else:
            error_msg = status_info.get("error") or "L'action a échoué (cible non trouvée ou erreur technique)."
            return {
                "status": "failed",
                "result_detail": f"Échec : {error_msg}",
                "human_question": None
            }
            
    except Exception as e:
        return {
            "status": "failed",
            "result_detail": f"Exception lors de l'exécution du Hub : {e}",
            "human_question": None
        }
