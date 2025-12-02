"""
Pydantic схемы для анализа текста и тестирования
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
from app.schemas.user import UserResponse

class CEFRLevel(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"

class GrammarAspect(str, Enum):
    PRESENT_SIMPLE = "present_simple"
    PRESENT_CONTINUOUS = "present_continuous"
    PAST_SIMPLE = "past_simple"
    PAST_CONTINUOUS = "past_continuous"
    PRESENT_PERFECT = "present_perfect"
    PAST_PERFECT = "past_perfect"
    FUTURE_SIMPLE = "future_simple"
    FUTURE_CONTINUOUS = "future_continuous"
    FUTURE_PERFECT = "future_perfect"
    CONDITIONALS = "conditionals"
    PASSIVE_VOICE = "passive_voice"
    MODAL_VERBS = "modal_verbs"
    RELATIVE_CLAUSES = "relative_clauses"
    ARTICLES = "articles"
    PREPOSITIONS = "prepositions"
    VOCABULARY_USAGE = "vocabulary_usage"
    VOCABULARY_COLLOCATIONS = "vocabulary_collocations"
    SENTENCE_STRUCTURE = "sentence_structure"

class QuestionType(str, Enum):
    GRAMMAR_TENSES = "grammar_tenses"
    GRAMMAR_ARTICLES = "grammar_articles"
    GRAMMAR_PREPOSITIONS = "grammar_prepositions"
    GRAMMAR_CONDITIONALS = "grammar_conditionals"
    VOCABULARY_COMPLEXITY = "vocabulary_complexity"
    VOCABULARY_APPROPRIATENESS = "vocabulary_appropriateness"
    VOCABULARY_COLLOCATIONS = "vocabulary_collocations"

# Схемы запросов
class EssayAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=50, max_length=5000, description="Текст для анализа (50-5000 символов)")
    title: Optional[str] = Field(None, max_length=200, description="Название эссе (опционально)")

class TestAnswerRequest(BaseModel):
    question_id: str
    user_answer: str
    response_time: Optional[float] = Field(0.0, ge=0)

class TestSessionRequest(BaseModel):
    essay_analysis_id: Optional[int] = None
    test_type: str = "followup"

# Схемы ответов
class GrammarAnalysisResponse(BaseModel):
    overall_grammar: float
    grammatical_accuracy: float
    sentence_structure: float
    sentence_complexity: float
    used_aspects: Dict[GrammarAspect, float]
    unused_aspects: List[GrammarAspect]
    specific_errors: List[Dict[str, Any]]

class VocabularyAnalysisResponse(BaseModel):
    overall_vocabulary: float
    lexical_diversity: float
    lexical_sophistication: float
    word_appropriateness: float
    level_distribution: Dict[CEFRLevel, int]
    lexical_errors: List[str]
    collocation_errors: List[str]

class WeakAreaResponse(BaseModel):
    aspect: str
    score: float
    description: str
    recommendations: List[str]

class TestQuestionResponse(BaseModel):
    id: str
    type: QuestionType
    aspect: GrammarAspect
    question: str
    options: List[str]
    difficulty: CEFRLevel
    topic: str

class EssayAnalysisResponse(BaseModel):
    id: int
    user_id: int
    text: str
    word_count: int
    sentence_count: int
    preliminary_cefr: CEFRLevel
    preliminary_score: float
    
    grammar_analysis: GrammarAnalysisResponse
    vocabulary_analysis: VocabularyAnalysisResponse
    identified_gaps: List[WeakAreaResponse]
    recommendations: List[str]
    specific_errors: List[Dict[str, Any]]
    
    created_at: datetime
    
    class Config:
        from_attributes = True

class TestSessionResponse(BaseModel):
    id: int
    user_id: int
    essay_analysis_id: Optional[int]
    test_type: str
    total_questions: int
    questions_answered: int
    correct_answers: int
    final_score: Optional[float]
    final_cefr: Optional[CEFRLevel]
    is_completed: bool
    created_at: datetime
    completed_at: Optional[datetime]

class UserProgressResponse(BaseModel):
    grammar_score: float
    vocabulary_score: float
    overall_score: float
    current_cefr: CEFRLevel
    essays_analyzed: int
    total_test_questions: int
    correct_test_answers: int
    weak_areas: List[Dict[str, Any]]
    strengths: List[Dict[str, Any]]
    last_analysis_date: Optional[datetime]
    last_test_date: Optional[datetime]