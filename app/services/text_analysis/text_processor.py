"""
утилиты обработки текста - вспомогательные функции
"""
from typing import Dict

def count_words(text: str) -> int:
    """Считает количество слов в тексте"""
    return len(text.split())

def get_text_statistics(text: str) -> Dict:
    """Возвращает статистику текста"""
    words = text.split()
    sentences = text.split('.')
    
    return {
        "word_count": len(words),
        "sentence_count": len([s for s in sentences if s.strip()]),
        "avg_sentence_length": len(words) / len(sentences) if sentences else 0,
        "char_count": len(text),
        "unique_words": len(set(words))
    }

def clean_text(text: str) -> str:
    """Очищает текст для анализа"""
    return ' '.join(text.split())