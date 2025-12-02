import time
from typing import Dict, Optional, List
import re
from datetime import datetime

# Используем относительные импорты внутри пакета
from .text_analyzer import TextAnalyzer
from .diagnostic_engine import DiagnosticEngine
from .storage import MemoryStorage  # Теперь этот импорт будет работать

# Импортируем Pydantic модели анализа
from .models import AnalysisResult, CEFRLevel, WeakArea, TestQuestion

class EnglishAnalyzer:
    """реалистичная оценка + всегда тесты для уточнения"""
    
    def __init__(self, storage_backend=None):
        self.text_analyzer = TextAnalyzer()
        self.diagnostic_engine = DiagnosticEngine()
        self.storage = storage_backend or MemoryStorage()
    
    async def analyze_essay(self, text: str, user_id: Optional[str] = None) -> Dict:
        """анализ с предварительной оценкой и обязательными тестами для уточнения"""
        start_time = time.time()

        validation = self._validate_text(text)
        if not validation["is_valid"]:
            raise ValueError(
                f"Текст должен содержать от 90 до 400 слов. "
                f"Сейчас: {validation['word_count']} слов. "
                f"Статус: {validation['status']}"
            )

        analysis_result = await self.text_analyzer.analyze(text)

        preliminary_score = self._calculate_preliminary_score(analysis_result)
        preliminary_cefr = self._determine_preliminary_cefr(preliminary_score)

        weak_areas = self._identify_weak_areas(analysis_result)

        final_result = AnalysisResult(
            text_length=len(text),
            word_count=validation["word_count"],
            sentence_count=self._count_sentences(text),
            avg_sentence_length=validation["word_count"] / self._count_sentences(text) if self._count_sentences(text) > 0 else 0,
            grammar=analysis_result["grammar"],
            vocabulary=analysis_result["vocabulary"],
            preliminary_score=preliminary_score,
            preliminary_cefr=preliminary_cefr,
            identified_gaps=weak_areas,
            unused_grammar_aspects=analysis_result["grammar"].unused_aspects,
            specific_errors=analysis_result.get("specific_errors", []),
            recommendations=self._generate_recommendations(weak_areas, analysis_result["grammar"].unused_aspects),
            processing_time=time.time() - start_time,
            analyzed_at=datetime.now()
        )

        await self.storage.save_analysis(final_result)

        followup_test = self.diagnostic_engine.generate_followup_test(final_result)
        test_reasoning = self._explain_test_recommendations(final_result, followup_test)
        
        return {
            "preliminary_analysis": final_result,
            "recommended_test": followup_test,
            "test_reasoning": test_reasoning,
            "note": "Это предварительная оценка. Точный уровень будет определен после тестирования."
        }
    
    def _validate_text(self, text: str) -> Dict:
        """проверяет, что текст соответствует требованиям"""
        words = text.split()
        word_count = len(words)
        
        if word_count < 90:
            status = "TOO_SHORT"
        elif word_count > 400:
            status = "TOO_LONG"
        else:
            status = "VALID"
        
        return {
            "word_count": word_count,
            "is_valid": status == "VALID",
            "status": status
        }
    
    def _count_sentences(self, text: str) -> int:
        """считает количество предложений"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return len(sentences)
    
    def _calculate_preliminary_score(self, analysis_result: Dict) -> float:
        """вычисляет предварительный балл"""
        grammar_score = analysis_result["grammar"].overall_grammar
        vocabulary_score = analysis_result["vocabulary"].overall_vocabulary
        
        return (grammar_score * 0.5 + vocabulary_score * 0.5)
    
    def _determine_preliminary_cefr(self, score: float) -> CEFRLevel:
        """определяет предварительный уровень CEFR"""
        if score >= 85: 
            return CEFRLevel.C1
        elif score >= 70: 
            return CEFRLevel.B2
        elif score >= 55: 
            return CEFRLevel.B1
        elif score >= 40: 
            return CEFRLevel.A2
        else: 
            return CEFRLevel.A1
    
    def _identify_weak_areas(self, analysis_result: Dict) -> List[WeakArea]:
        """выявляет слабые места с реалистичными критериями"""
        weak_areas = []
        grammar = analysis_result["grammar"]
        vocabulary = analysis_result["vocabulary"]
        
        for aspect, score in grammar.used_aspects.items():
            if score < 60:
                weak_areas.append(WeakArea(
                    aspect=f"grammar_{aspect.value}",
                    score=score,
                    description=f"Низкая правильность использования {aspect.value}",
                    recommendations=[f"Практикуйте использование {aspect.value}"]
                ))
        
        if grammar.sentence_structure < 60:
            weak_areas.append(WeakArea(
                aspect="sentence_structure",
                score=grammar.sentence_structure,
                description="Проблемы с построением предложений",
                recommendations=[
                    "Отработайте базовую структуру предложения",
                    "Практикуйте сложные предложения"
                ]
            ))
        
        if vocabulary.overall_vocabulary < 60:
            weak_areas.append(WeakArea(
                aspect="vocabulary_range",
                score=vocabulary.overall_vocabulary,
                description="Ограниченный словарный запас",
                recommendations=["Читайте больше на английском", "Учите новые слова в контексте"]
            ))

        if vocabulary.lexical_errors:
            weak_areas.append(WeakArea(
                aspect="lexical_errors",
                score=max(40, vocabulary.overall_vocabulary - 15),
                description=f"Обнаружены лексические ошибки ({len(vocabulary.lexical_errors)})",
                recommendations=["Изучайте сочетаемость слов", "Внимательнее к выбору слов"]
            ))
        
        return weak_areas
    
    def _generate_recommendations(self, weak_areas: List[WeakArea], unused_aspects: set) -> List[str]:
        """Генерирует рекомендации с учетом неиспользованных аспектов"""
        recommendations = []
        
        if not weak_areas and not unused_aspects:
            return ["Хорошая работа! Продолжайте практиковаться."]
        
        # рекомендации по слабым местам
        if weak_areas:
            grammar_weak = any("grammar" in area.aspect for area in weak_areas)
            vocab_weak = any("vocabulary" in area.aspect for area in weak_areas)
            
            if grammar_weak:
                recommendations.append("Рекомендуем уделить внимание грамматике.")
            if vocab_weak:
                recommendations.append("Стоит расширять словарный запас.")
        
        # рекомендации по неиспользованным аспектам
        if unused_aspects:
            unused_list = [aspect.value for aspect in list(unused_aspects)[:3]]
            recommendations.append(f"Попрактикуйте: {', '.join(unused_list)}")
        
        return recommendations
    
    def _explain_test_recommendations(self, result: AnalysisResult, test: List[TestQuestion]) -> str:
        """Объясняет почему рекомендованы тесты"""
        if not test:
            return "Тесты не сгенерированы"
        
        reasons = []

        if result.unused_grammar_aspects:
            unused_count = len(result.unused_grammar_aspects)
            reasons.append(f"проверить {unused_count} неиспользованных аспектов грамматики")

        if result.identified_gaps:
            reasons.append("уточнить выявленные слабые места")
 
        reasons.append("точно определить ваш уровень")
        
        return f"Тесты помогут: {', '.join(reasons)}"