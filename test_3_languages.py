"""
Script de test d'inférence multilingue (Français, Anglais, Darija) sur l'endpoint /chat.
"""
import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

FASTAPI_URL = "http://localhost:8000/chat"

import time

test_prompts = [
    ("Français", "Bonjour, quelles sont vos offres commerciales pour la création d'un site web ?"),
    ("Anglais", "Hello, do you offer custom software and web development services for companies?"),
    ("Darija", "wach nta bikhir, bch7al site web f IKSATECH ?")
]

print("\n==================================================")
print("🧪 TEST D'INFÉRENCE ET DÉTECTION DE LANGUE EN DIRECT")
print("==================================================\n")

for i, (lang_label, prompt_text) in enumerate(test_prompts, 1):
    payload = {
        "message": prompt_text,
        "session_id": f"fresh_session_{lang_label}_{int(time.time())}_{i}"
    }

    req = urllib.request.Request(
        FASTAPI_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8")
    )

    try:
        res = urllib.request.urlopen(req)
        data = json.loads(res.read().decode("utf-8"))
        agent_response = data.get("response", "")

        print(f"--- TEST {i} : [{lang_label.upper()}] ---")
        print(f"👤 Message Utilisateur : \"{prompt_text}\"")
        print(f"🤖 Réponse Agent IA   : \"{agent_response}\"\n")
    except Exception as e:
        print(f"❌ Erreur lors du test {i} ({lang_label}) : {e}\n")

print("==================================================\n")
