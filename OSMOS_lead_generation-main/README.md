# 🌐 Web Automation Hub

An intelligent, local, text-only web accessibility agent designed to plan and execute browser-based tasks. Powered by **browser-use**, **Ollama (`qwen3:8b`)**, and **Playwright**, the Hub provides an intuitive, rich Web UI and a Command-Line Interface (CLI) to automate tasks with robust human-in-the-loop assistance.

---

## 🌟 Key Architecture: The Skill Library

The Web Automation Hub uses a modern, modular **Skill-based Prompt Architecture** rather than a monolithic prompt. The agent's knowledge, behavior, constraints, and macros are split into logical files inside the `skills/` directory. These files are dynamically loaded and concatenated at runtime by the `skills/loader.py` utility.

### Skill Modules:
- **`system.md`**: Core system persona, operating boundaries, retry thresholds, and formatting instructions.
- **`linkedin.md`**: Specific knowledge, page routes, selectors, buttons, and login/navigation rules.
- **`navigation.md`**: Rules for safe web navigation, URL validation, and scroll boundaries.
- **`interaction.md`**: Details on how the agent executes page interactions and how it must prioritize and structure calls to custom **macros** (e.g., custom actions).
- **`verification.md`**: Constraints on verifying action success to prevent infinite loops (like clicking the "Like" button repeatedly and toggling it off).
- **`examples.md`**: Contextual examples of successful step planning and execution.

> [!TIP]
> *To update the agent's behavior, refine the respective markdown file in the `skills/` directory. No changes to the codebase are required.*

---

## 🛡️ Key Reinforcements & Protections

### 1. Direct Login Routing & Form Protection
- **Targeted Navigation**: Enforces direct routing to `https://www.linkedin.com/login` instead of the bare homepage (`https://www.linkedin.com`).
- **Registration Protection**: Explicitly forbids entering credentials into "Join now", "Sign up", or other registration cards. If the agent lands on the main landing page, it is instructed to locate and click the "Sign in" button in the top right header first.

### 2. Live Frontend Results Visualizer
- **Real-Time Rendering**: The Web UI features a premium **Extracted Content & Results** panel.
- **Dynamic Updates**: As the agent performs extraction steps, the collected data is pushed to the UI in real-time.
- **Outcome Summary**: Highlights the final extracted summary or outcome upon success.

### 3. Dynamic Port Conflict Failover
- **Safe Binding**: The server automatically searches for available ports starting at `8000` (up to `8100`) to guarantee successful launches without port contention issues.

### 4. Interactive Human-In-The-Loop (HITL)
- **Assistance Modal**: The agent pauses and opens an interactive modal to request guidance for 2FA, CAPTCHA, or when hitting consecutive step failures.

---

## 🛠️ Supported Automation & Macros

The agent supports the following native automated macros for LinkedIn to bypass complex visual steps:
1. **Login**: Automatically signs in using provided credentials without registration-page confusion.
2. **Like Post**: Calls custom element targeting and state-checking to securely like a post.
3. **Follow / Connect**: Initiates connection requests or follows target profiles.
4. **Comment Post**: Safely navigates and posts comments.
5. **Like Comment**: Reacts to specific comments on posts.
6. **Send Message**: Navigates to messaging and delivers customized messages.

---

## 🚀 Getting Started

### Requirements
- **Python**: version 3.12
- **Ollama**: Installed locally with the `qwen3:8b` model pulled (`ollama run qwen3:8b`).
- **System Libraries**: Playwright requires standard browser dependencies (e.g., GTK, GStreamer). If missing, run `playwright install-deps` inside your activated environment.

### Installation & Quick Setup
You can use the automatic setup script on Linux:

```bash
# 1. Setup environment and install dependencies
chmod +x setup.sh
./setup.sh

# 2. Activate virtual environment
source .venv/bin/activate
```

Alternatively, you can perform a manual installation:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

---

## 💻 How to Run

### 1. Web Dashboard (Interactive)
The Web UI provides a visual execution log, live state updates, an editable planning step-by-step list, and human-in-the-loop confirmations for 2FA or CAPTCHA.

```bash
# Activate environment
source .venv/bin/activate

# Run the web server
python3 app.py
```
Open the printed URL (typically **`http://localhost:8000`**) in your browser. (If port 8000 is occupied, it will automatically bind to the next available port up to 8100).

### 2. Command Line Interface (CLI Mode)
If you prefer to run automation directly via the terminal:

```bash
# Activate environment
source .venv/bin/activate

# Run CLI mode
python3 actions.py
```
This mode lets you enter prompts manually, reviews and edits the execution plan step-by-step, and prompts for confirmation in the terminal.

---

## ⚙️ Configuration & Safeguards

The project enforces strict limits to optimize LLM inference and prevent infinite execution loops:
- **LLM Model**: `qwen3:8b` via local Ollama.
- **Browser Locale**: `locale=en-US` is explicitly applied to the browser context to prevent input errors on foreign-language (e.g., Arabic) LinkedIn login forms, ensuring the agent always correctly identifies email and password fields.
- **DOM Capping**: Retains the beginning and end of large accessibility trees up to 12,000 characters to fit inside context windows.
- **Execution Limits**: Hard-capped at 60 steps per task.
- **Dedicated Chrome Profile**: Uses `chrome_profile/` to maintain session cookies locally (keeping you logged into LinkedIn between runs).

---

## 🔒 Security Practices

- **No Hardcoded Credentials**: Passwords and usernames are fed directly via runtime prompts or UI text inputs.
- **Data Protection**: Do not check in `chrome_profile/` or share the log files (`server.log`), as they may contain session cookies.
- **Local Logs**: Runtime logging is automatically directed to `server.log` inside the project root rather than global directories.

---

## 🏗️ État du Projet
**Brique 3/N** — Extraction et classement 100% réels via AHP et TOPSIS.
Aucune donnée simulée n'est utilisée. En cas d'échec du Hub (timeout, captcha, blocage), le système affiche une erreur explicite à l'utilisateur plutôt qu'un résultat de substitution fictif.

**Brique 4/N** — Génération de persona commercial via Ollama en appel direct.
Cette brique ne navigue pas sur le web et n'utilise pas le Hub. Elle effectue un appel direct à l'API locale d'Ollama (`qwen3:8b`) pour générer une identité commerciale stricte au format JSON. Elle est indépendante de la stabilité de l'actionneur.

**Brique 5/N** — Plan d'action et contenus rédigés via Ollama en appel direct.
Cette brique génère une séquence de prospection sur 3 semaines (6 étapes) et rédige des brouillons (Post, Commentaire, DM) ultra-personnalisés. Tout est fait via l'API locale d'Ollama (`qwen3:8b`), 100% indépendant du Hub et sans aucune navigation web.

**Brique 6/N** — Exécution réelle des actions planifiées via le Hub.
Contrairement aux Briques 4 et 5, cette étape dépend entièrement de la stabilité de l'actionneur. Elle lance l'agent sur LinkedIn (like, comment, connect, message) via `HubClient`. Aucun succès n'est jamais affiché sans une confirmation réelle (Expected Result) retournée par le Hub. L'intervention humaine (CAPTCHA, etc.) est gérée via un formulaire direct dans l'interface.

## Basculer entre Ollama et Groq (Test)

Ollama reste le provider par défaut et validé pour ce projet (via `qwen3:8b`). Cependant, une option de test avec Groq est disponible.
Pour utiliser Groq, il suffit d'ajouter/modifier les variables d'environnement suivantes dans votre fichier `.env` à la racine de `web-actions-qwen` :

```env
LLM_PROVIDER=groq
GROQ_API_KEY=votre_cle_api_groq
GROQ_MODEL=llama3-70b-8192
```

Si `LLM_PROVIDER` est absent, invalide, ou configuré sur `ollama`, le Hub reviendra automatiquement sur l'utilisation locale.
La configuration du navigateur (notamment `locale="en-US"`) est 100% découplée du LLM et reste rigoureusement active dans tous les cas. **Groq est une option de test, à valider avant de l'utiliser pour la démo finale.**
