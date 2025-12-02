# app/services/text_analysis/storage.py
""" Хранилище результатов анализа """

from typing import List, Optional
from app.models.analysis import EssayAnalysis
from sqlalchemy.orm import Session

class MemoryStorage:
    """Хранилище в памяти"""
    
    def __init__(self):
        self.analyses = []
    
    async def save_analysis(self, result):
        """Сохраняет результат анализа в памяти"""
        self.analyses.append(result)
    
    async def get_recent_analyses(self, user_id: Optional[str] = None, limit: int = 10):
        """Возвращает последние анализы"""
        if user_id:
            user_analyses = [a for a in self.analyses if getattr(a, 'user_id', None) == user_id]
            return user_analyses[-limit:]
        return self.analyses[-limit:]


class DatabaseStorage:
    """Хранилище в базе данных"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def save_analysis(self, result):
        """Сохраняет результат анализа в БД"""
        # Этот метод теперь реализован в analysis_service.py
        pass
    
    async def get_recent_analyses(self, user_id: int, limit: int = 10) -> List[EssayAnalysis]:
        """Возвращает последние анализы пользователя"""
        return self.db.query(EssayAnalysis).filter(
            EssayAnalysis.user_id == user_id
        ).order_by(EssayAnalysis.created_at.desc()).limit(limit).all()