# 🤖 Sales AI Agent — Agent IA Commercial Intelligent

> **Projet de Fin d'Études / Stage réalisé chez IKSATECH**  
> **Statut du Projet :** 🟢 **100% Complété & Validé** (30/30 Tests Pytest Réussis)

L'**Sales AI Agent** est une solution logicielle complète d'intelligence artificielle conçue pour automatiser l'intégralité des tâches d'un *Business Development Representative (BDR)* / Commercial : prospection ciblée, qualification de leads, conversation intelligente avec gestion des objections, prise de rendez-vous, relances automatiques et synchronisation CRM — disponible 24h/24 et 7j/7.

---

## 📌 Sommaire

- [État Actuel du Projet](#-état-actuel-du-projet)
- [Fonctionnalités](#-fonctionnalités)
- [Stack Technique & Architecture](#-stack-technique--architecture)
- [Identifiants d'Accès par Défaut](#-identifiants-daccès-par-défaut)
- [Guide de Démarrage et d'Exécution](#-guide-de-démarrage-et-dexécution)
  - [1. Lancement Local (Backend + Frontend)](#1-lancement-local-backend--frontend)
  - [2. Lancement Conteneurisé (Docker Compose)](#2-lancement-conteneurisé-docker-compose)
- [Exécution des Tests](#-exécution-des-tests)
- [Guide Git : Pousser le Projet sur GitHub](#-guide-git--pousser-le-projet-sur-github)
- [Documentation API](#-documentation-api)

---

## 📊 État Actuel du Projet

- **Avancement :** **100% Fonctionnel** — Tous les modules backend et l'interface utilisateur frontend sont intégrés.
- **Couverture de Tests :** **30/30 tests réussis** (`pytest app/tests/ -v`).
- **Mode Réel & Simulation :**
  - **Emails** : Envoi réel via `SMTP` (Google/SendGrid) si configuré dans `.env`, sinon fallback gracieux.
  - **WhatsApp** : Intégration réelle API **Meta Cloud v18.0** (`WhatsAppClient`).
  - **LinkedIn** : Intégration réelle API **LinkedIn RESTli v2** (`LinkedInClient`).
  - **CRMs** : Connecteurs réels **HubSpot v3 API** et **Odoo JSON-RPC API**.
  - **Agendas** : Connecteurs créneaux et réservations **Google Calendar / Outlook API**.

---

## 🚀 Fonctionnalités

1. **Prospection Intelligente (Scraping & Localisation)** :
   - Recherche personnalisée par mots-clés et par ville (*Tanger*, *Casablanca*, *Paris*, *Londres*, etc.).
   - Bouton de **réinitialisation/nettoyage** de la base de données en un clic.
2. **Scoring & Qualification IA** :
   - Algorithme de scoring qualifiant automatiquement les prospects (`Hot` $\ge 80$, `Warm` $50-79$, `Cold` $<50$).
3. **Agent Conversationnel RAG & Objections** :
   - Traitement contextuel des objections (*Prix*, *Timing*, *Concurrence*) via LangChain & Qdrant.
   - Interface de discussion interactive en temps réel.
4. **Prise de Rendez-vous Automatisée** :
   - Recherche de créneaux libres et réservation instantanée compatible Google Calendar et Outlook.
5. **Synchronisation CRM Bidirectionnelle** :
   - Envoi des prospects qualifiés et mise à jour des étapes de transactions sur **HubSpot** et **Odoo**.
6. **Relances Automatiques (J0, J3, J7, J15)** :
   - Suivi temporel automatisé et **Simulateur Temporel** (`+3 jours`, `+7 jours`, `+15 jours`) sur le Dashboard.
   - Tâches d'arrière-plan automatisées avec **Celery** & **Redis**.
7. **Gestion des Templates & Canaux Multicanaux** :
   - Éditeur visuel de templates de messages (Email, WhatsApp, LinkedIn) avec variables dynamiques (`{first_name}`, `{company}`, `{job_title}`, `{score}`) et test d'envoi en direct.
8. **Analytics Avancés & Export CSV** :
   - Calcul des taux de conversion, score moyen et **bouton d'exportation CSV instantané**.
9. **Sécurité & Authentification JWT** :
   - Portail de connexion (Login) stylisé en verre dépoli (Glassmorphic UI).
   - Authentification par jeton `Bearer JWT` et hachage sécurisé `PBKDF2`.
   - Seeding automatique du compte administrateur.

---

## 🛠️ Stack Technique & Architecture

### Stack Logicielle
- **Backend** : Python 3.11+, FastAPI, SQLAlchemy (Async AsyncPG), Pydantic v2, Passlib, Celery.
- **Frontend** : React, Next.js (Turbopack), Tailwind CSS.
- **Bases de Données** : PostgreSQL 16 (données métier), Qdrant (base vectorielle RAG), Redis 7 (cache & broker).
- **Conteneurisation** : Docker & Docker Compose.

### Structure du Répertoire
```text
-agent-ia-commercial-main/
├── app/                        # Backend FastAPI
│   ├── communication/          # Templates & Clients (Email, WhatsApp, LinkedIn)
│   ├── conversation/           # Agent conversationnel RAG, LangGraph, Objections
│   ├── crm/                    # Connecteurs HubSpot v3 & Odoo JSON-RPC
│   ├── prospection/            # Scraping, scoring, relances J0-J15, export CSV
│   ├── scheduling/             # Créneaux & Réservations (Calendar)
│   ├── shared/                 # Config, BDD PostgreSQL, Auth JWT, Redis
│   ├── tasks/                  # Workers & Tâches asynchrones Celery
│   ├── tests/                  # Suite de 30 tests unitaires & d'intégration
│   └── main.py                 # Point d'entrée de l'application FastAPI
├── frontend/                   # Interface Utilisateur Next.js
│   ├── src/app/                # Code source React (page.js, layout.js, globals.css)
│   ├── Dockerfile              # Containerisation Frontend
│   └── package.json            # Configuration npm
├── Dockerfile                  # Containerisation Backend FastAPI & Celery
├── docker-compose.yml          # Orchestration complète des microservices
├── requirements.txt            # Dépendances Python
└── README.md                   # Documentation du projet
```

---

## 🔑 Identifiants d'Accès par Défaut

Au premier démarrage, un compte administrateur est automatiquement généré en base de données :

| Rôle | Email | Mot de passe |
| :--- | :--- | :--- |
| **Administrateur** | `admin@iksatech.com` | `admin` |

---

## 💻 Guide de Démarrage et d'Exécution

### 1. Lancement Local (Backend + Frontend)

#### **A. Lancer le Backend (FastAPI)**

##### Sur Windows (PowerShell) :
```powershell
# 1. Créer l'environnement virtuel
python -m venv venv

# 2. Activer l'environnement virtuel
.\venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer le serveur backend FastAPI
uvicorn app.main:app --reload
```

##### Sur Linux / macOS (Bash) :
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

*Le Backend démarrera sur **http://localhost:8000**.*

---

#### **B. Lancer le Frontend (Next.js)**

Dans un **deuxième terminal** :

```bash
cd frontend
npm install
npm run dev
```

*Le Dashboard démarrera sur **http://localhost:3000**.*

---

### 2. Lancement Conteneurisé (Docker Compose)

Pour exécuter l'ensemble des services en un seul clic (`PostgreSQL`, `Redis`, `Qdrant`, `FastAPI Backend`, `Celery Worker`, `Next.js Frontend`) :

```bash
docker-compose up --build -d
```

---

## 🧪 Exécution des Tests

Pour exécuter la suite complète des **30 tests unitaires et d'intégration** :

```powershell
# Windows
.\venv\Scripts\python -m pytest app/tests/ -v

# Linux / macOS
pytest app/tests/ -v
```

---

## 🐙 Guide Git : Pousser le Projet sur GitHub

Voici les commandes étape par étape pour sauvegarder et publier le projet complet sur votre dépôt GitHub :

```bash
# 1. Vérifier l'état des fichiers
git status

# 2. Ajouter tous les fichiers modifiés et nouveaux au staging
git add .

# 3. Créer le commit avec un message descriptif
git commit -m "feat: Sales AI Agent 100% complete - Auth JWT, Templates, Relances Celery, Export CSV, Docker & 30 tests"

# 4. Vérifier la branche courante (main ou master)
git branch

# 5. Pousser le code vers GitHub
git push origin main
```
*(Si votre branche principale s'appelle `master`, utilisez `git push origin master`)*.

---

## 📖 Documentation API

Une fois le backend lancé, accédez à la documentation interactive Swagger :

- **Swagger UI** : [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc** : [http://localhost:8000/redoc](http://localhost:8000/redoc)
