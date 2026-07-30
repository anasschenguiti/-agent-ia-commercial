# OSMOS App - Brique 2

Brique 2/N — extraction réelle avec fallback sécurisé, jamais de crash même si le Hub échoue.

## Structure

Cette brique implémente la logique d'extraction intelligente d'une entreprise :
- `engines/llm_engine.py` : Logique de communication avec le Hub d'automatisation, extraction, parsing JSON via Ollama et mécanisme de Fallback.
- `engines/hub_client.py` : Client HTTP pour interagir avec le Hub (copié depuis `cerveau/hub_client/client.py`).

## Comment lancer le projet

1. **Installer les dépendances** :
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

2. **Démarrer l'application** :
   Depuis la racine `web-actions-qwen` :
   \`\`\`bash
   python3 osmos_app/app.py
   \`\`\`
   *(L'application écoute sur http://127.0.0.1:5000)*

## Comment tester les deux modes

L'application possède deux modes, contrôlés par la variable d'environnement `USE_REAL_ACTIONNEUR` dans le fichier `.env` :

### 1. Mode Simulé (Par défaut)
- Assurez-vous que `.env` contient `USE_REAL_ACTIONNEUR=false`.
- Soumettez le formulaire sur la page d'accueil.
- Un message bleu "Mode simulé" apparaîtra et des données de démonstration seront instantanément affichées sur la page d'analyse, *sans faire appel ni au Hub ni à Ollama*.

### 2. Mode Réel (Actionneur Hub)
- Modifiez `.env` pour mettre `USE_REAL_ACTIONNEUR=true` et redémarrez Flask.
- Assurez-vous que le **Hub d'automatisation** tourne sur le port `8000`.
- Assurez-vous qu'**Ollama** tourne avec le modèle `qwen3:8b`.
- Soumettez le formulaire sur la page d'accueil.
- L'application appellera le Hub pour extraire les informations LinkedIn et Ollama pour parser le JSON.
- **Sécurité (Fallback)** : Si le Hub est éteint, s'il rencontre une erreur, si une intervention humaine est requise, ou si Ollama est injoignable, **l'application ne crashera pas**. Un fallback silencieux (mais tracé dans la console Flask) prendra le relais et vous affichera les données de démonstration avec un avertissement jaune sur l'interface.
