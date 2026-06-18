import json
import logging
import re

from services.gemini_service import chat_with_gemini

logger = logging.getLogger(__name__)


def extract_json(response_text):
    """
    Extract JSON from AI response.
    Handles markdown code blocks.
    """
    try:
        response_text = response_text.strip()

        response_text = re.sub(r"```json", "", response_text)
        response_text = re.sub(r"```", "", response_text)

        return json.loads(response_text)

    except Exception as e:
        logger.error(f"JSON extraction error: {e}")
        return None


def generate_mcq_quiz(text, num_questions=10):
    """
    Generate MCQ quiz from document text.
    """

    prompt = f"""
You are an educational quiz generator.

Generate {num_questions} multiple choice questions from the content below.

Return ONLY valid JSON.

Format:

[
  {{
    "question": "Question text",
    "options": [
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "answer": "Option A"
  }}
]

Content:
{text[:12000]}
"""

    try:
        response = chat_with_gemini(prompt)

        quiz = extract_json(response)

        if quiz is None:
            return []

        return quiz

    except Exception as e:
        logger.error(f"MCQ generation failed: {e}")
        return []


def generate_short_questions(text, num_questions=5):
    """
    Generate short answer questions.
    """

    prompt = f"""
Generate {num_questions} short-answer questions from the content below.

Return ONLY valid JSON.

Format:

[
  {{
    "question": "Question text",
    "answer": "Expected answer"
  }}
]

Content:
{text[:12000]}
"""

    try:
        response = chat_with_gemini(prompt)

        questions = extract_json(response)

        if questions is None:
            return []

        return questions

    except Exception as e:
        logger.error(f"Short question generation failed: {e}")
        return []


def evaluate_mcq(user_answers, quiz_data):
    """
    Evaluate MCQ responses.
    """

    score = 0
    total = len(quiz_data)

    results = []

    for i, question in enumerate(quiz_data):

        correct_answer = question.get("answer")

        user_answer = (
            user_answers[i]
            if i < len(user_answers)
            else None
        )

        is_correct = user_answer == correct_answer

        if is_correct:
            score += 1

        results.append({
            "question": question.get("question"),
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "correct": is_correct
        })

    percentage = round((score / total) * 100, 2) if total else 0

    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": results
    }


def evaluate_short_answer(student_answer, expected_answer):
    """
    AI-based short answer evaluation.
    """

    prompt = f"""
Evaluate the student's answer.

Expected Answer:
{expected_answer}

Student Answer:
{student_answer}

Return ONLY valid JSON.

{{
  "score": 0-5,
  "feedback": "Short feedback",
  "result": "Correct / Partially Correct / Incorrect"
}}
"""

    try:
        response = chat_with_gemini(prompt)

        evaluation = extract_json(response)

        if evaluation is None:
            return {
                "score": 0,
                "feedback": "Evaluation failed.",
                "result": "Incorrect"
            }

        return evaluation

    except Exception as e:
        logger.error(f"Short answer evaluation failed: {e}")

        return {
            "score": 0,
            "feedback": "Evaluation failed.",
            "result": "Incorrect"
        }