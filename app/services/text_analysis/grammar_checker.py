""" Грамматический анализатор """
import asyncio
import difflib
import re
from typing import List, Dict, Tuple, Any
import language_tool_python

from .models import GrammarAspect


class GrammarCheckService:
    """сервис проверки грамматики"""

    def __init__(self, language: str = "en-US"):
        try:
            self.tool = language_tool_python.LanguageTool(language)
        except Exception as e:
            print(f"[GrammarCheckService] Warning: LanguageTool not available: {e}")
            self.tool = None
        self.language = language

        self.error_mapping = {
            "ENGLISH_WORD_REPEAT_RULE": GrammarAspect.VOCABULARY_USAGE,
            "UPPERCASE_SENTENCE_START": GrammarAspect.SENTENCE_STRUCTURE,
            "SENTENCE_WHITESPACE": GrammarAspect.SENTENCE_STRUCTURE,
            "ARTICLE": GrammarAspect.ARTICLES,
            "TENSE": GrammarAspect.PRESENT_SIMPLE,
            "PREPOSITION": GrammarAspect.PREPOSITIONS,
            "CONFUSED_WORDS": GrammarAspect.VOCABULARY_USAGE,
            "COLLOCATIONS": GrammarAspect.VOCABULARY_COLLOCATIONS,
            "AGREEMENT": GrammarAspect.SENTENCE_STRUCTURE,
            "TYPOGRAPHY": GrammarAspect.SENTENCE_STRUCTURE,
            "COMMA": GrammarAspect.SENTENCE_STRUCTURE,
        }

    # основной метод

    def check_text(self, text: str) -> Dict[str, Any]:
        """
        СИНХРОННАЯ версия проверки текста через LanguageTool
        """
        if not text.strip() or self.tool is None:
            return {
                "total_errors": 0, 
                "errors_by_aspect": {}, 
                "corrected_text": text,
                "extras": {}
            }

        try:
            matches = self.tool.check(text)
        except Exception as e:
            print(f"[GrammarCheckService] Error: {e}")
            return {
                "total_errors": 0, 
                "errors_by_aspect": {}, 
                "corrected_text": text,
                "extras": {}
            }

        total_errors = len(matches)
        errors_by_aspect: Dict[GrammarAspect, List[Dict[str, Any]]] = {}
        errors_summary = {"grammar": 0, "style": 0, "punctuation": 0, "agreement": 0, "other": 0}
        sentences = re.split(r"[.!?]+", text)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]

        for match in matches:
            # Используем rule_id вместо ruleId (новая версия language-tool-python)
            rule_id = getattr(match, 'rule_id', getattr(match, 'ruleId', ""))
            aspect = self._map_rule_to_aspect(rule_id)

            if aspect not in errors_by_aspect:
                errors_by_aspect[aspect] = []

            # Исправляем имена атрибутов для новой версии
            errors_by_aspect[aspect].append({
                "rule_id": rule_id,
                "message": getattr(match, 'message', ''),
                "context": getattr(match, 'context', ''),
                "replacements": getattr(match, 'replacements', []),
                "offset": getattr(match, 'offset', 0),
                "error_length": getattr(match, 'errorLength', getattr(match, 'error_length', 0)),
                "sentence": getattr(match, 'context', '').strip(),
            })

            # Примерная классификация по типу ошибки
            if "SPELL" in rule_id or "TYPOS" in rule_id:
                errors_summary["grammar"] += 1
            elif "STYLE" in rule_id or "WORDY" in rule_id:
                errors_summary["style"] += 1
            elif "COMMA" in rule_id or "PUNCT" in rule_id:
                errors_summary["punctuation"] += 1
            elif "AGREEMENT" in rule_id:
                errors_summary["agreement"] += 1
            else:
                errors_summary["other"] += 1

        corrected_text = text
        if self.tool:
            corrected_text = self.tool.correct(text)
        
        diff_intensity = self._calculate_diff_intensity(text, corrected_text)

        # дополнительные метрики
        word_count = len(re.findall(r"\b\w+\b", text))
        avg_sentence_len = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
        error_density = total_errors / max(word_count, 1) if word_count > 0 else 0
        readability = self._flesch_kincaid(text)
        dominant_errors = self._find_dominant_errors(errors_summary)
        recommendations = self._generate_recommendations(errors_summary)

        return {
            "total_errors": total_errors,
            "errors_by_aspect": errors_by_aspect,
            "errors_summary": errors_summary,
            "dominant_errors": dominant_errors,
            "corrected_text": corrected_text,
            "recommendations": recommendations,
            "extras": {
                "error_density": round(error_density, 4),
                "avg_sentence_length": round(avg_sentence_len, 2),
                "readability_index": round(readability, 2),
                "correction_intensity": round(diff_intensity, 3),
            }
        }

    # методы анализа
    def calculate_grammar_score(self, text: str, word_count: int) -> float:
        """Синхронная версия вычисления балла грамматики с использованием LanguageTool"""
        if not text.strip() or word_count == 0 or self.tool is None:
            return 100.0

        try:
            matches = self.tool.check(text)
            total_errors = len(matches)
            
            error_ratio = total_errors / word_count if word_count > 0 else 0
            if error_ratio == 0:
                return 100.0
            elif error_ratio < 0.01:
                return 90.0
            elif error_ratio < 0.03:
                return 80.0
            elif error_ratio < 0.05:
                return 70.0
            elif error_ratio < 0.1:
                return 60.0
            else:
                return 50.0
                
        except Exception as e:
            print(f"[GrammarCheckService] Error in calculate_grammar_score: {e}")
            # Fallback базовая оценка на основе простых эвристик
            return self._fallback_grammar_score(text, word_count)

    def _fallback_grammar_score(self, text: str, word_count: int) -> float:
        """Резервный метод оценки грамматики если LanguageTool не работает"""
        if word_count == 0:
            return 100.0
        
        # простые эвристики для демонстрации
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        capitalization_errors = sum(1 for s in sentences if s and not s[0].isupper())
        
        punctuation_errors = text.count('..') + text.count('??') + text.count('!!')
        
        total_errors = capitalization_errors + punctuation_errors
        error_ratio = total_errors / word_count
        
        if error_ratio == 0:
            return 95.0
        elif error_ratio < 0.02:
            return 85.0
        elif error_ratio < 0.05:
            return 75.0
        elif error_ratio < 0.1:
            return 65.0
        else:
            return 55.0


    def _map_rule_to_aspect(self, rule_id: str) -> GrammarAspect:
        """Сопоставляет правило LanguageTool  и аспект грамматики"""
        if not rule_id:
            return GrammarAspect.SENTENCE_STRUCTURE
            
        for key, aspect in self.error_mapping.items():
            if key.upper() in rule_id.upper():
                return aspect
        return GrammarAspect.SENTENCE_STRUCTURE

    def _calculate_diff_intensity(self, text1: str, text2: str) -> float:
        """Считает процент изменённых символов между оригиналом и корректировкой"""
        seq = difflib.SequenceMatcher(None, text1, text2)
        diff_ratio = 1 - seq.ratio()
        return min(1.0, max(0.0, diff_ratio))

    def _find_dominant_errors(self, summary: Dict[str, int]) -> List[str]:
        """Определяет наиболее частые типы ошибок"""
        if not summary:
            return []
        max_val = max(summary.values()) or 0
        if max_val == 0:
            return []
        return [k for k, v in summary.items() if v == max_val]

    def _generate_recommendations(self, summary: Dict[str, int]) -> List[Dict[str, str]]:
        """Создаёт рекомендации на основе профиля ошибок"""
        recs = []
        if summary.get("grammar", 0) > 5:
            recs.append({
                "aspect": "GRAMMAR",
                "tip": "Review subject–verb agreement and sentence structure rules."
            })
        if summary.get("style", 0) > 2:
            recs.append({
                "aspect": "STYLE",
                "tip": "Try to make sentences more concise. Avoid redundant expressions."
            })
        if summary.get("punctuation", 0) > 2:
            recs.append({
                "aspect": "PUNCTUATION",
                "tip": "Check comma placement and punctuation consistency."
            })
        if summary.get("agreement", 0) > 1:
            recs.append({
                "aspect": "AGREEMENT",
                "tip": "Ensure verbs match subjects in number and tense."
            })
        if not recs:
            recs.append({
                "aspect": "GENERAL",
                "tip": "Good grammar overall. Focus on clarity and coherence."
            })
        return recs

    def _flesch_kincaid(self, text: str) -> float:
        """вычисляет индекс читаемости Flesch–Kincaid (чем выше — проще)"""
        words = re.findall(r"\b\w+\b", text)
        sentences = re.split(r"[.!?]+", text)
        syllables = sum(self._count_syllables(w) for w in words)
        num_words = len(words)
        num_sentences = len([s for s in sentences if s.strip()])
        if num_words == 0 or num_sentences == 0:
            return 0.0
        asl = num_words / num_sentences  # Average Sentence Length
        asw = syllables / num_words      # Average Syllables per Word
        score = 206.835 - 1.015 * asl - 84.6 * asw
        return max(0.0, min(100.0, score))

    def _count_syllables(self, word: str) -> int:
        """грубая эвристика подсчёта слогов в английском слове"""
        word = word.lower()
        word = re.sub(r"[^a-z]", "", word)
        vowels = "aeiouy"
        count = 0
        prev_was_vowel = False
        for c in word:
            if c in vowels and not prev_was_vowel:
                count += 1
            prev_was_vowel = c in vowels
        if word.endswith("e"):
            count = max(1, count - 1)
        return max(1, count)