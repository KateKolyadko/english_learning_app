"""
анализатор лексикис интеграцией WordNet
"""

from __future__ import annotations

import math
from functools import lru_cache
from statistics import mean
from typing import Dict, List, Tuple, Any, Optional

import spacy
from spacy.tokens import Doc, Token

from .models import VocabularyAnalysis, CEFRLevel
from .wordnet_analyzer import WordNetAnalyzer

try:
    from wordfreq import zipf_frequency as _zipf
except Exception:
    _zipf = None  


#конфигурация параметров
WEIGHTS = {
    "diversity": 0.22,          # TTR/MTLD/HD-D и проч.
    "sophistication": 0.28,     # CEFR-уровни + редкость слов
    "appropriateness": 0.20,    # уместность 
    "pos_balance": 0.10,        # баланс частей речи/контент-слов
    "wordnet": 0.15,            # вклад WordNet 
    "stability": 0.05,          # длина слов, распределения, согласованность метрик
}

PENALTIES = {
    "lexical_error": 2.5,       # штраф за элемент в lexical_errors
    "collocation_error": 1.5,   # штраф за элемент в collocation_errors
    "max_total": 25.0,          # максимум суммарного штрафа
}

#словарь академических слов (примерно, не жёстко)
ACADEMIC_HINTS = {
    "moreover", "furthermore", "nevertheless", "notwithstanding",
    "therefore", "consequently", "hence", "accordingly", "thus",
    "subsequently", "predominantly", "robust", "salient", "plausible",
    "empirical", "theoretical", "novel", "paradigm", "framework",
}

# неформальная или разговорная лексика
INFORMAL_WORDS = {
    "gonna", "wanna", "gotta", "yeah", "stuff", "things", "kinda", "sorta",
    "cool", "awesome", "buddy", "dude", "nah", "yep", "btw", "idk", "imo",
}

# частые ложные коллокации/ошибки (расширено)
COMMON_COLLOCATION_ERRORS = {
    "make a homework": "do homework",
    "make an exercise": "do exercise",
    "do a mistake": "make a mistake",
    "say the truth": "tell the truth",
    "win the world": "conquer the world",
    "strong rain": "heavy rain",
    "big problem": "serious problem",
    "do a decision": "make a decision",
    "do an effort": "make an effort",
}

#шаблоны неверных пар make/do (биграммы)
MAKE_DO_VERB_COMPLEMENTS = {
    "make": {"mistake", "noise", "decision", "effort", "progress", "arrangement", "appointment"},
    "do": {"homework", "exercise", "work", "research", "business", "housework"},
}

# частотные пары для much/many
COUNTABLE = {"people", "students", "books", "cars", "houses", "tasks", "ideas", "facts", "words"}
UNCOUNTABLE = {"information", "advice", "news", "money", "time", "equipment", "luggage", "furniture"}

@lru_cache(maxsize=1)
def _get_nlp() -> spacy.Language:
    """Кэшированная загрузка spaCy: предпочтительно en_core_web_sm, fallback — blank('en')."""
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        nlp = spacy.blank("en")
    # Убедимся, что есть токенизация предложений
    if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


class VocabularyAnalyzer:
    def __init__(self):
        self.nlp = _get_nlp()
        self.wordnet_analyzer = WordNetAnalyzer()

        # Базовый словарь CEFR-индикаторов
        self.level_words = {
            CEFRLevel.A1: {
                "i", "you", "he", "she", "it", "we", "they", "is", "am", "are",
                "have", "has", "do", "does", "good", "bad", "big", "small"
            },
            CEFRLevel.A2: {
                "because", "but", "and", "or", "when", "where", "why", "how",
                "what", "which", "who", "nice", "beautiful", "interesting"
            },
            CEFRLevel.B1: {
                "although", "however", "therefore", "furthermore", "meanwhile",
                "significant", "important", "development", "education"
            },
            CEFRLevel.B2: {
                "nevertheless", "consequently", "accordingly", "similarly",
                "complicated", "sophisticated", "contemporary", "significant"
            },
            CEFRLevel.C1: {
                "notwithstanding", "paradigm", "ubiquitous", "comprehensive",
                "sophisticated", "proliferation", "fundamental"
            },
            CEFRLevel.C2: {
                "precipitate", "myriad", "engender", "imperative", "idiosyncratic",
                "magnanimous", "perspicacious"
            },
        }

        # Неформальная лексика
        self.informal_words = set(INFORMAL_WORDS)

 
    async def analyze(self, text: str) -> VocabularyAnalysis:
        doc = self.nlp(text)

        #леммы/слова/фильтры
        tokens_alpha = [t for t in doc if t.is_alpha]
        lemmas = [t.lemma_.lower() if t.lemma_ != "" else t.text.lower() for t in tokens_alpha]
        words_no_stop = [t.text.lower() for t in doc if t.is_alpha and not t.is_stop]

        #CEFR-распределение по триггерам
        level_distribution = self._analyze_vocabulary_levels(lemmas)

        #лексическое разнообразие
        lexical_diversity = self._calculate_lexical_diversity(doc)

        #лексическая сложность (CEFR + редкость слов)
        lexical_sophistication = self._calculate_lexical_sophistication(level_distribution, lemmas)

        #уместность использования слов 
        word_appropriateness, style_meta = self._analyze_word_appropriateness(doc, lemmas)

        # POS-распределение, контент-слова, длина слов, редкие слова
        pos_profile = self._pos_profile(doc)
        content_ratio = self._content_word_ratio(doc)
        avg_word_len = self._avg_word_len(lemmas)
        rare_ratio = self._rare_word_ratio(lemmas)

        #анализ через WordNet + дополнительные вычисления
        wordnet_analysis = self.wordnet_analyzer.analyze_lexical_richness(text)

        #Ошибки лексики и коллокаций
        lexical_errors = self._identify_lexical_errors(lemmas)
        collocation_errors, collocation_suggestions = self._identify_collocation_errors(doc)

        #итоговая оценкас учётом WordNet
        overall_vocabulary = self._calculate_overall_vocabulary(
            level_distribution=level_distribution,
            diversity=lexical_diversity,
            sophistication=lexical_sophistication,
            appropriateness=word_appropriateness,
            lexical_errors=lexical_errors,
            collocation_errors=collocation_errors,
            wordnet_analysis=wordnet_analysis,
            pos_profile=pos_profile,
            content_ratio=content_ratio,
            avg_word_len=avg_word_len,
            rare_ratio=rare_ratio,
        )

        extras = wordnet_analysis.setdefault("extras", {})
        extras.update(
            {
                "pos_profile": pos_profile,
                "content_word_ratio": content_ratio,
                "avg_word_len": avg_word_len,
                "rare_word_ratio": rare_ratio,
                "style_meta": style_meta,
                "collocation_suggestions": collocation_suggestions,
                "diversity_breakdown": self._diversity_breakdown(doc),
            }
        )

        return VocabularyAnalysis(
            level_distribution=level_distribution,
            lexical_diversity=lexical_diversity,
            lexical_sophistication=lexical_sophistication,
            word_appropriateness=word_appropriateness,
            lexical_errors=lexical_errors,
            collocation_errors=collocation_errors,
            overall_vocabulary=overall_vocabulary,
            wordnet_analysis=wordnet_analysis,
        )

    # CEFR-распределение
    def _analyze_vocabulary_levels(self, lemmas: List[str]) -> Dict[CEFRLevel, int]:
        """Подсчёт CEFR-индикаторов по спискам-триггерам (леммы)."""
        level_counts: Dict[CEFRLevel, int] = {level: 0 for level in CEFRLevel}
        for w in lemmas:
            for level, vocab in self.level_words.items():
                if w in vocab:
                    level_counts[level] += 1
                    break
        return {k: v for k, v in level_counts.items() if v > 0}

    # лексическое разнообразие
    def _calculate_lexical_diversity(self, doc: Doc) -> float:
        """
        Композитная метрика разнообразия: TTR, Herdan's C, Maas a, MTLD (приближ.), HD-D (упрощённо).
        Приводим к 100-балльной шкале.
        """
        words = [t.text.lower() for t in doc if t.is_alpha and not t.is_stop]
        if len(words) < 10:
            return 35.0

        types = len(set(words))
        tokens = len(words)

        #базовые метрики
        ttr = types / tokens
        herdan_c = self._herdan_c(types, tokens) 
        maas_a = self._maas_a(types, tokens) 
        mtld = self._mtld(words)     
        hdd = self._hdd(words) 

        scores = [
            self._scale(ttr, 0.25, 0.8), 
            self._scale(herdan_c, 0.5, 1.2),
            self._scale(1.0 / (maas_a + 1e-6), 0.5, 4),
            self._scale(mtld, 10, 150), 
            self._scale(hdd, 0.2, 0.9), 
        ]
        return round(mean(scores) * 100, 2)

    def _herdan_c(self, v: int, n: int) -> float:
        return math.log(max(v, 1)) / max(math.log(max(n, 2)), 1e-6)

    def _maas_a(self, v: int, n: int) -> float:
        ln_n = math.log(max(n, 2))
        ln_v = math.log(max(v, 1))
        # Maas a^2 = (ln N - ln V) / (ln N)^2
        a2 = (ln_n - ln_v) / (ln_n ** 2 + 1e-9)
        return math.sqrt(max(a2, 0.0))

    def _mtld(self, words: List[str], ttr_threshold: float = 0.72) -> float:
        """Приближённый MTLD: считаем длину сегментов, пока TTR не упадёт ниже порога"""
        if not words:
            return 0.0
        factors = 0
        seg_types = set()
        seg_count = 0
        for w in words:
            seg_count += 1
            seg_types.add(w)
            ttr = len(seg_types) / seg_count
            if ttr < ttr_threshold:
                factors += 1
                seg_types.clear()
                seg_count = 0
        if seg_count > 0:
            # частичный фактор
            factors += (seg_count / max(len(seg_types), 1))
        return len(words) / max(factors, 1e-6)

    def _hdd(self, words: List[str], sample_size: int = 42) -> float:
        """
        Упрощённый HD-D: вероятность встретить тип при случайной выборке размера sample_size.
        Это грубая аппроксимация (без рандома и корпусов).
        """
        from collections import Counter
        counts = Counter(words)
        n = sum(counts.values())
        if n == 0:
            return 0.0

        s = min(sample_size, n)
        probs = []
        for f in counts.values():
            p = 1.0 - ((n - f) / n) ** s
            probs.append(p)
        # нормируем на число типов
        return sum(probs) / max(len(counts), 1)

    # лексическая сложность
    def _calculate_lexical_sophistication(self, level_distribution: Dict[CEFRLevel, int], lemmas: List[str]) -> float:
        """CEFR-веса + доля редких слов """
        if level_distribution:
            total = sum(level_distribution.values())
            weights = {
                CEFRLevel.A1: 1.0,
                CEFRLevel.A2: 2.0,
                CEFRLevel.B1: 3.0,
                CEFRLevel.B2: 4.0,
                CEFRLevel.C1: 5.0,
                CEFRLevel.C2: 6.0,
            }
            wsum = sum(level_distribution.get(l, 0) * weights[l] for l in CEFRLevel)
            cefr_score = (wsum / (total * 6.0)) * 100.0
        else:
            cefr_score = 30.0

        # Редкость слов по Zipf
        rare_ratio = self._rare_word_ratio(lemmas) 
        rare_bonus = min(30.0, max(0.0, (rare_ratio - 0.2) * 75.0))

        return round(min(100.0, cefr_score * 0.75 + rare_bonus * 0.25), 2)
    
    # уместность
    def _analyze_word_appropriateness(self, doc: Doc, lemmas: List[str]) -> Tuple[float, Dict[str, Any]]:
        """
        Оценка уместности: простая формальность (Heylighen-style приближение), доля академических и разговорных слов.
        Возвращает (score, meta).
        """
        total = sum(1 for t in doc if t.is_alpha)
        if total == 0:
            return 70.0, {"informal_ratio": 0.0, "academic_ratio": 0.0, "formality": 0.0}

        informal_cnt = sum(1 for w in lemmas if w in self.informal_words)
        academic_cnt = sum(1 for w in lemmas if w in ACADEMIC_HINTS)

        #проксирующая формальность: контент-слова + мало местоимений/междометий
        pos_counts = self._pos_counts(doc)
        content_ratio = self._content_word_ratio(doc)
        pronouns = pos_counts.get("PRON", 0)
        interj = pos_counts.get("INTJ", 0)
        formality = max(0.0, content_ratio * 100 - (pronouns + interj) * 2)

        informal_ratio = informal_cnt / total
        academic_ratio = academic_cnt / total

        #комбинация сигналов
        if informal_ratio > 0.12:
            base = 55.0
        elif academic_ratio > 0.08:
            base = 88.0
        elif academic_ratio > 0.04:
            base = 80.0
        else:
            base = 70.0

        #подмешаем формальность
        score = 0.7 * base + 0.3 * min(95.0, formality)
        score = max(35.0, min(100.0, score))

        meta = {
            "informal_ratio": round(informal_ratio, 4),
            "academic_ratio": round(academic_ratio, 4),
            "formality": round(formality, 2),
        }
        return score, meta


    # POS-профиль,контент-слова, длина, редкость
    def _pos_counts(self, doc: Doc) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for t in doc:
            if not t.is_alpha:
                continue
            counts[t.pos_] = counts.get(t.pos_, 0) + 1
        return counts

    def _pos_profile(self, doc: Doc) -> Dict[str, float]:
        counts = self._pos_counts(doc)
        total = sum(counts.values()) or 1
        return {k: round(v / total * 100.0, 2) for k, v in counts.items()}

    def _content_word_ratio(self, doc: Doc) -> float:
        total = sum(1 for t in doc if t.is_alpha)
        if total == 0:
            return 0.0
        content = sum(1 for t in doc if t.pos_ in ("NOUN", "VERB", "ADJ", "ADV"))
        return content / total

    def _avg_word_len(self, lemmas: List[str]) -> float:
        if not lemmas:
            return 0.0
        return round(mean(len(w) for w in lemmas), 2)

    def _rare_word_ratio(self, lemmas: List[str]) -> float:
        """доля редких слов по Zipf < 3.5, если wordfreq доступен, иначе грубая эвристика по длине"""
        if not lemmas:
            return 0.0
        if _zipf:
            freqs = [_zipf(w, "en") for w in lemmas]
            rare = sum(1 for f in freqs if f < 3.5)
            return rare / len(lemmas)
        rare = sum(1 for w in lemmas if len(w) >= 10)
        return rare / len(lemmas)

    # лексические ошибки или коллокации
    def _identify_lexical_errors(self, lemmas: List[str]) -> List[str]:
        """Выявляет типичные лексические ошибки (much/many, make/do и др.)."""
        errors: List[str] = []
        for i in range(len(lemmas) - 1):
            w1, w2 = lemmas[i], lemmas[i + 1]

            if w1 == "much" and w2 in COUNTABLE:
                errors.append(f"Use 'many' with countable noun '{w2}'")
            if w1 == "many" and w2 in UNCOUNTABLE:
                errors.append(f"Use 'much' with uncountable noun '{w2}'")

            if w1 == "make" and w2 in MAKE_DO_VERB_COMPLEMENTS["do"]:
                errors.append(f"Use 'do' instead of 'make' with '{w2}'")
            if w1 == "do" and w2 in MAKE_DO_VERB_COMPLEMENTS["make"]:
                errors.append(f"Use 'make' instead of 'do' with '{w2}'")

        return errors

    def _identify_collocation_errors(self, doc: Doc) -> Tuple[List[str], List[Dict[str, Any]]]:
        """выявляет ошибки в словосочетаниях"""
        errors: List[str] = []
        suggestions: List[Dict[str, Any]] = []

        text_lower = doc.text.lower()
        for wrong, correct in COMMON_COLLOCATION_ERRORS.items():
            if wrong in text_lower:
                errors.append(f"Use '{correct}' instead of '{wrong}'")

        # можно предложить более точный синоним
        weak_adjs = {"big", "small", "nice", "good", "bad", "interesting"}
        for token in doc:
            if token.pos_ == "ADJ" and token.head.pos_ == "NOUN":
                adj = token.lemma_.lower()
                noun = token.head.lemma_.lower()
                if adj in weak_adjs:
                    # Попробуем предложить до 3 синонимов подходящего уровня
                    syns = self.wordnet_analyzer.get_word_suggestions(adj, level="B2")
                    if syns:
                        suggestions.append(
                            {
                                "pattern": f"{adj} {noun}",
                                "suggestions": syns[:3],
                                "note": "Consider more specific adjective",
                            }
                        )

        generic_verbs = {"do", "make", "get", "have"}
        for token in doc:
            if token.pos_ == "VERB" and token.lemma_.lower() in generic_verbs:
                has_obj = any(ch.dep_ in ("dobj", "obj") for ch in token.children)
                if has_obj:
                    syns = self.wordnet_analyzer.get_word_suggestions(token.lemma_.lower(), level="B2")
                    if syns:
                        suggestions.append(
                            {
                                "pattern": token.lemma_.lower(),
                                "suggestions": syns[:3],
                                "note": "Consider a more specific verb",
                            }
                        )

        return errors, suggestions

    # итог
    def _calculate_overall_vocabulary(
        self,
        level_distribution: Dict[CEFRLevel, int],
        diversity: float,
        sophistication: float,
        appropriateness: float,
        lexical_errors: List[str],
        collocation_errors: List[str],
        wordnet_analysis: Dict[str, Any],
        pos_profile: Dict[str, float],
        content_ratio: float,
        avg_word_len: float,
        rare_ratio: float,
    ) -> float:
        """Оценка словаря.Все компоненты приводятся к взвешенной сумме, затем применяется штраф за ошибки"""
        pos_component = self._pos_component(pos_profile, content_ratio)

        wn_div = wordnet_analysis.get("synonym_diversity", 0)    # 0..100
        wn_poly = wordnet_analysis.get("polysemy_score", 0)       # 0..100
        wn_sem = wordnet_analysis.get("semantic_density", 0)      # 0..100
        wordnet_component = 0.55 * wn_div + 0.30 * wn_poly + 0.15 * wn_sem

        stability = self._stability_component(diversity, sophistication, appropriateness, rare_ratio, avg_word_len)

        base = (
            WEIGHTS["diversity"] * diversity
            + WEIGHTS["sophistication"] * sophistication
            + WEIGHTS["appropriateness"] * appropriateness
            + WEIGHTS["pos_balance"] * pos_component
            + WEIGHTS["wordnet"] * wordnet_component
            + WEIGHTS["stability"] * stability
        )

        #штрафы
        penalty = min(
            PENALTIES["max_total"],
            len(lexical_errors) * PENALTIES["lexical_error"] + len(collocation_errors) * PENALTIES["collocation_error"],
        )

        final = max(30.0, base - penalty)

        #бонус за высокий уровень CEFR-индикаторов
        if level_distribution:
            highest = max(level_distribution.keys(), key=lambda x: x.value)
            bonus_map = {
                CEFRLevel.A1: 0, CEFRLevel.A2: 4, CEFRLevel.B1: 8,
                CEFRLevel.B2: 12, CEFRLevel.C1: 18, CEFRLevel.C2: 24
            }
            final = min(100.0, final + bonus_map.get(highest, 0))

        return round(final, 2)

    def _pos_component(self, pos_profile: Dict[str, float], content_ratio: float) -> float:
        """баланс частей речи"""
        content_score = content_ratio * 100  # 0..100
        pron = pos_profile.get("PRON", 0.0)
        intj = pos_profile.get("INTJ", 0.0)
        penalty = min(20.0, (pron + intj) * 0.8)
        return max(40.0, min(95.0, content_score - penalty))

    def _stability_component(
        self,
        diversity: float,
        sophistication: float,
        appropriateness: float,
        rare_ratio: float,
        avg_word_len: float,
    ) -> float:
        """стабильность профиля: насколько согласованы крупные метрики и нет ли перекосов.
        Доп. штраф за экстремальные редкость/длину.
        """
        trio = [diversity, sophistication, appropriateness]
        spread = max(trio) - min(trio) 
        consensus = max(0.0, 100 - spread)
        # штраф за слишком много редких слов или слишком длинные слова
        rare_pen = max(0.0, (rare_ratio - 0.35) * 60.0) 
        len_pen = max(0.0, (avg_word_len - 8.5) * 6.0)  
        return max(30.0, min(95.0, consensus - rare_pen - len_pen))

    # вспомогательные
    def _scale(self, x: float, lo: float, hi: float) -> float:
        """Линейная нормализация x из [lo..hi] в [0..1] с отсечением."""
        if hi <= lo:
            return 0.0
        return max(0.0, min(1.0, (x - lo) / (hi - lo)))

    def _diversity_breakdown(self, doc: Doc) -> Dict[str, float]:
        """Возвращает детальный расклад по метрикам разнообразия (в процентах)"""
        words = [t.text.lower() for t in doc if t.is_alpha and not t.is_stop]
        if len(words) < 10:
            return {"ttr": 0.0, "herdan_c": 0.0, "maas_inv": 0.0, "mtld": 0.0, "hdd": 0.0}
        types = len(set(words))
        tokens = len(words)
        ttr = types / tokens
        herdan_c = self._herdan_c(types, tokens)
        maas_inv = 1.0 / (self._maas_a(types, tokens) + 1e-6)
        mtld = self._mtld(words)
        hdd = self._hdd(words)
        return {
            "ttr": round(self._scale(ttr, 0.25, 0.8) * 100, 2),
            "herdan_c": round(self._scale(herdan_c, 0.5, 1.2) * 100, 2),
            "maas_inv": round(self._scale(maas_inv, 0.5, 4.0) * 100, 2),
            "mtld": round(self._scale(mtld, 10, 150) * 100, 2),
            "hdd": round(self._scale(hdd, 0.2, 0.9) * 100, 2),
        }
