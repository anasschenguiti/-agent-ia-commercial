"""
Routeur FastAPI pour l'authentification des utilisateurs.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.shared.database import get_db
from app.shared.models_sql import UserSQL
from app.shared.auth import hash_password, verify_password, create_access_token, Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    payload: dict,
    db: AsyncSession = Depends(get_db)
):
    """Connexion via JSON standard (utilisé par le Frontend)."""
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email et mot de passe requis"
        )

    stmt = select(UserSQL).where(UserSQL.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    token = create_access_token(data={"sub": user.id, "email": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Connexion standard OAuth2 (utilisé par Swagger/docs)."""
    stmt = select(UserSQL).where(UserSQL.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.id, "email": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: dict,
    db: AsyncSession = Depends(get_db)
):
    """Enregistre un nouvel utilisateur."""
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email et mot de passe requis"
        )

    stmt = select(UserSQL).where(UserSQL.email == email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà"
        )

    new_user = UserSQL(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=hash_password(password)
    )
    db.add(new_user)
    await db.commit()
    return {"message": "Utilisateur créé avec succès"}
