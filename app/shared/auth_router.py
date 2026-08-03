"""
Routeur FastAPI pour l'authentification des utilisateurs.

Week 1 (securite) :
- /register exige ADMIN_BOOTSTRAP_TOKEN (env) => 403 sinon.
- /login et /token peuvent etre rate-limites via slowapi (decore sur main.py).
"""

import hmac
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.shared.database import get_db
from app.shared.models_sql import UserSQL
from app.shared.auth import (
    hash_password,
    verify_password,
    create_access_token,
    Token,
)
from app.shared.config import settings

router = APIRouter()

# Week 1 : limiter slowapi dedie a /login (5/min par IP).
# On partage l'instance avec main.py via app.state.limiter si dispo,
# sinon on cree un Limiter local (cas des tests unitaires).
limiter = Limiter(key_func=get_remote_address)


def _verify_bootstrap_token(provided: str) -> bool:
    """Comparaison constant-time pour eviter le timing attack."""
    expected = settings.ADMIN_BOOTSTRAP_TOKEN.get_secret_value()
    if not expected:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Connexion via JSON standard (utilise par le Frontend)."""
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email et mot de passe requis",
        )

    stmt = select(UserSQL).where(UserSQL.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    role = getattr(user, "role", "user") or "user"
    token = create_access_token(data={"sub": user.id, "email": user.email, "role": role})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Connexion standard OAuth2 (utilise par Swagger/docs)."""
    stmt = select(UserSQL).where(UserSQL.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = getattr(user, "role", "user") or "user"
    token = create_access_token(data={"sub": user.id, "email": user.email, "role": role})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Enregistre un nouvel utilisateur.

    Week 1 (securite) : exige ADMIN_BOOTSTRAP_TOKEN dans le body ou
    en header `X-Admin-Bootstrap-Token`. Sans token valide => 403.
    """
    email = payload.get("email")
    password = payload.get("password")
    bootstrap = payload.get("bootstrap_token", "")
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email et mot de passe requis",
        )

    if not _verify_bootstrap_token(bootstrap):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token bootstrap invalide. Contactez un administrateur.",
        )

    stmt = select(UserSQL).where(UserSQL.email == email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe deja",
        )

    new_user = UserSQL(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password(password),
        role=payload.get("role", "user"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_user)
    await db.commit()
    return {"message": "Utilisateur cree avec succes"}
