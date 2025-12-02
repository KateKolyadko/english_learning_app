"""
Модели для анализа эссе и тестирования
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class CEFRLevel(str, enum.Enum):
    """Уровни CEFR"""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class EssayAnalysis(Base):
    """Анализ эссе"""
    __tablename__ = "essay_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    
    # Предварительная оценка
    preliminary_cefr = Column(Enum(CEFRLevel), nullable=True)
    preliminary_score = Column(Float, default=0.0)
    
    # Детальный анализ
    grammar_score = Column(Float, default=0.0)
    vocabulary_score = Column(Float, default=0.0)
    coherence_score = Column(Float, default=0.0)
    
    feedback = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("User", back_populates="essay_analyses")
    test_sessions = relationship("TestSession", back_populates="essay_analysis")


class TestSession(Base):
    """Сессия тестирования"""
    __tablename__ = "test_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    essay_analysis_id = Column(Integer, ForeignKey("essay_analyses.id"), nullable=True)
    
    test_type = Column(String(50), nullable=False)  # grammar, vocabulary, mixed
    total_questions = Column(Integer, default=0)
    questions_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    
    final_score = Column(Float, default=0.0)
    final_cefr = Column(Enum(CEFRLevel), nullable=True)
    
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    user = relationship("User", back_populates="test_sessions")
    essay_analysis = relationship("EssayAnalysis", back_populates="test_sessions")
    answers = relationship("TestAnswer", back_populates="test_session")


class TestAnswer(Base):
    """Ответ на вопрос теста"""
    __tablename__ = "test_answers"

    id = Column(Integer, primary_key=True, index=True)
    test_session_id = Column(Integer, ForeignKey("test_sessions.id"), nullable=False)
    question_id = Column(Integer, nullable=False)
    user_answer = Column(String(500), nullable=False)
    correct_answer = Column(String(500), nullable=False)
    is_correct = Column(Boolean, default=False)
    response_time = Column(Float, default=0.0)  # в секундах
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    test_session = relationship("TestSession", back_populates="answers")


class UserProgress(Base):
    """Прогресс пользователя"""
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    grammar_score = Column(Float, default=0.0)
    vocabulary_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    current_cefr = Column(Enum(CEFRLevel), nullable=True)
    
    essays_analyzed = Column(Integer, default=0)
    total_test_questions = Column(Integer, default=0)
    correct_test_answers = Column(Integer, default=0)
    
    last_analysis_date = Column(DateTime(timezone=True), nullable=True)
    last_test_date = Column(DateTime(timezone=True), nullable=True)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связь
    user = relationship("User", back_populates="progress")