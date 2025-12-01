from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from password_strength import PasswordPolicy

policy = PasswordPolicy.from_names(
    length=8,
    uppercase=1,
    numbers=1,
    special=1
)

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    current_level: Optional[str] = "beginner"
    target_level: Optional[str] = "intermediate"


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        errors = policy.test(v)
        if errors:
            error_messages = []
            if "length" in str(errors):
                error_messages.append("at least 8 characters")
            if "uppercase" in str(errors):
                error_messages.append("1 uppercase letter")
            if "numbers" in str(errors):
                error_messages.append("1 number")
            if "special" in str(errors):
                error_messages.append("1 special character")
            raise ValueError(f"Password too weak. Must contain: {', '.join(error_messages)}")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    current_level: Optional[str] = None
    target_level: Optional[str] = None

class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

class TokenRefresh(BaseModel):
    refresh_token: str