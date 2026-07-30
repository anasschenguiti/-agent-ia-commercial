"""
Tests unitaires pour le module d'authentification et les JWT.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from jose import jwt
from fastapi import HTTPException

from app.shared.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    settings,
    ALGORITHM
)
from app.shared.auth_router import login, register
from app.shared.models_sql import UserSQL


def test_password_hashing_and_verification():
    raw_pwd = "my-secret-password"
    hashed = hash_password(raw_pwd)
    
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_jwt_token_generation_and_decoding():
    payload = {"sub": "user_123", "email": "test@test.com"}
    token = create_access_token(payload)
    
    assert token is not None
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "user_123"
    assert decoded["email"] == "test@test.com"
    assert "exp" in decoded


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    payload = {"sub": "user_123", "email": "test@test.com"}
    token = create_access_token(payload)
    
    token_data = await get_current_user(token)
    assert token_data.user_id == "user_123"
    assert token_data.email == "test@test.com"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user("invalid-token-string")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_endpoint_success():
    # Mock database session
    mock_db = AsyncMock()
    
    # Simuler un utilisateur trouvé en base
    user = UserSQL(
        id="user_1",
        email="test@iksatech.com",
        hashed_password=hash_password("password123")
    )
    
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res
    
    payload = {"email": "test@iksatech.com", "password": "password123"}
    response = await login(payload, db=mock_db)
    
    assert "access_token" in response
    assert response["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_endpoint_wrong_password():
    mock_db = AsyncMock()
    
    user = UserSQL(
        id="user_1",
        email="test@iksatech.com",
        hashed_password=hash_password("password123")
    )
    
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_res
    
    payload = {"email": "test@iksatech.com", "password": "wrong-password"}
    with pytest.raises(HTTPException) as exc_info:
        await login(payload, db=mock_db)
    assert exc_info.value.status_code == 401
