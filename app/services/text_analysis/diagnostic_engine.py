from typing import List
from .models import AnalysisResult, TestQuestion, QuestionType, CEFRLevel, GrammarAspect
from .question_bank import QUESTION_BANK
import random

class DiagnosticEngine:
    """генерирует тесты для уточнения слабых мест, выявленных в сочинении"""
    
    def __init__(self, question_bank: List[TestQuestion] = None):
        self.question_bank = question_bank or QUESTION_BANK
    
    def generate_followup_test(self, essay_result: AnalysisResult) -> List[TestQuestion]:
        """создает персонализированный тест на основе анализа сочинения"""
        questions = []
        
        # вопросы для неиспользованных грамматических 
        unused_questions = self._generate_questions_for_unused_aspects(essay_result)
        questions.extend(unused_questions)
        
        # вопросы для слабых мест
        weak_area_questions = self._generate_questions_for_weak_areas(essay_result)
        questions.extend(weak_area_questions)
        
        # тесты для опрелеления реального уровня
        level_questions = self._generate_level_determination_questions(essay_result)
        questions.extend(level_questions)
        
        # тесты проверки лексики
        vocabulary_questions = self._generate_vocabulary_questions(essay_result)
        questions.extend(vocabulary_questions)

        random.shuffle(questions)
        #ограничение кол-ва вопросов
        return questions[:10]
    
    def _generate_questions_for_unused_aspects(self, essay_result: AnalysisResult) -> List[TestQuestion]:
        """Генерирует вопросы по неиспользованным грамматическим аспектам"""
        questions = []
        unused_aspects = essay_result.grammar.unused_aspects
        
        if not unused_aspects:
            return questions
        
        # преобразуем GrammarAspect в QuestionType
        aspect_to_type = {
            GrammarAspect.PRESENT_SIMPLE: QuestionType.GRAMMAR_TENSES,
            GrammarAspect.PRESENT_CONTINUOUS: QuestionType.GRAMMAR_TENSES,
            GrammarAspect.PAST_SIMPLE: QuestionType.GRAMMAR_TENSES,
            GrammarAspect.PAST_CONTINUOUS: QuestionType.GRAMMAR_TENSES,
            GrammarAspect.PRESENT_PERFECT: QuestionType.GRAMMAR_TENSES,
            GrammarAspect.PAST_PERFECT: QuestionType.GRAMMAR_TENSES,
            GrammarAspect.FUTURE_SIMPLE: QuestionType.GRAMMAR_TENSES,
            GrammarAspect.FUTURE_CONTINUOUS: QuestionType.GRAMMAR_TENSES,
            GrammarAspect.FUTURE_PERFECT: QuestionType.GRAMMAR_TENSES,
            GrammarAspect.ARTICLES: QuestionType.GRAMMAR_ARTICLES,
            GrammarAspect.PREPOSITIONS: QuestionType.GRAMMAR_PREPOSITIONS,
        }
        
        # для каждого неиспользованного аспекта 1-2 вопроса
        for aspect in list(unused_aspects)[:4]:
            question_type = aspect_to_type.get(aspect)
            if question_type:
                aspect_questions = self._get_questions_by_aspect_and_level(
                    aspect, essay_result.preliminary_cefr, 1
                )
                questions.extend(aspect_questions)
        
        return questions
    
    def _generate_questions_for_weak_areas(self, essay_result: AnalysisResult) -> List[TestQuestion]:
        """Генерирует вопросы для выявленных слабых мест"""
        questions = []
        
        for aspect, score in essay_result.grammar.used_aspects.items():
            if score < 60:
                weak_questions = self._get_questions_by_aspect_and_level(
                    aspect, essay_result.preliminary_cefr, 1
                )
                questions.extend(weak_questions)
        
        return questions
    
    def _generate_level_determination_questions(self, essay_result: AnalysisResult) -> List[TestQuestion]:
        """Генерирует вопросы для точного определения уровня"""
        questions = []
        current_level = essay_result.preliminary_cefr
        
        # берем вопросы текущего уровня
        current_level_questions = self._get_questions_by_level(current_level, 2)
        questions.extend(current_level_questions)
        
        # добавляем вопросы следующего уровня
        next_level = self._get_next_level(current_level)
        if next_level:
            next_level_questions = self._get_questions_by_level(next_level, 1)
            questions.extend(next_level_questions)
        
        return questions
    
    def _generate_vocabulary_questions(self, essay_result: AnalysisResult) -> List[TestQuestion]:
        """Генерирует вопросы для проверки словарного запаса"""
        questions = []
        
        # всегда даем вопросы по лексике
        complexity_questions = self._get_questions_by_type_and_level(
            QuestionType.VOCABULARY_COMPLEXITY, essay_result.preliminary_cefr, 1
        )
        questions.extend(complexity_questions)
        
        appropriateness_questions = self._get_questions_by_type_and_level(
            QuestionType.VOCABULARY_APPROPRIATENESS, essay_result.preliminary_cefr, 1
        )
        questions.extend(appropriateness_questions)
        
        return questions
    
    def _get_next_level(self, current_level: CEFRLevel) -> CEFRLevel:
        """Возвращает следующий уровень CEFR"""
        levels = list(CEFRLevel)
        current_index = levels.index(current_level)
        if current_index + 1 < len(levels):
            return levels[current_index + 1]
        return None
    
    def _get_questions_by_aspect_and_level(self, aspect: GrammarAspect, 
                                         level: CEFRLevel, max_questions: int) -> List[TestQuestion]:
        """Находит вопросы определенного аспекта и уровня"""
        filtered = [
            q for q in self.question_bank
            if hasattr(q, 'aspect') and q.aspect == aspect and q.difficulty == level
        ]
        return filtered[:max_questions]
    
    def _get_questions_by_type_and_level(self, question_type: QuestionType, 
                                       level: CEFRLevel, max_questions: int) -> List[TestQuestion]:
        """Находит вопросы определенного типа и уровня"""
        filtered = [
            q for q in self.question_bank
            if q.type == question_type and q.difficulty == level
        ]
        return filtered[:max_questions]
    
    def _get_questions_by_level(self, level: CEFRLevel, max_questions: int) -> List[TestQuestion]:
        """Находит вопросы определенного уровня"""
        filtered = [q for q in self.question_bank if q.difficulty == level]
        return filtered[:max_questions]