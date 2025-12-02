"""
общий анализатор текста
Координирует грамматический, лексический и мета-анализ текста
"""

import asyncio
from typing import Dict, List, Any
from statistics import mean

from .models import GrammarAnalysis, VocabularyAnalysis, CEFRLevel
from .grammar_analyzer import GrammarAnalyzer
from .vocabulary_analyzer import VocabularyAnalyzer



class TextAnalyzer:
    """главный модуль анализа текста"""

    def __init__(self):
        self.grammar_analyzer = GrammarAnalyzer()
        self.vocabulary_analyzer = VocabularyAnalyzer()

    #основной метод
    async def analyze(self, text: str) -> Dict[str, Any]:
        """Выполняет полный анализ текста. грамматика + лексика + когнитивные показатели + CEFR + confidence."""

        if not text or not text.strip():
            return {
                "grammar": {},
                "vocabulary": {},
                "specific_errors": [],
                "insights": {},
                "estimated_level": CEFRLevel.A1.name,
                "confidence": 0.0,
            }

        #запуск анализаторов
        grammar_task = asyncio.create_task(self.grammar_analyzer.analyze(text))
        vocab_task = asyncio.create_task(self.vocabulary_analyzer.analyze(text))
        grammar_result, vocab_result = await asyncio.gather(grammar_task, vocab_task)

        extras = grammar_result.grammar_check_result.get("extras", {})
        insights = self._collect_insights(grammar_result, vocab_result, extras)

        estimated_level = self._estimate_global_cefr(grammar_result, vocab_result)

        confidence = self._calculate_confidence(text, grammar_result, vocab_result)

        specific_errors = self._extract_specific_errors(text, grammar_result, vocab_result)

        return {
            "grammar": grammar_result,
            "vocabulary": vocab_result,
            "specific_errors": specific_errors,
            "insights": insights,
            "estimated_level": estimated_level.name,
            "confidence": confidence,
        }

    def _collect_insights(
        self,
        grammar: GrammarAnalysis,
        vocab: VocabularyAnalysis,
        extras: Dict,
    ) -> Dict[str, Any]:
        """Формирует блок инсайтов (ключевые показатели анализа)."""

        insights = {
            #грамматические
            "syntactic_depth_avg": extras.get("syntactic_depth_avg", 0.0),
            "coherence_score": extras.get("coherence_score", 0.0),
            "grammatical_density": extras.get("grammatical_density", 0.0),
            "sentence_types": extras.get("sentence_types", {}),
            "subject_verb_agreement_issues": extras.get("subject_verb_agreement_issues", []),
            #лексические
            "lexical_diversity": getattr(vocab, "lexical_diversity", 0.0),
            "lexical_sophistication": getattr(vocab, "lexical_sophistication", 0.0),
            "word_appropriateness": getattr(vocab, "word_appropriateness", 0.0),
            #интегральные
            "grammar_score": grammar.overall_grammar,
            "vocabulary_score": vocab.overall_vocabulary,
        }

        core_scores = [
            grammar.overall_grammar,
            vocab.overall_vocabulary,
            insights["coherence_score"],
            insights["grammatical_density"],
        ]
        insights["cognitive_maturity"] = round(mean(core_scores), 2)

        return insights

    def _estimate_global_cefr(
        self,
        grammar: GrammarAnalysis,
        vocab: VocabularyAnalysis,
    ) -> CEFRLevel:
        """определяет уровень CEFR по совокупности метрик. Берём среднюю оценку по грамматике, словарю и когезии."""
        avg_score = mean([
            grammar.overall_grammar,
            vocab.overall_vocabulary,
            grammar.grammar_check_result.get("extras", {}).get("coherence_score", 60),
        ])

        if avg_score >= 90:
            return CEFRLevel.C2
        elif avg_score >= 80:
            return CEFRLevel.C1
        elif avg_score >= 70:
            return CEFRLevel.B2
        elif avg_score >= 60:
            return CEFRLevel.B1
        elif avg_score >= 50:
            return CEFRLevel.A2
        else:
            return CEFRLevel.A1

    def _calculate_confidence(
        self,
        text: str,
        grammar: GrammarAnalysis,
        vocab: VocabularyAnalysis,
    ) -> float:
        """Оценивает уверенность системы на основе длины текста и согласованности метрик."""
        word_count = grammar.grammar_check_result.get("extras", {}).get("word_count", 0)
        diff = abs(grammar.overall_grammar - vocab.overall_vocabulary)

        confidence = 40 + min(30, word_count / 5) - min(20, diff / 3)
        return float(max(25, min(95, confidence)))


    # анализ ошибок
    def _extract_specific_errors(
        self,
        text: str,
        grammar: GrammarAnalysis,
        vocabulary: VocabularyAnalysis,
    ) -> List[Dict[str, Any]]:
        """Собирает конкретные ошибки """

        errors: List[Dict[str, Any]] = []

        #грамматические аспекты с низкой оценкой
        for aspect, score in grammar.used_aspects.items():
            if score < 60:
                errors.append({
                    "type": f"grammar_{aspect.value}",
                    "severity": "medium",
                    "description": f"Низкая правильность использования {aspect.value}: {score:.1f}%",
                })

        #структурные проблемы
        if grammar.sentence_structure < 70:
            errors.append({
                "type": "sentence_structure",
                "severity": "medium",
                "description": f"Проблемы с построением предложений ({grammar.sentence_structure:.1f}%)",
            })

        #ошибки LanguageTool
        lt = grammar.grammar_check_result or {}
        by_aspect = lt.get("errors_by_aspect", {})
        for aspect, items in by_aspect.items():
            for it in items:
                example = self._extract_sentence_with_highlight(
                    text, it.get("offset", 0), it.get("error_length", 0)
                )
                errors.append({
                    "type": f"lt_{getattr(aspect, 'value', str(aspect))}",
                    "severity": "high" if len(items) > 3 else "low",
                    "description": it.get("message", "Grammar issue"),
                    "suggestions": it.get("replacements", [])[:3],
                    "example": example,
                })

        #лексические ошибки
        for err in vocabulary.lexical_errors or []:
            errors.append({
                "type": "vocabulary_usage",
                "severity": "low",
                "description": err,
            })


        for err in vocabulary.collocation_errors or []:
            errors.append({
                "type": "vocabulary_collocations",
                "severity": "medium",
                "description": err,
            })

        #Ошибки согласования
        svas = grammar.grammar_check_result.get("extras", {}).get("subject_verb_agreement_issues", [])
        for msg in svas:
            errors.append({
                "type": "subject_verb_agreement",
                "severity": "medium",
                "description": msg,
            })

        return errors
    
    # выделение контекста
    def _extract_sentence_with_highlight(
        self,
        text: str,
        offset: int,
        length: int,
        radius: int = 100,
    ) -> str:
        """возвращает фрагмент текста с подсветкой ошибки: ... left [ERROR] right ..."""
        if offset < 0 or offset >= len(text):
            return text[:200]

        start = max(0, offset - radius)
        end = min(len(text), offset + length + radius)
        left = text[start:offset]
        span = text[offset:offset + length]
        right = text[offset + length:end]

        return f"...{left}[{span}]{right}..."

