from .models import TestQuestion, QuestionType, CEFRLevel, GrammarAspect


def enhance_questions_with_irt(questions):
    """Добавляет параметры Item Response Theory к вопросам"""
    for question in questions:
        if question.difficulty == CEFRLevel.A1:
            question.difficulty_param = 0.2
            question.discrimination_param = 0.8
        elif question.difficulty == CEFRLevel.A2:
            question.difficulty_param = 0.4
            question.discrimination_param = 1.0
        elif question.difficulty == CEFRLevel.B1:
            question.difficulty_param = 0.6
            question.discrimination_param = 1.2
        elif question.difficulty == CEFRLevel.B2:
            question.difficulty_param = 0.8
            question.discrimination_param = 1.4
        else:
            question.difficulty_param = 1.0
            question.discrimination_param = 1.6
    
    return questions

QUESTION_BANK = enhance_questions_with_irt([
    # грамматика - времена (A1-A2)
    TestQuestion(
        id="g_t_1",
        type=QuestionType.GRAMMAR_TENSES,
        aspect=GrammarAspect.PRESENT_SIMPLE,
        question="She ______ to school every day.",
        options=["go", "goes", "went", "going"],
        correct_answer="goes",
        difficulty=CEFRLevel.A1,
        topic="present_simple"
    ),
    TestQuestion(
        id="g_t_2",
        type=QuestionType.GRAMMAR_TENSES,
        aspect=GrammarAspect.PAST_SIMPLE,
        question="They ______ football yesterday.",
        options=["play", "plays", "played", "playing"],
        correct_answer="played",
        difficulty=CEFRLevel.A1,
        topic="past_simple"
    ),
    
    #грамматика- времена (B1)
    TestQuestion(
        id="g_t_3",
        type=QuestionType.GRAMMAR_TENSES,
        aspect=GrammarAspect.PRESENT_PERFECT,
        question="I ______ here since 2010.",
        options=["live", "lived", "have lived", "am living"],
        correct_answer="have lived",
        difficulty=CEFRLevel.B1,
        topic="present_perfect"
    ),
    
    # Грамматика- артикли
    TestQuestion(
        id="g_a_1",
        type=QuestionType.GRAMMAR_ARTICLES,
        aspect=GrammarAspect.ARTICLES,
        question="She is ______ honest person.",
        options=["a", "an", "the", "-"],
        correct_answer="an",
        difficulty=CEFRLevel.A1,
        topic="articles"
    ),
    
    # лексика- сложность
    TestQuestion(
        id="v_c_1",
        type=QuestionType.VOCABULARY_COMPLEXITY,
        aspect=GrammarAspect.PRESENT_SIMPLE,
        question="The company decided to ______ the new project due to budget constraints.",
        options=["terminate", "cease", "abandon", "conclude"],
        correct_answer="abandon",
        difficulty=CEFRLevel.B2,
        topic="advanced_vocabulary"
    ),
    
    # лексика - уместность
    TestQuestion(
        id="v_a_1",
        type=QuestionType.VOCABULARY_APPROPRIATENESS,
        aspect=GrammarAspect.PRESENT_SIMPLE,
        question="In a formal letter, it's better to write 'I am writing to ______' instead of 'I wanna'.",
        options=["complain", "inform you", "let you know", "tell you"],
        correct_answer="inform you",
        difficulty=CEFRLevel.B1,
        topic="formal_vocabulary"
    ),
])