# 🤖 Agent IA Commercial IKSATECH — Voice + WhatsApp + Multilingue

> **Projet réalisé chez IKSATECH — Maroc**  
> **Statut :** 🟢 **100% Opérationnel** — Voix Trilingue (Darija 🇲🇦 | Français 🇫🇷 | Anglais 🇬🇧) + WhatsApp Intégré

Un **Agent Commercial IA complet** qui automatise les tâches d'un *Business Development Representative (BDR)* : prospection, conversations intelligentes par texte et par **voix**, détection des objections, prise de rendez-vous et synchronisation CRM — disponible **24h/24 sur WhatsApp et sur le Web**.

---

## 📌 Sommaire

- [Fonctionnalités](#-fonctionnalités)
- [Architecture & Stack Technique](#-architecture--stack-technique)
- [Guide de Démarrage Rapide](#-guide-de-démarrage-rapide)
  - [1. Backend FastAPI (Python)](#1-backend-fastapi-python)
  - [2. Frontend Next.js (Dashboard)](#2-frontend-nextjs-dashboard)
  - [3. Pont WhatsApp (Node.js)](#3-pont-whatsapp-nodejs)
  - [4. Modèle IA Local (Ollama)](#4-modèle-ia-local-ollama)
- [Commandes de Lancement](#-commandes-de-lancement)
- [Variables d'Environnement (.env)](#-variables-denvironnement-env)
- [Identifiants par Défaut](#-identifiants-par-défaut)
- [Documentation API](#-documentation-api)
- [Guide Git](#-guide-git)

---

## 🚀 Fonctionnalités

### 🎙️ Agent Vocal Trilingue
- **Détection automatique de la langue** : Darija marocaine (Arabizi + caractères arabes), Français, Anglais
- **Transcription vocale** : `faster-whisper` (offline, rapide, gratuit)
- **Synthèse vocale adaptée par langue** via **Microsoft Edge-TTS** :
  - 🇲🇦 Darija : `ar-MA-MounaNeural` (voix féminine marocaine)
  - 🇫🇷 Français : `fr-FR-VivienneMultilingualNeural`
  - 🇬🇧 Anglais : `en-US-AriaNeural` (voix chaleureuse et naturelle)
- **Conversation naturelle** : répond aux salutations normalement ET présente IKSATECH commercialement

### 📲 Intégration WhatsApp Complète
- **Messages texte** : réception + réponse automatique intelligente
- **Notes vocales (PTT)** : téléchargement, transcription et réponse vocale
- **Support comptes @lid** : patch spécifique pour les nouveaux identifiants WhatsApp
- **Multilangue WhatsApp** : détection de langue et réponse adaptée

### 🤖 Agent Commercial IA
- **LLM Local** : `qwen2.5:7b-instruct` via **Ollama** (100% offline, sans coût API)
- **RAG (Retrieval-Augmented Generation)** : Qdrant pour la base de connaissances IKSATECH
- **Gestion des objections** : Prix, Timing, Concurrence
- **Historique conversationnel** : mémoire de session persistante (SQLite)
- **Prise de rendez-vous** : Google Calendar & Outlook

### 📊 Dashboard Web (Next.js)
- Interface moderne avec **glassmorphism** et animations
- Prospection intelligente (scraping par ville & mots-clés)
- Scoring IA des prospects (`Hot` ≥ 80, `Warm` 50-79, `Cold` < 50)
- Templates multicanaux (Email, WhatsApp, LinkedIn)
- Analytics & Export CSV
- Authentification JWT sécurisée

### 🔗 Intégrations
- **CRM** : HubSpot v3 API + Odoo JSON-RPC
- **Email** : SMTP (Google / SendGrid)
- **LinkedIn** : LinkedIn RESTli v2
- **Calendriers** : Google Calendar / Outlook

---

## 🛠️ Architecture & Stack Technique

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT IA COMMERCIAL                          │
│                                                                   │
│  📲 WhatsApp Web        🌐 Dashboard Web                         │
│  (whatsapp-bridge/)     (frontend/ - Next.js)                    │
│         │                        │                               │
│         └────────────┬───────────┘                               │
│                      │ HTTP REST                                  │
│              ┌───────▼────────┐                                  │
│              │  FastAPI :8000  │                                  │
│              │  (app/main.py)  │                                  │
│              └───────┬────────┘                                  │
│           ┌──────────┼──────────┐                                │
│           ▼          ▼          ▼                                 │
│      🎙️ Voice    🤖 Agent    📊 Prospect                         │
│      STT/TTS    LangGraph    Scraping                            │
│    (Whisper +  (Qwen2.5 +  (Live Scraper)                       │
│    Edge-TTS)    Ollama)                                          │
│           │          │                                            │
│           └──────────┼──────────┐                                │
│                      ▼          ▼                                 │
│                  🗄️ SQLite   📚 Qdrant                           │
│                  (sessions)  (RAG vectors)                        │
└─────────────────────────────────────────────────────────────────┘
```

### Stack Logicielle

| Couche | Technologies |
|--------|-------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, Pydantic v2 |
| **LLM** | Ollama + `qwen2.5:7b-instruct` (Local, Offline) |
| **STT** | `faster-whisper` (Transcription locale) |
| **TTS** | Microsoft Edge-TTS (`ar-MA-MounaNeural`, `fr-FR-VivienneMultilingualNeural`, `en-US-AriaNeural`) |
| **RAG** | LangChain + Qdrant |
| **WhatsApp** | `whatsapp-web.js` v1.34.7 (Node.js 25) + Puppeteer |
| **Frontend** | React 18, Next.js 14, Tailwind CSS |
| **Base de données** | SQLite (local) / PostgreSQL (production) |
| **CRM** | HubSpot v3 + Odoo JSON-RPC |
| **Conteneurs** | Docker & Docker Compose |

### Structure du Répertoire

```
-agent-ia-commercial-ai-agent-voice/
├── app/                          # Backend FastAPI
│   ├── conversation/             # Agent LangGraph + RAG + Détection Objections
│   │   ├── agent.py              # Agent principal (détection langue, LLM, prompts)
│   │   ├── rag.py                # Pipeline RAG Qdrant
│   │   ├── memory.py             # Mémoire de session
│   │   └── objection_handler.py  # Gestionnaire d'objections
│   ├── voice/                    # Pipeline Vocal Complet
│   │   ├── router.py             # Endpoints /voice/interact, /voice/config
│   │   ├── agent_voice.py        # Orchestrateur STT → LLM → TTS
│   │   ├── stt.py                # Transcription (faster-whisper)
│   │   └── tts.py                # Synthèse vocale multilingue (Edge-TTS)
│   ├── communication/            # Email, WhatsApp Meta, LinkedIn
│   ├── crm/                      # HubSpot + Odoo connecteurs
│   ├── prospection/              # Scraping, Scoring IA, Relances
│   ├── scheduling/               # Google Calendar / Outlook
│   ├── shared/                   # Config, Auth JWT, Sécurité
│   └── main.py                   # Point d'entrée FastAPI + endpoint /chat
├── whatsapp-bridge/              # Pont WhatsApp (Node.js)
│   ├── index.js                  # Bridge WhatsApp Web.js (texte + PTT + patch @lid)
│   └── package.json              # Dépendances Node.js
├── frontend/                     # Dashboard Next.js
│   └── src/app/                  # Composants React
├── agent-commercial-training/    # Fine-tuning du modèle Darija (Qwen2.5)
│   └── scripts/                  # Scripts préparation dataset Darija
├── Modelfile                     # Configuration Ollama (qwen2.5-darija)
├── docker-compose.yml            # Orchestration complète
├── requirements.txt              # Dépendances Python
└── .env.example                  # Variables d'environnement (template)
```

---

## 💻 Guide de Démarrage Rapide

### Prérequis

- **Python** 3.11+
- **Node.js** 25+
- **Ollama** installé et en cours d'exécution
- **npm** 10+

### 1. Backend FastAPI (Python)

```powershell
# Windows PowerShell — depuis la racine du projet

# 1. Créer l'environnement virtuel
python -m venv venv

# 2. Activer l'environnement virtuel
.\\venv\\Scripts\\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Copier et configurer les variables d'environnement
copy .env.example .env
# Éditez .env selon vos besoins

# 5. Lancer le serveur backend
.\\venv\\Scripts\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> 🌐 Backend disponible sur **http://localhost:8000**

### 2. Frontend Next.js (Dashboard)

Dans un **deuxième terminal** :

```powershell
cd frontend
npm install
npm run dev
```

> 🌐 Dashboard disponible sur **http://localhost:3000**

### 3. Pont WhatsApp (Node.js)

Dans un **troisième terminal** :

```powershell
cd whatsapp-bridge
npm install
node index.js
```

Un **QR Code** s'affiche dans le terminal. Scannez-le avec WhatsApp :
- Ouvrez WhatsApp sur votre téléphone
- Allez dans **Paramètres → Appareils connectés → Connecter un appareil**
- Scannez le QR Code

> ✅ Une fois connecté : l'agent répond automatiquement aux messages texte et notes vocales

**Pour arrêter et relancer le pont :**
```powershell
# Stopper Chrome bloquant la session et relancer
Stop-Process -Name "chrome" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
node index.js
```

### 4. Modèle IA Local (Ollama)

```powershell
# Installer Ollama (une seule fois)
# Télécharger depuis https://ollama.com/download

# Télécharger le modèle de base
ollama pull qwen2.5:7b-instruct

# Créer le modèle Darija personnalisé IKSATECH
ollama create qwen2.5-darija -f Modelfile

# Vérifier que le modèle est disponible
ollama list
```

---

## ⚡ Commandes de Lancement

### Démarrage Complet (3 terminaux)

| Terminal | Commande | URL |
|----------|----------|-----|
| **1 — Backend** | `.\\venv\\Scripts\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000` | http://localhost:8000 |
| **2 — Frontend** | `cd frontend && npm run dev` | http://localhost:3000 |
| **3 — WhatsApp** | `cd whatsapp-bridge && node index.js` | (QR Code terminal) |

### Docker Compose (tout en un)

```bash
docker-compose up --build -d
```

---

## 🔧 Variables d'Environnement (.env)

Copiez `.env.example` vers `.env` et configurez :

```bash
# LLM — Choisir "ollama" (local gratuit) ou "openai"
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5-darija
OLLAMA_BASE_URL=http://localhost:11434/v1

# Base de données
DATABASE_URL=sqlite:///./sales_db.sqlite

# Sécurité JWT
SECRET_KEY=votre_clé_secrète_ici

# TTS (Voix Edge-TTS)
TTS_VOICE_DARIJA=ar-MA-MounaNeural
TTS_VOICE_FRENCH=fr-FR-VivienneMultilingualNeural
TTS_FALLBACK_ORDER=edge_tts,gtts,piper

# CRM (optionnel)
HUBSPOT_API_KEY=your_hubspot_key
ODOO_URL=https://your-odoo-instance.com

# Calendrier (optionnel)
GOOGLE_CALENDAR_CREDENTIALS_JSON=...
```

---

## 🔑 Identifiants par Défaut

Au premier démarrage, un compte administrateur est automatiquement créé :

| Rôle | Email | Mot de passe |
|------|-------|-------------|
| **Administrateur** | `admin@iksatech.com` | `admin` |

---

## 🧪 Exécution des Tests

```powershell
# Windows
.\\venv\\Scripts\\python -m pytest app/tests/ -v

# Test trilingual (Darija / Français / Anglais)
.\\venv\\Scripts\\python test_3_languages.py
```

---

## 📖 Documentation API

Une fois le backend lancé :

- **Swagger UI** : [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc** : [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Endpoints Principaux

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/chat` | Message texte → Réponse IA (WhatsApp Bridge) |
| `POST` | `/api/v1/voice/interact` | Fichier audio → Transcription + Réponse IA + Audio |
| `GET` | `/api/v1/voice/config` | Configuration vocale active |
| `POST` | `/api/v1/auth/login` | Authentification JWT |
| `GET` | `/api/v1/prospects/` | Liste des prospects |
| `POST` | `/api/v1/prospects/scrape` | Lancer le scraping |

---

## ⚠️ Notes Techniques Importantes

### Patch WhatsApp @lid (Comptes Récents)
Les nouveaux comptes WhatsApp utilisent le format d'identifiant `@lid`. Le pont WhatsApp inclut un patch spécifique dans `whatsapp-web.js` qui :
- Récupère l'ID sérialisé depuis la propriété `$1` du message
- Permet le téléchargement correct des notes vocales sur ces comptes

Ce patch est appliqué automatiquement dans `node_modules/whatsapp-web.js/src/structures/Message.js` au démarrage.

### Modèle Darija (qwen2.5-darija)
Le modèle est fine-tuné via Ollama avec un `Modelfile` qui injecte un système de règles trilingues :
- Réponse strictement en Darija marocaine si le message est en Darija
- Réponse en Français ou Anglais selon la langue détectée

### Détection de Langue
L'agent utilise une détection à 4 niveaux :
1. **Caractères arabes** → Darija marocaine
2. **Mots-clés Arabizi** (`wach`, `bghit`, `labas`, etc.) → Darija marocaine
3. **langdetect** → `en` / `fr` / `ar`
4. **Mots-clés fallback** anglais → Anglais

---

## 🐙 Guide Git

```bash
git add .
git commit -m "feat: Agent IA Commercial - Voice trilingue + WhatsApp PTT + patch @lid + Edge-TTS Aria/Mouna/Vivienne"
git push origin main
```

---

## 📞 Contact & Support

**IKSATECH** — Solutions Numériques & Intelligence Artificielle au Maroc  
Sites web sur-mesure | Agents IA | Chatbots WhatsApp | Applications Mobile  
💰 À partir de **4 900 DH**

---

*Agent IA Commercial — Propulsé par Ollama (qwen2.5) + FastAPI + Next.js + whatsapp-web.js*
