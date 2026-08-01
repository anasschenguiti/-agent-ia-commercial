# Dockerfile — Backend FastAPI & Celery Worker
# Week 1 : ajout d'un HEALTHCHECK. Week 5 installera libstdc++ pour Piper.
FROM python:3.11-slim

WORKDIR /app

# Dependances systeme de base
# - libstdc++ : requis par onnxruntime (Piper TTS, Week 5)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dependances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir python-multipart

# Copier le code source de l'application
COPY . .

# Exposer le port FastAPI
EXPOSE 8000

# Healthcheck (Week 1)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/live || exit 1

# Commande par defaut (FastAPI uvicorn)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
