from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from fastapi import HTTPException, status

from app.models.analysis import (
    EssayAnalysis,
    TestSession,
    TestAnswer,
    UserProgress,
    CEFRLevel as CEFRLevelModel, 
)
from app.models.user import User
from app.services.text_analysis.analyzer import EnglishAnalyzer
from app.services.text_analysis.models import CEFRLevel  


class AnalysisService:
    """Сервис для анализа текста и управления тестированием"""
    
    def __init__(self):
        self.english_analyzer = EnglishAnalyzer()
    
    async def analyze_essay(self, db: Session, user_id: int, text: str, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Анализирует эссе пользователя с использованием EnglishAnalyzer
        """
        try:
            # Используем EnglishAnalyzer для анализа
            analysis_result = await self.english_analyzer.analyze_essay(text, user_id=str(user_id))
            
            # Получаем предварительный анализ
            prelim_analysis = analysis_result["preliminary_analysis"]
            
            # Преобразуем CEFRLevel из анализатора в CEFRLevel модели
            preliminary_cefr_value = prelim_analysis.preliminary_cefr.value
            db_cefr = None
            for level in CEFRLevelModel:
                if level.value == preliminary_cefr_value:
                    db_cefr = level
                    break
            
            # Сохраняем анализ эссе в БД
            essay_analysis = EssayAnalysis(
                user_id=user_id,
                title=title,
                text=text,
                word_count=prelim_analysis.word_count,
                preliminary_cefr=db_cefr,
                preliminary_score=prelim_analysis.preliminary_score,
                grammar_score=prelim_analysis.grammar.overall_grammar,
                vocabulary_score=prelim_analysis.vocabulary.overall_vocabulary,
                coherence_score=prelim_analysis.grammar.sentence_structure,
                feedback=self._generate_feedback(prelim_analysis)
            )
            
            db.add(essay_analysis)
            db.commit()
            db.refresh(essay_analysis)
            
            # Создаем тестовую сессию на основе анализа
            test_session = TestSession(
                user_id=user_id,
                essay_analysis_id=essay_analysis.id,
                test_type="mixed",
                total_questions=10,
            )
            db.add(test_session)
            db.commit()
            db.refresh(test_session)
            
            # Обновляем прогресс пользователя
            await self._update_user_progress(db, user_id)
            
            return {
                "essay_analysis": essay_analysis,
                "test_session": test_session,
                "test_reasoning": analysis_result.get("test_reasoning", "Эссе проанализировано, рекомендован тест для точной оценки уровня")
            }
            
        except ValueError as e:
            # Ошибка валидации текста (слишком короткий/длинный)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            # Другие ошибки анализатора
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка анализа текста: {str(e)}"
            )
    
    def _generate_feedback(self, analysis) -> str:
        """Генерирует текстовый фидбек на основе анализа"""
        feedback_parts = []
        
        # Обратная связь по грамматике
        grammar_score = analysis.grammar.overall_grammar
        if grammar_score < 60:
            feedback_parts.append(f"Грамматика: {grammar_score:.1f}% - требуется улучшение")
        elif grammar_score < 80:
            feedback_parts.append(f"Грамматика: {grammar_score:.1f}% - удовлетворительно")
        else:
            feedback_parts.append(f"Грамматика: {grammar_score:.1f}% - хорошо")
        
        # Обратная связь по словарю
        vocab_score = analysis.vocabulary.overall_vocabulary
        if vocab_score < 60:
            feedback_parts.append(f"Словарный запас: {vocab_score:.1f}% - требуется расширение")
        elif vocab_score < 80:
            feedback_parts.append(f"Словарный запас: {vocab_score:.1f}% - удовлетворительно")
        else:
            feedback_parts.append(f"Словарный запас: {vocab_score:.1f}% - хорошо")
        
        # Добавляем рекомендации
        if analysis.recommendations:
            feedback_parts.append("Рекомендации: " + "; ".join(analysis.recommendations))
        
        return "\n".join(feedback_parts)
    
    # Остальные методы остаются без изменений...
    async def get_user_analyses(self, db: Session, user_id: int, limit: int = 10, offset: int = 0) -> List[EssayAnalysis]:
        """
        Получает историю анализов пользователя
        """
        return db.query(EssayAnalysis)\
            .filter(EssayAnalysis.user_id == user_id)\
            .order_by(desc(EssayAnalysis.created_at))\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    async def start_test_session(self, db: Session, user_id: int, essay_analysis_id: Optional[int] = None, test_type: str = "mixed") -> TestSession:
        """
        Начинает новую сессию тестирования
        """
        test_session = TestSession(
            user_id=user_id,
            essay_analysis_id=essay_analysis_id,
            test_type=test_type,
            total_questions=10 if test_type == "mixed" else 15,
        )
        db.add(test_session)
        db.commit()
        db.refresh(test_session)
        return test_session
    
    async def submit_test_answer(self, db: Session, test_session_id: int, question_id: int, user_answer: str, response_time: float) -> Dict[str, Any]:
        """
        Отправляет ответ на вопрос теста
        """
        # TODO: Реализовать проверку правильности ответа
        # Временная логика (заглушка)
        correct_answer = "correct_answer_example"  # В реальности из базы вопросов
        is_correct = user_answer == correct_answer
        
        # Сохраняем ответ
        test_answer = TestAnswer(
            test_session_id=test_session_id,
            question_id=question_id,
            user_answer=user_answer,
            correct_answer=correct_answer,
            is_correct=is_correct,
            response_time=response_time,
        )
        db.add(test_answer)
        
        # Обновляем статистику сессии
        test_session = db.query(TestSession).filter(TestSession.id == test_session_id).first()
        if test_session:
            test_session.questions_answered += 1
            if is_correct:
                test_session.correct_answers += 1
            
            # Если все вопросы отвечены, завершаем сессию
            if test_session.questions_answered >= test_session.total_questions:
                test_session.is_completed = True
                test_session.completed_at = datetime.utcnow()
                
                # Рассчитываем финальный результат
                accuracy = (test_session.correct_answers / test_session.total_questions) * 100
                test_session.final_score = accuracy
                
                # Определяем CEFR уровень на основе результата
                if accuracy < 40:
                    test_session.final_cefr = CEFRLevel.A1
                elif accuracy < 50:
                    test_session.final_cefr = CEFRLevel.A2
                elif accuracy < 60:
                    test_session.final_cefr = CEFRLevel.B1
                elif accuracy < 75:
                    test_session.final_cefr = CEFRLevel.B2
                elif accuracy < 90:
                    test_session.final_cefr = CEFRLevel.C1
                else:
                    test_session.final_cefr = CEFRLevel.C2
            
            db.commit()
            
            # Обновляем прогресс пользователя
            await self._update_user_progress(db, test_session.user_id)
        
        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "question_id": question_id,
            "session_progress": {
                "questions_answered": test_session.questions_answered,
                "total_questions": test_session.total_questions,
                "correct_answers": test_session.correct_answers,
            }
        }
    
    async def get_test_sessions(self, db: Session, user_id: int, limit: int = 10, offset: int = 0) -> List[TestSession]:
        """
        Получает историю тестовых сессий пользователя
        """
        return db.query(TestSession)\
            .filter(TestSession.user_id == user_id)\
            .order_by(desc(TestSession.created_at))\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    async def get_user_progress(self, db: Session, user_id: int) -> UserProgress:
        """
        Получает прогресс пользователя
        """
        progress = db.query(UserProgress).filter(UserProgress.user_id == user_id).first()
        
        if not progress:
            # Создаем запись прогресса, если ее нет
            progress = UserProgress(
                user_id=user_id,
                grammar_score=0.0,
                vocabulary_score=0.0,
                overall_score=0.0,
                essays_analyzed=0,
                total_test_questions=0,
                correct_test_answers=0,
            )
            db.add(progress)
            db.commit()
            db.refresh(progress)
        
        return progress
    
    async def _update_user_progress(self, db: Session, user_id: int) -> None:
        """
        Обновляет прогресс пользователя на основе всех данных
        """
        # Получаем все анализы эссе пользователя
        essays = db.query(EssayAnalysis)\
            .filter(EssayAnalysis.user_id == user_id)\
            .all()
        
        # Получаем все тестовые сессии
        test_sessions = db.query(TestSession)\
            .filter(TestSession.user_id == user_id)\
            .filter(TestSession.is_completed == True)\
            .all()
        
        # Рассчитываем статистику
        essays_analyzed = len(essays)
        total_test_questions = sum(session.total_questions for session in test_sessions)
        correct_test_answers = sum(session.correct_answers for session in test_sessions)
        
        # Рассчитываем средние оценки
        avg_grammar = 0.0
        avg_vocabulary = 0.0
        avg_overall = 0.0
        
        if essays:
            avg_grammar = sum(e.grammar_score for e in essays if e.grammar_score) / len(essays)
            avg_vocabulary = sum(e.vocabulary_score for e in essays if e.vocabulary_score) / len(essays)
            avg_overall = sum(e.preliminary_score for e in essays) / len(essays)
        
        # Обновляем или создаем запись прогресса
        progress = await self.get_user_progress(db, user_id)
        
        progress.grammar_score = avg_grammar
        progress.vocabulary_score = avg_vocabulary
        progress.overall_score = avg_overall
        progress.essays_analyzed = essays_analyzed
        progress.total_test_questions = total_test_questions
        progress.correct_test_answers = correct_test_answers
        
        # Определяем текущий CEFR уровень
        if avg_overall < 20:
            progress.current_cefr = CEFRLevel.A1
        elif avg_overall < 40:
            progress.current_cefr = CEFRLevel.A2
        elif avg_overall < 60:
            progress.current_cefr = CEFRLevel.B1
        elif avg_overall < 80:
            progress.current_cefr = CEFRLevel.B2
        elif avg_overall < 90:
            progress.current_cefr = CEFRLevel.C1
        else:
            progress.current_cefr = CEFRLevel.C2
        
        # Обновляем даты последней активности
        if essays:
            progress.last_analysis_date = max(e.created_at for e in essays)
        
        if test_sessions:
            progress.last_test_date = max(s.completed_at for s in test_sessions if s.completed_at)
        
        db.commit()