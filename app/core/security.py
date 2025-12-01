from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import settings
from typing import Dict

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Безопасная проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Безопасное хеширование пароля с валидацией"""
    # Валидация пароля
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 128:
        raise ValueError("Password must be less than 128 characters")
    
    # BCrypt автоматически обрезает до 72 байт
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Создание JWT токена"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise ValueError(f"Error creating token: {str(e)}")
    
def create_tokens(email: str) -> Dict[str, str]:
    """Создает пару access и refresh токенов"""
    access_token = create_access_token(data={"sub": email})
    refresh_token = create_refresh_token(data={"sub": email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def create_refresh_token(data: dict) -> str:
    """Создание refresh токена"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh"  
    })
    

    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_refresh_token(token: str) -> Dict:
    """Верификация refresh токена"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Refresh token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid refresh token")