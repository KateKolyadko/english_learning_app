from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserUpdatePassword
from app.core.security import get_password_hash, verify_password
from fastapi import HTTPException, status

class UserService:
    @staticmethod
    def get_user_by_email(db: Session, email: str):
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create_user(db: Session, user_create: UserCreate):
        # Проверяем, существует ли пользователь
        existing_user = UserService.get_user_by_email(db, user_create.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Создаем пользователя
        hashed_password = get_password_hash(user_create.password)
        user = User(
            email=user_create.email,
            hashed_password=hashed_password,
            full_name=user_create.full_name,
            current_level=user_create.current_level,
            target_level=user_create.target_level
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str):
        user = UserService.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_password(db: Session, user_id: int, current_password: str, new_password: str):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        return {"message": "Password updated successfully"}