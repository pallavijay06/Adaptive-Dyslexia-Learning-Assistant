"""Intelligent quiz generation and evaluation for the cHEAL assistant."""

from __future__ import annotations

import ast
import json
import logging
import re
from typing import Any

from services.gemini_service import (
    GeminiAPIError,
    GeminiConfigurationError,
    GeminiServiceError,
    chat_with_gemini,
)

logger = logging.getLogger(__name__)


def generate_mcq_quiz(text: str, num_questions: int = 10) -> list[dict[str, str]]:
    """Generate high-quality multiple choice questions from document content."""
    if not text or not text.strip():
        raise ValueError("Document text cannot be empty for quiz generation.")

    prompt = (
        "Generate a learner-friendly multiple choice quiz from the document below. "
        f"Create exactly {num_questions} questions. "
        "For each question, return a JSON object with the keys:\n"
        "- question\n"
        "- options (a list of exactly 4 answer choices)\n"
        "- answer (the correct answer exactly as one of the options)\n"
        "Do not add any additional text outside the JSON array. "
        "Use simple language and keep answer choices clear and short."
    )

    response = _run_quiz_prompt(prompt, text)
    mcqs = _parse_json_response(response)
    if not isinstance(mcqs, list):
        raise ValueError("Expected a list of MCQ objects from the quiz generator.")

    validated_mcqs = []
    for item in mcqs:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        options = item.get("options") or []
        answer = str(item.get("answer", "")).strip()
        if not question or not answer or not isinstance(options, list) or len(options) != 4:
            continue
        validated_mcqs.append(
            {
                "question": question,
                "options": [str(opt).strip() for opt in options],
                "answer": answer,
            }
        )

    if not validated_mcqs:
        raise ValueError("Quiz generation did not return valid multiple choice questions.")

    return validated_mcqs


def generate_short_questions(text: str, num_questions: int = 5) -> list[dict[str, str]]:
    """Generate short answer questions from document content."""
    if not text or not text.strip():
        raise ValueError("Document text cannot be empty for short question generation.")

    prompt = (
        "Create a list of learner-friendly short answer questions from the document below. "
        f"Generate exactly {num_questions} questions. "
        "Return only a JSON array where each element has the keys:\n"
        "- question\n"
        "- answer\n"
        "Use simple language and keep the expected answers concise."
    )

    response = _run_quiz_prompt(prompt, text)
    questions = _parse_json_response(response)
    if not isinstance(questions, list):
        raise ValueError("Expected a list of short answer question objects.")

    validated_questions = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if not question or not answer:
            continue
        validated_questions.append({"question": question, "answer": answer})

    if not validated_questions:
        raise ValueError("Short question generation did not return valid output.")

    return validated_questions


def evaluate_mcq(user_answers: list[str], quiz_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate MCQ answers and provide a full learning report."""
    if not isinstance(user_answers, list):
        raise ValueError("User answers must be a list.")
    if not isinstance(quiz_data, list):
        raise ValueError("Quiz data must be a list of MCQ questions.")
    if len(user_answers) != len(quiz_data):
        raise ValueError("Number of answers must match number of quiz questions.")

    total = len(quiz_data)
    correct_count = 0
    question_feedback = []

    for index, (question_item, student_answer) in enumerate(zip(quiz_data, user_answers), start=1):
        question = str(question_item.get("question", "")).strip()
        correct_answer = str(question_item.get("answer", "")).strip()
        options = [str(option).strip() for option in question_item.get("options", []) if option is not None]
        student_answer = str(student_answer or "").strip()

        is_correct = _compare_mcq_answers(student_answer, correct_answer, options)
        if is_correct:
            correct_count += 1

        question_feedback.append(
            {
                "question": question,
                "student_answer": student_answer,
                "correct_answer": correct_answer,
                "options": options,
                "is_correct": is_correct,
            }
        )

    percentage = round((correct_count / total) * 100) if total else 0

    try:
        analysis = _generate_mcq_learning_report(question_feedback)
    except Exception as exc:
        logger.exception("Quiz analysis generation failed.")
        analysis = {
            "strengths": [],
            "weaknesses": [],
            "recommendations": [
                "Review the document and try the quiz again."
            ],
            "mistakes": [],
            "revision_material": [],
        }

    report: dict[str, Any] = {
        "score": correct_count,
        "total": total,
        "percentage": percentage,
        "correct_answers": correct_count,
        "incorrect_answers": total - correct_count,
        "mistakes": analysis.get("mistakes", []),
        "strengths": analysis.get("strengths", []),
        "weaknesses": analysis.get("weaknesses", []),
        "recommendations": analysis.get("recommendations", []),
        "revision_material": analysis.get("revision_material", []),
    }

    return report


def evaluate_short_answer(student_answer: str, expected_answer: str) -> dict[str, Any]:
    """Evaluate a short answer semantically and return friendly feedback."""
    student_answer_text = str(student_answer or "").strip()
    expected_answer_text = str(expected_answer or "").strip()

    if not expected_answer_text:
        raise ValueError("Expected answer cannot be empty.")
    if not student_answer_text:
        raise ValueError("Student answer cannot be empty.")

    prompt = (
        "Compare the student answer to the expected answer. "
        "Evaluate the response based on meaning, not exact wording. "
        "Return only a JSON object with the fields:\n"
        "- score (integer between 0 and 5)\n"
        "- max_score (integer)\n"
        "- result (\"Perfectly Correct\", \"Partially Correct\", or \"Incorrect\")\n"
        "- feedback\n"
        "- improvement_tip\n"
        "Be kind, clear, and explain why the answer is correct or where it is missing the main idea."
        f"\n\nEXPECTED ANSWER:\n{expected_answer_text}\n\n"
        f"STUDENT ANSWER:\n{student_answer_text}"
    )

    response = _run_quiz_prompt(prompt)
    evaluation = _parse_json_response(response)
    if not isinstance(evaluation, dict):
        raise ValueError("Short answer evaluation did not return a JSON object.")

    evaluation.setdefault("max_score", 5)
    evaluation.setdefault("score", 0)
    evaluation.setdefault("result", "Partially Correct")
    evaluation.setdefault("feedback", "Could not determine evaluation. Please try again.")
    evaluation.setdefault("improvement_tip", "Review the key idea and answer it in your own words.")

    if not isinstance(evaluation["score"], int):
        try:
            evaluation["score"] = int(str(evaluation["score"]).strip())
        except Exception:
            evaluation["score"] = 0

    return evaluation


def _run_quiz_prompt(prompt: str, document_text: str | None = None) -> str:
    try:
        return chat_with_gemini(prompt, document_text=document_text)
    except (GeminiConfigurationError, GeminiAPIError):
        raise
    except Exception as exc:
        logger.exception("Unexpected quiz service error.")
        raise GeminiAPIError(f"Quiz service failed: {exc}") from exc


def _parse_json_response(text: str) -> Any:
    payload = _extract_json_payload(text)
    if not payload:
        raise ValueError("No JSON payload found in model response.")

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(payload)
        except Exception as exc:
            logger.exception("JSON parsing failed for quiz service response.")
            raise ValueError("Could not parse the model response as JSON.") from exc


def _extract_json_payload(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    # Attempt to locate the first JSON array or object block.
    array_match = re.search(r"(\[\s*\{.*\}\s*\])", text, re.S)
    if array_match:
        return array_match.group(1)

    object_match = re.search(r"(\{.*\})", text, re.S)
    if object_match:
        return object_match.group(1)

    # Fallback to the first bracketed JSON content.
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text


def _compare_mcq_answers(
    student_answer: str,
    correct_answer: str,
    options: list[str],
) -> bool:
    normalized_student = _normalize_answer(student_answer)
    normalized_correct = _normalize_answer(correct_answer)

    if normalized_student == normalized_correct:
        return True

    # If student selected a letter, map to the corresponding option text when possible.
    if normalized_student in {"a", "b", "c", "d"} and len(options) == 4:
        index = ord(normalized_student) - ord("a")
        if 0 <= index < len(options):
            return _normalize_answer(options[index]) == normalized_correct

    # Compare option text values ignoring letter prefixes.
    for option in options:
        if _normalize_answer(option) == normalized_student:
            return _normalize_answer(option) == normalized_correct

    return False


def _normalize_answer(answer: str) -> str:
    clean = str(answer or "").strip().lower()
    clean = re.sub(r"^\s*[abcd]\s*[\).:-]*\s*", "", clean)
    return re.sub(r"\s+", " ", clean)


def _generate_mcq_learning_report(question_feedback: list[dict[str, Any]]) -> dict[str, Any]:
    prompt_lines = [
        "Evaluate this quiz performance and return a JSON object with the following fields:",
        "- strengths: list of strong topics or concepts",
        "- weaknesses: list of weak topics or concepts",
        "- recommendations: list of short personalized recommendations",
        "- mistakes: list of objects with question, student_answer, correct_answer, mistake_explanation, correct_concept",
        "- revision_material: list of objects with topic, simple_explanation, revision_note, practice_question",
        "Use simple, learner-friendly language." ,
        "Include only the requested fields. Do not include score calculations.",
        "Quiz feedback should be based on the student answers and the correct answers provided."
    ]

    quiz_items = []
    for item in question_feedback:
        quiz_items.append(
            {
                "question": item["question"],
                "student_answer": item["student_answer"],
                "correct_answer": item["correct_answer"],
                "is_correct": item["is_correct"],
            }
        )

    prompt = (
        "\n".join(prompt_lines)
        + "\n\nQUIZ ITEMS:\n"
        + json.dumps(quiz_items, indent=2, ensure_ascii=False)
    )

    response = _run_quiz_prompt(prompt)
    report = _parse_json_response(response)
    if not isinstance(report, dict):
        raise ValueError("Learning report must be a JSON object.")

    report.setdefault("strengths", [])
    report.setdefault("weaknesses", [])
    report.setdefault("recommendations", [])
    report.setdefault("mistakes", [])
    report.setdefault("revision_material", [])
    return report
