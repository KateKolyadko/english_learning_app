from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.user import Token, UserCreate, UserResponse
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя
    """
    logger.info(f"Registration attempt for: {user_data.email}")
    try:
        result = UserService.create_user(db, user_data)
        logger.info(f"User registered successfully: {user_data.email}")
        return result
    except Exception as e:
        logger.error(f"Registration failed for {user_data.email}: {str(e)}")
        raise

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Аутентификация пользователя и получение JWT токена
    """
    user = UserService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}