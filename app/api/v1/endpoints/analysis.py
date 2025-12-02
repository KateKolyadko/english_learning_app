"""
Эндпоинты для анализа текста и тестирования
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any

from app.core.database import get_db
from app.api.deps import get_current_user 
from app.models.user import User
from app.schemas.analysis import (
    EssayAnalysisRequest,
    TestAnswerRequest,
    TestSessionRequest,
)

from app.services.analysis_service import AnalysisService

router = APIRouter()
analysis_service = AnalysisService()

@router.post("/essay", response_model=Dict[str, Any])
async def analyze_essay(
    request: EssayAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Анализирует эссе пользователя и возвращает результаты
    """
    try:
        result = await analysis_service.analyze_essay(
            db=db,
            user_id=current_user.id,
            text=request.text,
            title=request.title
        )
        
        return {
            "message": "Эссе успешно проанализировано",
            "essay_analysis_id": result["essay_analysis"].id,
            "test_session_id": result["test_session"].id,
            "preliminary_cefr": result["essay_analysis"].preliminary_cefr,
            "preliminary_score": result["essay_analysis"].preliminary_score,
            "test_reasoning": result["test_reasoning"]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при анализе текста: {str(e)}"
        )

@router.get("/essay/history", response_model=List[Dict[str, Any]])
async def get_essay_history(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает историю анализов эссе пользователя
    """
    analyses = await analysis_service.get_user_analyses(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    
    # Преобразуем в словари для ответа
    result = []
    for analysis in analyses:
        result.append({
            "id": analysis.id,
            "text": analysis.text[:100] + "..." if len(analysis.text) > 100 else analysis.text,
            "word_count": analysis.word_count,
            "preliminary_cefr": analysis.preliminary_cefr,
            "preliminary_score": analysis.preliminary_score,
            "created_at": analysis.created_at
        })
    
    return result

@router.post("/test/start", response_model=Dict[str, Any])
async def start_test_session(
    request: TestSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Начинает новую сессию тестирования
    """
    test_session = await analysis_service.start_test_session(
        db=db,
        user_id=current_user.id,
        essay_analysis_id=request.essay_analysis_id,
        test_type=request.test_type
    )
    
    return {
        "id": test_session.id,
        "test_type": test_session.test_type,
        "created_at": test_session.created_at
    }

@router.post("/test/{test_session_id}/answer", response_model=Dict[str, Any])
async def submit_test_answer(
    test_session_id: int,
    answer: TestAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Отправляет ответ на вопрос теста
    """
    result = await analysis_service.submit_test_answer(
        db=db,
        test_session_id=test_session_id,
        question_id=answer.question_id,
        user_answer=answer.user_answer,
        response_time=answer.response_time
    )
    
    return result

@router.get("/test/history", response_model=List[Dict[str, Any]])
async def get_test_history(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает историю тестовых сессий пользователя
    """
    sessions = await analysis_service.get_test_sessions(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    
    result = []
    for session in sessions:
        result.append({
            "id": session.id,
            "test_type": session.test_type,
            "total_questions": session.total_questions,
            "questions_answered": session.questions_answered,
            "correct_answers": session.correct_answers,
            "final_score": session.final_score,
            "final_cefr": session.final_cefr,
            "is_completed": session.is_completed,
            "created_at": session.created_at,
            "completed_at": session.completed_at
        })
    
    return result

@router.get("/progress", response_model=Dict[str, Any])
async def get_user_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает прогресс пользователя
    """
    progress = await analysis_service.get_user_progress(
        db=db,
        user_id=current_user.id
    )
    
    return {
        "grammar_score": progress.grammar_score,
        "vocabulary_score": progress.vocabulary_score,
        "overall_score": progress.overall_score,
        "current_cefr": progress.current_cefr,
        "essays_analyzed": progress.essays_analyzed,
        "total_test_questions": progress.total_test_questions,
        "correct_test_answers": progress.correct_test_answers,
        "accuracy": (progress.correct_test_answers / progress.total_test_questions * 100 
                    if progress.total_test_questions > 0 else 0),
        "last_analysis_date": progress.last_analysis_date,
        "last_test_date": progress.last_test_date
    }

@router.get("/recommendations", response_model=Dict[str, Any])
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает персонализированные рекомендации для пользователя
    """
    progress = await analysis_service.get_user_progress(db, current_user.id)
    
    # Генерируем рекомендации на основе прогресса
    recommendations = []
    
    if progress.grammar_score < 60:
        recommendations.append({
            "type": "grammar",
            "priority": "high",
            "message": "Рекомендуем уделить внимание грамматике",
            "suggestions": [
                "Практикуйте времена глаголов",
                "Отработайте использование артиклей",
                "Уделите внимание построению предложений"
            ]
        })
    
    if progress.vocabulary_score < 60:
        recommendations.append({
            "type": "vocabulary",
            "priority": "high",
            "message": "Стоит расширить словарный запас",
            "suggestions": [
                "Читайте статьи на английском",
                "Учите 10 новых слов каждый день",
                "Используйте слова в контексте"
            ]
        })
    
    if not recommendations:
        recommendations.append({
            "type": "general",
            "priority": "medium",
            "message": "Продолжайте регулярную практику",
            "suggestions": [
                "Пишите хотя бы одно эссе в неделю",
                "Проходите тесты для закрепления материала",
                "Читайте книги на английском"
            ]
        })
    
    return {
        "user_level": progress.current_cefr,
        "overall_score": progress.overall_score,
        "recommendations": recommendations,
        "stats": {
            "essays_analyzed": progress.essays_analyzed,
            "total_questions": progress.total_test_questions,
            "accuracy": (
                (progress.correct_test_answers / progress.total_test_questions * 100)
                if progress.total_test_questions > 0 else 0
            )
        }
    }