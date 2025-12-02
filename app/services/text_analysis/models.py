"""
модели данных для анализа текста
"""
from pydantic import BaseModel
from typing import List, Dict, Optional, Set
from datetime import datetime
from enum import Enum

class CEFRLevel(str, Enum):
    A1 = "A1"
    A2 = "A2" 
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"

class QuestionType(str, Enum):
    GRAMMAR_TENSES = "grammar_tenses"
    GRAMMAR_ARTICLES = "grammar_articles"
    GRAMMAR_PREPOSITIONS = "grammar_prepositions"
    GRAMMAR_CONDITIONALS = "grammar_conditionals"
    VOCABULARY_COMPLEXITY = "vocabulary_complexity"
    VOCABULARY_APPROPRIATENESS = "vocabulary_appropriateness"
    VOCABULARY_COLLOCATIONS = "vocabulary_collocations"

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

class GrammarAnalysis(BaseModel):
    """Детальный грамматический анализ"""
    used_aspects: Dict[GrammarAspect, float] 
    sentence_structure: float
    sentence_complexity: float
    grammatical_accuracy: float
    overall_grammar: float
    unused_aspects: Set[GrammarAspect]
    grammar_check_result: Optional[Dict] = None

class VocabularyAnalysis(BaseModel):
    """Детальный лексический анализ"""
    level_distribution: Dict[CEFRLevel, int]
    lexical_diversity: float 
    lexical_sophistication: float  
    word_appropriateness: float
    lexical_errors: List[str]
    collocation_errors: List[str]
    overall_vocabulary: float
    wordnet_analysis: Optional[Dict] = None

class WeakArea(BaseModel):
    aspect: str
    score: float
    description: str
    recommendations: List[str]
    confirmed: bool = False  

class TestQuestion(BaseModel):
    id: str
    type: QuestionType
    aspect: GrammarAspect 
    question: str
    options: List[str]
    correct_answer: str
    difficulty: CEFRLevel
    topic: str

    difficulty_param: float = 0.5
    discrimination_param: float = 1.0

class AnalysisResult(BaseModel):
    text_length: int
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    grammar: GrammarAnalysis
    vocabulary: VocabularyAnalysis
    preliminary_score: float
    preliminary_cefr: CEFRLevel
    identified_gaps: List[WeakArea]
    unused_grammar_aspects: Set[GrammarAspect]  
    specific_errors: List[Dict]
    recommendations: List[str]
    processing_time: float
    analyzed_at: datetime = datetime.now()