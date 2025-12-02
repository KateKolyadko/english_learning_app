"""
анализ грамматики с LanguageTool 
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict, Set, List, Tuple

import spacy
from spacy.tokens import Doc, Span, Token

from .models import GrammarAnalysis, GrammarAspect, CEFRLevel
from .grammar_checker import GrammarCheckService


# конфигурация весов и штрафов

GRAMMAR_WEIGHTS = {
    "aspect_weight": 0.5,     #вклад оценок по аспектам 
    "structure_weight": 0.3,  #вклад структурной метрики предложений
    "accuracy_weight": 0.2,   #вклад интегральной метрики от GrammarCheckService
}

ERROR_LIMITS = {
    "global_max_penalty": 15.0,  #глобальный штраф по количеству ошибок LT
    "per_aspect_penalty_step": 5.0,  # штраф за каждую ошибку в аспекте при корректировке used_aspects
    "per_aspect_max_penalty": 20.0,  #штраф на аспект
}

COHERENCE_CONNECTIVES = {
    "because", "although", "therefore", "however", "meanwhile",
    "furthermore", "nevertheless", "moreover", "since", "whereas", "while",
}

COORD_CONJ = {"and", "but", "or", "nor", "yet", "so"}

LOGGER = logging.getLogger(__name__)
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# В app/services/text_analysis/grammar_analyzer.py исправьте
@lru_cache(maxsize=1)
def _get_nlp(model_name: str = "en_core_web_sm") -> spacy.Language:  # Используйте sm вместо md
    """Кэшированная загрузка модели spaCy. При ошибке — blank('en') + sentencizer."""
    try:
        nlp = spacy.load(model_name)
        if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        return nlp
    except OSError:
        LOGGER.warning("[GrammarAnalyzer] Не удалось загрузить '%s'. Использую blank('en').", model_name)
        nlp = spacy.blank("en")
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        return nlp


class GrammarAnalyzer:
    def __init__(self, model: str = "en_core_web_sm") -> None:  # Используйте sm вместо md
        self.nlp = _get_nlp(model)
        self.grammar_checker = GrammarCheckService()
        LOGGER.info("[GrammarAnalyzer] Инициализировано. Модель: %s", getattr(self.nlp.meta, "name", "blank_en"))

    async def analyze(self, text: str) -> GrammarAnalysis:
        if not text or not text.strip():
            empty_result = GrammarAnalysis(
                used_aspects={},
                sentence_structure=60.0,
                sentence_complexity=0.0,
                grammatical_accuracy=100.0,
                overall_grammar=60.0,
                unused_aspects=self._all_aspects(),
                grammar_check_result={"total_errors": 0, "errors_by_aspect": {}, "corrected_text": text, "extras": {}},
            )
            return empty_result

        doc = self.nlp(text)
        word_count = sum(1 for token in doc if token.is_alpha)

        #анализ грамматики 
        used_aspects = self._analyze_used_grammar_aspects(doc)

        #проверка через LanguageTool
        grammar_check_result = self.grammar_checker.check_text(text)
        grammar_score = self.grammar_checker.calculate_grammar_score(text, word_count)

        #корректируем оценки аспектов
        used_aspects = self._adjust_scores_with_languagetool(used_aspects, grammar_check_result)

        #неиспользованные аспекты
        unused_aspects = self._identify_unused_aspects(used_aspects, doc)

        #структурная метрика + сложность
        sentence_structure = self._analyze_sentence_structure(doc)
        sentence_complexity = self._analyze_sentence_complexity(doc)

        #дополнительные глубокие метрики
        svas_errors = self._check_subject_verb_agreement(doc)  # список строк с ошибками согласования
        syntactic_depth = self._syntactic_depth_avg(doc)
        coherence_score = self._coherence_score(doc)
        gram_density = self._grammatical_density(doc)
        sent_type_dist = self._sentence_type_distribution(doc)

        #интегриальная метрика точности
        grammatical_accuracy = self._calculate_grammatical_accuracy(used_aspects, grammar_score)

        #итоговая оценка
        overall_grammar = self._calculate_overall_grammar(
            used_aspects, sentence_structure, grammatical_accuracy, grammar_check_result
        )

        #оценка уровня CEFR
        estimated_level = self._estimate_grammar_cefr(overall_grammar)

        extras = grammar_check_result.setdefault("extras", {})
        extras.update(
            {
                "word_count": word_count,
                "subject_verb_agreement_issues": svas_errors,
                "syntactic_depth_avg": syntactic_depth,
                "coherence_score": coherence_score,
                "grammatical_density": gram_density,
                "sentence_types": sent_type_dist,  
                "estimated_cefr": estimated_level.name if isinstance(estimated_level, CEFRLevel) else str(estimated_level),
            }
        )

        return GrammarAnalysis(
            used_aspects=used_aspects,
            sentence_structure=sentence_structure,
            sentence_complexity=sentence_complexity,
            grammatical_accuracy=grammatical_accuracy,
            overall_grammar=overall_grammar,
            unused_aspects=unused_aspects,
            grammar_check_result=grammar_check_result,
        )


    #вспомогательные
    def _all_aspects(self) -> Set[GrammarAspect]:
        return {
            GrammarAspect.PRESENT_SIMPLE,
            GrammarAspect.PRESENT_CONTINUOUS,
            GrammarAspect.PAST_SIMPLE,
            GrammarAspect.PAST_CONTINUOUS,
            GrammarAspect.PRESENT_PERFECT,
            GrammarAspect.PAST_PERFECT,
            GrammarAspect.FUTURE_SIMPLE,
            GrammarAspect.FUTURE_CONTINUOUS,
            GrammarAspect.FUTURE_PERFECT,
            GrammarAspect.CONDITIONALS,
            GrammarAspect.PASSIVE_VOICE,
            GrammarAspect.MODAL_VERBS,
            GrammarAspect.RELATIVE_CLAUSES,
            GrammarAspect.ARTICLES,
            GrammarAspect.PREPOSITIONS,
        }

    # анализ использованных аспектов
    def _analyze_used_grammar_aspects(self, doc: Doc) -> Dict[GrammarAspect, float]:
        """Анализирует только использованные грамматические аспекты: времена, артикли, предлоги, модальные, пассив и т.п."""
        if len(doc) == 0:
            return {}

        aspects: Dict[GrammarAspect, float] = {}

        for token in doc:
            #времена
            tense = self._identify_tense(token)
            if tense and tense not in aspects:
                correctness = self._assess_tense_correctness(token, tense, doc)
                aspects[tense] = correctness

            #артикли
            if token.text.lower() in ("a", "an", "the") and GrammarAspect.ARTICLES not in aspects:
                aspects[GrammarAspect.ARTICLES] = self._assess_article_correctness(token, doc)

            #предлоги
            if token.pos_ == "ADP" and GrammarAspect.PREPOSITIONS not in aspects:
                aspects[GrammarAspect.PREPOSITIONS] = self._assess_preposition_correctness(token, doc)

            #модальные глаголы
            if token.tag_ == "MD" and GrammarAspect.MODAL_VERBS not in aspects:
                aspects[GrammarAspect.MODAL_VERBS] = 80.0

            #пассивный залог
            if token.dep_ == "auxpass" or (token.head.dep_ == "auxpass" and token.pos_ == "VERB"):
                if GrammarAspect.PASSIVE_VOICE not in aspects:
                    aspects[GrammarAspect.PASSIVE_VOICE] = 85.0

            #относительные придаточные
            if token.dep_ == "relcl" and GrammarAspect.RELATIVE_CLAUSES not in aspects:
                aspects[GrammarAspect.RELATIVE_CLAUSES] = 80.0

        return aspects

    # определене времен
    def _identify_tense(self, token: Token) -> GrammarAspect | None:
        """Определяет время глагола (расширенная логика: Future, Conditionals, Perfect/Continuous)."""
        # модальные и вспомогательные проверяем на специфические случаи
        low = token.text.lower()

        # Future Simple: 'will' + VERB
        if low == "will" and token.head.pos_ == "VERB":
            return GrammarAspect.FUTURE_SIMPLE

        # 'going to' Future
        if low == "going" and any(ch.text.lower() == "to" for ch in token.children):
            # He is going to do 
            return GrammarAspect.FUTURE_SIMPLE

        # Conditionals: would + VERB 
        if low == "would" and token.head.pos_ == "VERB":
            return GrammarAspect.CONDITIONALS

        # Основные теги
        if token.pos_ != "VERB":
            return None

        tag = token.tag_
        # Настоящее простое
        if tag in ("VBP", "VBZ"):
            return GrammarAspect.PRESENT_SIMPLE
        # Прошедшее простое
        if tag == "VBD":
            return GrammarAspect.PAST_SIMPLE
        # Continuous + вспомогательные am/is/are/was/were
        if tag == "VBG":
            for child in token.children:
                if child.text.lower() in {"am", "is", "are"}:
                    return GrammarAspect.PRESENT_CONTINUOUS
                if child.text.lower() in {"was", "were"}:
                    return GrammarAspect.PAST_CONTINUOUS
            return GrammarAspect.PRESENT_CONTINUOUS
        # Perfect  + have/has/had
        if tag == "VBN":
            for child in token.children:
                if child.text.lower() in {"have", "has"}:
                    return GrammarAspect.PRESENT_PERFECT
                if child.text.lower() == "had":
                    return GrammarAspect.PAST_PERFECT
            if token.head.text.lower() in {"have", "has"}:
                return GrammarAspect.PRESENT_PERFECT
            if token.head.text.lower() == "had":
                return GrammarAspect.PAST_PERFECT
            return GrammarAspect.PRESENT_PERFECT

        return None

    def _assess_tense_correctness(self, token: Token, tense: GrammarAspect, doc: Doc) -> float:
        """Оценивает правильность использования времени (эвристика)."""
        base_scores = {
            GrammarAspect.PRESENT_SIMPLE: 85.0,
            GrammarAspect.PAST_SIMPLE: 80.0,
            GrammarAspect.PRESENT_CONTINUOUS: 75.0,
            GrammarAspect.PAST_CONTINUOUS: 70.0,
            GrammarAspect.PRESENT_PERFECT: 72.0,
            GrammarAspect.PAST_PERFECT: 68.0,
            GrammarAspect.FUTURE_SIMPLE: 78.0,
            GrammarAspect.FUTURE_CONTINUOUS: 70.0,
            GrammarAspect.FUTURE_PERFECT: 68.0,
            GrammarAspect.CONDITIONALS: 72.0,
        }
        return base_scores.get(tense, 70.0)

    # Артикли и Предлоги
    def _assess_article_correctness(self, token: Token, doc: Doc) -> float:
        """Оценивает правильность использования артикля (простая проверка соседнего слова)."""
        article = token.text.lower()
        next_token = None
        for i, t in enumerate(doc):
            if t == token:
                if i + 1 < len(doc):
                    next_token = doc[i + 1]
                break

        if next_token and next_token.pos_ == "NOUN":
            first = next_token.text[:1].lower()
            if article == "a" and first in "aeiou":
                return 40.0  # должен быть 'an'
            if article == "an" and first not in "aeiou":
                return 40.0  # должен быть 'a'
            return 85.0
        return 70.0

    def _assess_preposition_correctness(self, token: Token, doc: Doc) -> float:
        """Оценивает правильность использования предлогов (базовая)."""
        return 75.0
    
    # Корректировка аспектов по результатам LanguageTool
    def _adjust_scores_with_languagetool(
        self,
        used_aspects: Dict[GrammarAspect, float],
        grammar_check_result: Dict,
    ) -> Dict[GrammarAspect, float]:
        adjusted = used_aspects.copy()
        per_step = ERROR_LIMITS["per_aspect_penalty_step"]
        per_max = ERROR_LIMITS["per_aspect_max_penalty"]

        for aspect, errors in grammar_check_result.get("errors_by_aspect", {}).items():
            if aspect in adjusted:
                penalty = min(per_max, len(errors) * per_step)
                adjusted[aspect] = max(30.0, adjusted[aspect] - penalty)
        return adjusted

    # Неиспользованные аспекты
    def _identify_unused_aspects(self, used_aspects: Dict[GrammarAspect, float], doc: Doc) -> Set[GrammarAspect]:
        used = set(used_aspects.keys())
        return self._all_aspects() - used

    # Структура и сложность предложений
    def _analyze_sentence_structure(self, doc: Doc) -> float:
        """Оценивает корректность структуры предложений """
        sentences = list(doc.sents)
        if not sentences:
            return 60.0

        scores: List[float] = []
        for sent in sentences:
            has_subject = any(t.dep_ in ("nsubj", "nsubjpass", "csubj") for t in sent)
            has_verb = any(t.pos_ == "VERB" for t in sent)
            has_object = any(t.dep_ in ("dobj", "iobj", "pobj", "obj") for t in sent)

            if has_subject and has_verb and has_object:
                scores.append(90.0)
            elif has_subject and has_verb:
                scores.append(75.0)
            elif has_verb:
                scores.append(60.0)
            else:
                scores.append(40.0)

        return sum(scores) / len(scores)

    def _analyze_sentence_complexity(self, doc: Doc) -> float:
        """Оценивает сложность предложений по наличию придаточных, герундиев и сложных союзов"""
        sentences = list(doc.sents)
        if not sentences:
            return 0.0

        complex_cnt = 0
        for sent in sentences:
            sub_clauses = sum(1 for t in sent if t.dep_ in ("acl", "advcl", "relcl", "ccomp", "xcomp"))
            complex_conjs = any(t.text.lower() in COORD_CONJ for t in sent)
            non_finite = sum(1 for t in sent if t.tag_ in ("VBG", "VBN") and t.dep_ != "aux")
            if sub_clauses > 0 or complex_conjs or non_finite > 1:
                complex_cnt += 1

        return (complex_cnt / len(sentences)) * 100.0


    # доп. метрики: согласование, глубина, связность, плотность, типы предложений

    def _check_subject_verb_agreement(self, doc: Doc) -> List[str]:
        """проверяет простейшее согласование подлежащего и сказуемого (число). Возвращает список описаний ошибок"""
        issues: List[str] = []
        for token in doc:
            if token.dep_ in ("nsubj", "nsubjpass") and token.head and token.head.pos_ == "VERB":
                subj_num = token.morph.get("Number")
                verb_num = token.head.morph.get("Number")
                if subj_num and verb_num and subj_num != verb_num:
                    issues.append(f"Subject–verb agreement: '{token.text}' ↔ '{token.head.text}' (Number {subj_num} vs {verb_num})")
        return issues

    def _syntactic_depth_avg(self, doc: Doc) -> float:
        """средняя синтаксическая глубина по предложениям"""
        def depth(tok: Token) -> int:
            if not list(tok.children):
                return 1
            return 1 + max(depth(ch) for ch in tok.children)

        depths: List[int] = []
        for sent in doc.sents:
            roots = [t for t in sent if t.dep_ == "ROOT"]
            if not roots:
                continue
            depths.append(max(depth(r) for r in roots))
        if not depths:
            return 0.0
        return sum(depths) / len(depths)

    def _coherence_score(self, doc: Doc) -> float:
        """Оценивает связность по количеству служебных связок на предложение"""
        sent_count = max(1, len(list(doc.sents)))
        conn = sum(1 for t in doc if t.text.lower() in COHERENCE_CONNECTIVES)
        density = conn / sent_count
        return min(density * 100.0, 100.0)

    def _grammatical_density(self, doc: Doc) -> float:
        """процент контент-слов (NOUN/VERB/ADJ/ADV) среди всех слов"""
        total = sum(1 for t in doc if t.is_alpha)
        if total == 0:
            return 0.0
        content = sum(1 for t in doc if t.pos_ in ("NOUN", "VERB", "ADJ", "ADV"))
        return round((content / total) * 100.0, 2)

    def _sentence_type_distribution(self, doc: Doc) -> Dict[str, float]:
        """оценивает распределение типов предложений"""
        sents = list(doc.sents)
        if not sents:
            return {"simple": 100.0, "compound": 0.0, "complex": 0.0}

        counts = {"simple": 0, "compound": 0, "complex": 0}
        for sent in sents:
            has_sub = any(t.dep_ in ("advcl", "relcl", "ccomp", "xcomp", "acl") for t in sent)
            has_coord = any(t.text.lower() in COORD_CONJ and t.dep_ == "cc" for t in sent)
            if has_sub and has_coord:
                counts["complex"] += 1
            elif has_sub:
                counts["complex"] += 1
            elif has_coord:
                counts["compound"] += 1
            else:
                counts["simple"] += 1

        total = len(sents)
        return {k: round((v / total) * 100.0, 2) for k, v in counts.items()}

    # Интегральные метрики
    def _calculate_grammatical_accuracy(self, used_aspects: Dict[GrammarAspect, float], grammar_score: float) -> float:
        """Комбинирует оценку использованных аспектов и метрику LanguageTool."""
        if not used_aspects:
            return max(30.0, grammar_score * 0.8)
        aspect_score = sum(used_aspects.values()) / len(used_aspects)
        return (aspect_score * 0.6 + grammar_score * 0.4)

    def _calculate_overall_grammar(
        self,
        used_aspects: Dict[GrammarAspect, float],
        structure_score: float,
        accuracy_score: float,
        grammar_check_result: Dict,
    ) -> float:
        """Формула итоговой оценки с учётом глобального штрафа за количество ошибок LT."""
        if not used_aspects:
            # без аспектов больше веса у структуры
            base = structure_score * 0.7 + accuracy_score * 0.3
        else:
            w_a = GRAMMAR_WEIGHTS["aspect_weight"]
            w_s = GRAMMAR_WEIGHTS["structure_weight"]
            w_g = GRAMMAR_WEIGHTS["accuracy_weight"]

            aspect_score = sum(used_aspects.values()) / len(used_aspects)
            base = aspect_score * w_a + structure_score * w_s + accuracy_score * w_g

        total_errors = grammar_check_result.get("total_errors", 0)
        penalty = min(ERROR_LIMITS["global_max_penalty"], float(total_errors) * 1.5)
        return max(30.0, base - penalty)

    # Оценка CEFR 
    def _estimate_grammar_cefr(self, overall_score: float) -> CEFRLevel:
        """Грубая эвристика для уровня CEFR на основе итогового балла."""
        if overall_score >= 90:
            return CEFRLevel.C2
        if overall_score >= 80:
            return CEFRLevel.C1
        if overall_score >= 70:
            return CEFRLevel.B2
        if overall_score >= 60:
            return CEFRLevel.B1
        if overall_score >= 50:
            return CEFRLevel.A2
        return CEFRLevel.A1
