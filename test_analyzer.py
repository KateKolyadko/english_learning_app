import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_proper():
    """Тест с текстами правильной длины"""
    from app.services.text_analysis.analyzer import EnglishAnalyzer
    
    # Тестовые тексты с правильным количеством слов
    test_texts = {
        "B1": """
        Education is a fundamental aspect of human development that shapes individuals and societies. 
        It provides knowledge, skills, and values necessary for personal growth and social progress. 
        In today's rapidly changing world, education has become more important than ever before. 
        Access to quality education can significantly improve a person's life chances and opportunities. 
        Many countries invest heavily in their education systems to ensure future prosperity. 
        However, educational inequality remains a serious issue in various parts of the world. 
        Some children have access to excellent schools and resources, while others struggle with basic facilities. 
        Technology has revolutionized education by making learning materials more accessible. 
        Online courses and digital platforms allow people to study from anywhere at any time. 
        This flexibility has opened up educational opportunities for millions of people worldwide. 
        Despite these advancements, traditional classroom learning still offers valuable benefits. 
        Face-to-face interaction with teachers and peers enhances the learning experience. 
        Practical activities and group discussions develop important social and communication skills. 
        Therefore, a balanced approach combining traditional and modern methods seems most effective. 
        Education should not only focus on academic knowledge but also on character development. 
        Critical thinking, creativity, and problem-solving abilities are essential in the 21st century. 
        Schools should prepare students for real-world challenges they will face in their lives. 
        Lifelong learning has become a necessity in our constantly evolving society. 
        People need to continuously update their skills to remain competitive in the job market. 
        Educational institutions must adapt to these changing demands to remain relevant. 
        Ultimately, education empowers individuals and transforms communities for the better.
        """,
        
        "C1": """
        The globalization of education has precipitated a paradigm shift in pedagogical methodologies and institutional frameworks. 
        Contemporary educational discourse increasingly emphasizes the necessity of cultivating interdisciplinary competencies and adaptive learning strategies. 
        The proliferation of digital technologies has fundamentally altered the epistemological landscape, facilitating unprecedented access to informational resources. 
        However, this technological democratization concomitantly engenders concerns regarding informational veracity and cognitive overload. 
        The constructivist approach to learning, which posits knowledge as actively constructed rather than passively absorbed, has gained considerable scholarly traction. 
        This theoretical orientation underscores the importance of metacognitive awareness and self-regulated learning behaviors. 
        Educational neuroscience research has elucidated the neurobiological substrates underlying effective learning processes. 
        Empirical evidence suggests that multisensory integration and spaced repetition significantly enhance long-term knowledge retention. 
        The implementation of differentiated instruction, which accommodates diverse learning modalities and cognitive profiles, represents a significant advancement in educational equity. 
        Furthermore, the integration of socio-emotional learning components within curricular frameworks addresses the holistic development of learners. 
        The emergence of competency-based education models challenges traditional temporal constraints and credentialing systems. 
        Micro-credentials and digital badging systems offer more granular representations of skill acquisition and professional development. 
        The internationalization of higher education has fostered cross-cultural pedagogical exchanges and collaborative research initiatives. 
        Transnational educational partnerships facilitate the dissemination of innovative teaching practices and comparative policy analysis. 
        Nevertheless, the commodification of education raises ethical questions regarding accessibility and institutional priorities. 
        The tension between educational instrumentalism and humanistic values continues to animate philosophical debates within academic circles. 
        Sustainable educational development requires synergistic alignment of institutional resources, pedagogical innovation, and societal needs. 
        Future-oriented educational systems must balance technological integration with the preservation of essential human interactions. 
        The cultivation of epistemic agility and adaptive expertise represents a paramount objective in preparing learners for complex, uncertain futures.
        """
    }
    
    analyzer = EnglishAnalyzer()
    
    for level, text in test_texts.items():
        print(f"\n{'='*60}")
        print(f"Тестирование текста уровня {level}")
        print(f"{'='*60}")
        
        words = text.split()
        word_count = len(words)
        print(f"Длина: {len(text)} символов, {word_count} слов")
        
        if word_count < 90:
            print(f"Текст слишком короткий: {word_count} слов. Нужно минимум 90.")
            continue
        elif word_count > 400:
            print(f"Текст слишком длинный: {word_count} слов. Нужно максимум 400.")

            text = ' '.join(words[:400])
            print(f"Обрезано до 400 слов для теста")
        
        try:
            print("Анализирую...")
            result = await analyzer.analyze_essay(text, user_id="test_user")
            prelim = result["preliminary_analysis"]
            
            print(f"\nРезультаты анализа:")
            print(f"Предварительный уровень CEFR: {prelim.preliminary_cefr}")
            print(f"Предварительная оценка: {prelim.preliminary_score:.1f}")
            print(f"Оценка грамматики: {prelim.grammar.overall_grammar:.1f}")
            print(f"Оценка словаря: {prelim.vocabulary.overall_vocabulary:.1f}")
            print(f"Количество предложений: {prelim.sentence_count}")
            print(f"Средняя длина предложения: {prelim.avg_sentence_length:.1f} слов")
            
            # Информация о слабых местах
            if prelim.identified_gaps:
                print(f"\nВыявленные слабые места:")
                for gap in prelim.identified_gaps[:3]:
                    print(f"   • {gap.description} ({gap.score:.1f})")
            
            # Рекомендации
            if prelim.recommendations:
                print(f"\nРекомендации:")
                for rec in prelim.recommendations:
                    print(f"   • {rec}")
            
            # Тестовые вопросы
            test_questions = result.get("recommended_test", [])
            print(f"\nРекомендовано тестовых вопросов: {len(test_questions)}")
            
            if result.get("test_reasoning"):
                print(f"Обоснование: {result.get('test_reasoning')}")
            
            print(f"\nВремя анализа: {prelim.processing_time:.2f} секунд")
            
        except ValueError as e:
            print(f"Ошибка валидации: {e}")
        except Exception as e:
            print(f"Ошибка анализа: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_proper())