"""
Анализ синонимии и лексического богатства с помощью WordNet.
"""

from __future__ import annotations

import math
from functools import lru_cache
from collections import Counter
import nltk
from nltk.corpus import wordnet as wn
import spacy

try:
    nltk.data.find("corpora/wordnet")
except LookupError:
    nltk.download("wordnet")

try:
    nltk.data.find("corpora/omw-1.4")
except LookupError:
    nltk.download("omw-1.4")

try:
    from wordfreq import zipf_frequency as _zipf
except Exception:
    _zipf = None

@lru_cache(maxsize=1)
def _get_nlp():
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        nlp = spacy.blank("en")
    if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


class WordNetAnalyzer:

    def __init__(self):
        self.nlp = _get_nlp()

    def analyze_lexical_richness(self, text: str) -> dict:
        doc = self.nlp(text)
        tokens = [t for t in doc if t.is_alpha]
        lemmas = [t.lemma_.lower() if t.lemma_ else t.text.lower() for t in tokens]
        content_lemmas = [t.lemma_.lower() for t in doc
                          if t.is_alpha and t.pos_ in ("NOUN", "VERB", "ADJ", "ADV")]

        mwe_phrases = self._extract_mwe_noun_chunks(doc)
        types_for_semantics = list(set(content_lemmas))

        synonym_diversity = self._calculate_synonym_diversity(types_for_semantics)
        polysemy_score = self._calculate_polysemy_score(types_for_semantics)
        semantic_density = self._calculate_semantic_density(types_for_semantics)
        word_frequency = self._analyze_word_frequency(lemmas)

        # Расширенные метрики
        wsd_assignment = self._wsd_assign(types_for_semantics, context=self._context_bag_of_words(doc))
        coherence = self._semantic_coherence(types_for_semantics, wsd_assignment)
        depth = self._taxonomy_depth(wsd_assignment)
        hyper_hypo = self._hypernym_hyponym_richness(wsd_assignment)
        antonyms = self._antonym_contrast_ratio(types_for_semantics)
        deriv_var = self._derivational_variety(types_for_semantics)
        sense_entropy = self._sense_distribution_entropy(types_for_semantics)
        lex_domains, domain_div = self._lexname_distribution(wsd_assignment)

        extras = {
            "mwe_phrases": mwe_phrases,
            "semantic_coherence": round(coherence, 2),
            "taxonomy_depth": round(depth, 2),
            "hypernym_hyponym_richness": hyper_hypo,
            "antonym_contrast_ratio": round(antonyms, 4),
            "derivational_variety": deriv_var,
            "sense_entropy": round(sense_entropy, 4),
            "lexname_distribution": lex_domains,
            "lexname_diversity": round(domain_div, 2),
            "unique_content_types": len(types_for_semantics),
            "zipf_stats": self._zipf_stats(lemmas),
        }

        return {
            "synonym_diversity": synonym_diversity,
            "polysemy_score": polysemy_score,
            "semantic_density": semantic_density,
            "word_frequency": word_frequency,
            "extras": extras,
        }

    def get_word_suggestions(self, word: str, level: str):
        """синонимы, подходящие под условный уровень (по длине/простоте)"""
        suggestions = []
        for syn in wn.synsets(word):
            for lem in syn.lemmas():
                s = lem.name().replace("_", " ")
                # по длине для разных уровней
                if level in ["A1", "A2"] and len(s) <= 6:
                    suggestions.append(s)
                elif level in ["B1", "B2"] and len(s) <= 10:
                    suggestions.append(s)
                elif level in ["C1", "C2"]:
                    suggestions.append(s)
        base = word.lower().replace("_", " ")
        uniq = [w for w in dict.fromkeys(suggestions) if w.lower() != base]
        return uniq[:5]

    #базовые метрики
    def _calculate_synonym_diversity(self, words):
        if not words:
            return 0.0
        scores = []
        for w in set(words):
            syns = self._synonyms(w)
            n = len(syns)
            if n > 10:
                score = 100.0
            elif n > 5:
                score = 80.0
            elif n > 2:
                score = 60.0
            elif n > 0:
                score = 40.0
            else:
                score = 20.0
            scores.append(score)
        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_polysemy_score(self, words):
        if not words:
            return 0.0
        scores = []
        for w in set(words):
            n = len(self._synsets_cached(w))
            if n > 5:
                score = 100.0
            elif n > 3:
                score = 75.0
            elif n > 1:
                score = 50.0
            else:
                score = 25.0
            scores.append(score)
        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_semantic_density(self, words):
        """доля пар, которые имеют высокую близость (Wu-Palmer / path_similarity) """
        uniq = list(set(words))
        if len(uniq) < 2:
            return 0.0
        connected = 0
        pairs = 0
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                if self._are_words_related(uniq[i], uniq[j]):
                    connected += 1
                pairs += 1
        if pairs == 0:
            return 0.0
        return min(100.0, (connected / pairs) * 100)

    def _are_words_related(self, w1, w2):
        syns1 = self._synsets_cached(w1)
        syns2 = self._synsets_cached(w2)
        for s1 in syns1:
            for s2 in syns2:
                if (s1.wup_similarity(s2) or s1.path_similarity(s2)):
                    return True
                # прямые синонимы тоже считаем связью
                if w1 in [l.name().replace("_", " ") for l in s2.lemmas()] or \
                   w2 in [l.name().replace("_", " ") for l in s1.lemmas()]:
                    return True
        return False

    def _analyze_word_frequency(self, words):
        """простая категоризация + частотная логика с Zipf"""
        out = {"common_short": 0, "common_long": 0, "uncommon": 0}
        if not words:
            return out
        if _zipf:
            # Zipf >= 4.0 очень частотные; 3.0..4.0 средние; < 3.0 редкие
            for w in words:
                f = _zipf(w, "en")
                if f >= 4.0:
                    out["common_short"] += 1
                elif f >= 3.0:
                    out["common_long"] += 1
                else:
                    out["uncommon"] += 1
            return out

        for w in words:
            if len(w) <= 4:
                out["common_short"] += 1
            elif len(w) <= 7:
                out["common_long"] += 1
            else:
                out["uncommon"] += 1
        return out


    # вспомогательные методы

    def _extract_mwe_noun_chunks(self, doc):
        """Упрощённый сбор MWE на базе noun_chunks (если доступны)."""
        phrases = []
        if hasattr(doc, "noun_chunks"):
            try:
                for ch in doc.noun_chunks:
                    txt = ch.text.strip()
                    if len(txt.split()) >= 2 and txt.isascii():
                        phrases.append(txt)
            except Exception:
                pass
        return list(dict.fromkeys(phrases))[:15]

    def _context_bag_of_words(self, doc):
        """Контекст для Lesk: набор лемм контент-слов и MWE токенов."""
        bow = {t.lemma_.lower() for t in doc
               if t.is_alpha and t.pos_ in ("NOUN", "VERB", "ADJ", "ADV")}
        for phrase in self._extract_mwe_noun_chunks(doc):
            bow.update(p.lower() for p in phrase.split())
        return bow
    
    def _wsd_assign(self, words, context):
        assign = {}
        for w in words:
            best_syn = self._best_synset_lesk(w, context)
            if best_syn is None and self._synsets_cached(w):
                best_syn = self._synsets_cached(w)[0]
            if best_syn:
                assign[w] = best_syn
        return assign

    def _best_synset_lesk(self, word, context):
        best = None
        best_score = 0
        for syn in self._synsets_cached(word):
            gloss = self._gloss_tokens(syn)
            overlap = len(gloss & context)
            # лёгкий плюс за совпадения по примерам
            overlap += sum(1 for ex in syn.examples() for t in ex.split() if t.lower() in context)
            # небольшой приоритет MFS
            overlap += 0.2 if syn == self._synsets_cached(word)[0] else 0.0
            if overlap > best_score:
                best_score, best = overlap, syn
        return best

    def _gloss_tokens(self, syn):
        txt = (syn.definition() or "") + " " + " ".join(syn.examples())
        return {t.lower() for t in txt.split() if t.isalpha()}

    def _semantic_coherence(self, words, assign):
        if len(words) < 2:
            return 0.0
        seq = [w for w in words if w in assign]
        if len(seq) < 2:
            return 0.0
        scores = []
        for i in range(len(seq) - 1):
            s1 = assign[seq[i]]
            s2 = assign[seq[i + 1]]
            sim = (s1.wup_similarity(s2) or 0.0)
            if sim == 0.0:
                p = (s1.path_similarity(s2) or 0.0)
                sim = max(sim, p)
            scores.append(sim)
        if not scores:
            return 0.0
        return min(100.0, max(0.0, (sum(scores) / len(scores)) * 100))

    def _taxonomy_depth(self, assign):
        depths = []
        for syn in assign.values():
            try:
                d = max((h.min_depth() for h in syn.hypernym_paths()[-1:]), default=0)
            except Exception:
                d = syn.min_depth()
            depths.append(int(d))
        if not depths:
            return 0.0
        return min(100.0, (sum(depths) / len(depths)) / 15.0 * 100)

    def _hypernym_hyponym_richness(self, assign):
        if not assign:
            return {"avg_hypernyms": 0.0, "avg_hyponyms": 0.0}
        hypers = []
        hypos = []
        for syn in assign.values():
            try:
                hypers.append(len(syn.hypernyms()))
                hypos.append(len(syn.hyponyms()))
            except Exception:
                continue
        if not hypers and not hypos:
            return {"avg_hypernyms": 0.0, "avg_hyponyms": 0.0}
        return {
            "avg_hypernyms": round(sum(hypers) / max(1, len(hypers)), 2),
            "avg_hyponyms": round(sum(hypos) / max(1, len(hypos)), 2),
        }

    def _antonym_contrast_ratio(self, words):
        if not words:
            return 0.0
        has_ant = 0
        uniq = set(words)
        for w in uniq:
            found = False
            for s in self._synsets_cached(w):
                for l in s.lemmas():
                    if l.antonyms():
                        found = True
                        break
                if found:
                    break
            if found:
                has_ant += 1
        return has_ant / max(1, len(uniq))

    def _derivational_variety(self, words):
        rel = set()
        uniq = set(words)
        for w in uniq:
            for s in self._synsets_cached(w):
                for l in s.lemmas():
                    for d in l.derivationally_related_forms():
                        rel.add(d.name().replace("_", " "))
        return {"unique_derivational_forms": len(rel)}

    # энтропия распределения значений
    def _sense_distribution_entropy(self, words):
        uniq = set(words)
        counts = [len(self._synsets_cached(w)) for w in uniq]
        total = sum(counts)
        if total == 0:
            return 0.0
        probs = [c / total for c in counts if c > 0]
        H = -sum(p * math.log(p, 2) for p in probs)
        return H / max(1e-9, math.log(len(probs) + 1, 2))
    
    def _lexname_distribution(self, assign):
        counter = Counter()
        for syn in assign.values():
            try:
                counter[syn.lexname()] += 1
            except Exception:
                pass
        total = sum(counter.values())
        if total == 0:
            return {}, 0.0
        # индекс разнообразия Шеннон
        probs = [c / total for c in counter.values()]
        H = -sum(p * math.log(p + 1e-9, 2) for p in probs)
        # нормируем на log2(K)
        K = len(counter)
        Hn = H / max(1e-9, math.log(K + 1, 2))
        return dict(counter.most_common(15)), min(100.0, Hn * 100)

    def _zipf_stats(self, lemmas):
        if not lemmas:
            return {"mean": 0.0, "p10": 0.0, "p90": 0.0}
        vals = []
        if _zipf:
            vals = [_zipf(w, "en") for w in lemmas]
        else:
            vals = [max(1.5, 7.0 - len(w) * 0.3) for w in lemmas]
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        p10 = vals_sorted[int(0.1 * (n - 1))]
        p90 = vals_sorted[int(0.9 * (n - 1))]
        return {"mean": round(sum(vals) / n, 3), "p10": round(p10, 3), "p90": round(p90, 3)}

    @lru_cache(maxsize=8192)
    def _synsets_cached(self, word: str):
        base = wn.morphy(word) or word
        return wn.synsets(base)

    def _synonyms(self, word: str):
        out = set()
        for syn in self._synsets_cached(word):
            for l in syn.lemmas():
                s = l.name().replace("_", " ")
                if s.lower() != word.lower():
                    out.add(s)
        return out