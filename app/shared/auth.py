"""
Authentification et autorisation via JWT.

Week 1: alignement sur settings.SECRET_KEY (SecretStr).
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.shared.config import settings

# ── Configuration ────────────────────────────────────────────────────
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = "user"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Fonctions utilitaires ─────────────────────────────────────────────

def _secret() -> str:
    """Retourne la valeur brute du SECRET_KEY (Pydantic SecretStr)."""
    return settings.SECRET_KEY.get_secret_value()


def hash_password(password: str) -> str:
    """Hache un mot de passe avec PBKDF2-SHA256."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifie un mot de passe contre son hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Genere un JWT d'acces."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _secret(), algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Dependance FastAPI : valide le JWT et retourne les donnees utilisateur."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role", "user")
        if user_id is None:
            raise credentials_exception
        return TokenData(user_id=user_id, email=email, role=role)
    except JWTError:
        raise credentials_exception


async def get_current_admin(
    current: TokenData = Depends(get_current_user),
) -> TokenData:
    """Dependance FastAPI : reservee aux administrateurs."""
    if current.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privileges administrateur requis",
        )
    return current
