"""AI-powered hint generation service for quiz questions."""

from __future__ import annotations

import logging
from typing import Any

from services.llm_router import LLMRouterError, generate_content

logger = logging.getLogger(__name__)


def generate_quiz_hint(
    question: str,
    correct_answer: str,
    concept: str | None = None,
    question_type: str = "MCQ",
) -> str:
    """
    Generate a contextual, AI-powered hint for a quiz question.
    
    The hint guides the learner toward the correct concept without revealing the answer.
    
    Args:
        question: The quiz question text
        correct_answer: The correct answer (used for context, not revealed in hint)
        concept: The learning concept (optional, for better hint generation)
        question_type: Type of question (MCQ or Short Answer)
    
    Returns:
        A helpful hint string
        
    Raises:
        LLMRouterError: If LLM call fails
    """
    concept_hint = f"The main concept is '{concept}'." if concept else "Focus on the core concept."
    
    prompt = f"""Generate ONE helpful hint for this {question_type} question.

QUESTION: {question}

CORRECT ANSWER (do NOT mention this in the hint): {correct_answer}

REQUIREMENTS FOR THE HINT:
1. Guide the learner toward the concept WITHOUT revealing the answer
2. Use simple, dyslexia-friendly language
3. Ask a thinking question or provide a clue about what to consider
4. Maximum 2 sentences
5. {concept_hint}

Examples of GOOD hints:
- "Think about what happens when plants are exposed to light. What gas do they produce?"
- "This process involves the sun's energy being converted into what type of energy?"
- "Consider what the first step in the water cycle is called when water rises from the ground."

Examples of BAD hints (DO NOT USE):
- "The answer is Oxygen." (reveals answer)
- "Photosynthesis produces Oxygen." (mentions correct option)
- "It's one of the four steps in the cycle." (too vague)

Generate ONLY the hint text. No preamble or explanation."""

    try:
        hint = generate_content(prompt)
        hint = str(hint or "").strip()
        if hint:
            return hint
        else:
            return f"Think carefully about the concept of {concept or 'this topic'}."
    except LLMRouterError:
        logger.exception("Failed to generate hint via LLM, returning generic hint")
        return f"Think carefully about the concept of {concept or 'this topic'} and reconsider your understanding."


def generate_short_answer_hint(
    question: str,
    expected_answer: str,
    concept: str | None = None,
) -> str:
    """
    Generate a contextual hint for a short answer question.
    
    Args:
        question: The quiz question text
        expected_answer: The expected/correct answer (used for context, not revealed)
        concept: The learning concept (optional)
    
    Returns:
        A helpful hint string
    """
    return generate_quiz_hint(
        question=question,
        correct_answer=expected_answer,
        concept=concept,
        question_type="Short Answer",
    )
