# Dockerfile — Backend FastAPI & Celery Worker
FROM python:3.11-slim

WORKDIR /app

# Dépendances système de base
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir python-multipart

# Copier le code source de l'application
COPY . .

# Exposer le port FastAPI
EXPOSE 8000

# Commande par défaut (FastAPI uvicorn)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
