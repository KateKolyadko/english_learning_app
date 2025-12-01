from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_tokens, verify_refresh_token, create_access_token
from app.schemas.user import Token, UserCreate, TokenRefresh
from app.services.user_service import UserService
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя + сразу выдача токенов
    """
    logger.info(f"Registration attempt for: {user_data.email}")
    try:
        user = UserService.create_user(db, user_data)
        logger.info(f"User registered successfully: {user_data.email}")
        
        tokens = create_tokens(user.email)
        logger.info(f"Tokens issued for new user: {user.email}")
        
        return tokens
    except Exception as e:
        logger.error(f"Registration failed for {user_data.email}: {str(e)}")
        raise

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Аутентификация и получение пары токенов
    """
    user = UserService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    tokens = create_tokens(user.email)
    logger.info(f"User logged in: {user.email}")
    
    return tokens

@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_data: TokenRefresh, 
    db: Session = Depends(get_db)
):
    """
    Обновление access токена с помощью refresh токена
    """
    try:
        payload = verify_refresh_token(refresh_data.refresh_token)
        email = payload.get("sub")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )

        tokens = create_tokens(user.email)
        logger.info(f"Tokens refreshed for user: {user.email}")
        
        return tokens
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.post("/logout")
def logout(
    refresh_token: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Выход из системы (можно расширить для blacklist токенов)
    Пока просто возвращаем успешный ответ
    """
    return {"message": "Successfully logged out"}