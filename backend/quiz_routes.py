"""Quiz-focused backend routes for the cHEAL assistant."""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from services.document_context import DocumentError, get_document_text
from services.llm_router import LLMRouterError
from services.quiz_service import (
    evaluate_mcq,
    evaluate_short_answer,
    evaluate_short_answer_locally,
    generate_mcq_quiz,
    generate_short_questions,
)
from services.learner_model_service import calculate_comprehension_score
from database.db import save_learner_comprehension_profile

quiz_bp = Blueprint("quiz", __name__)
logger = logging.getLogger(__name__)


@quiz_bp.get("/quiz/health")
def quiz_health() -> tuple[object, int]:
    """Return a simple health check for the quiz service."""
    return jsonify({"status": "Quiz service running"}), 200


@quiz_bp.post("/quiz/generate")
def generate_quiz() -> tuple[object, int]:
    """Generate MCQs and short answer questions from the current document."""
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id")
    num_mcqs = payload.get("num_mcqs", 10)
    num_short_questions = payload.get("num_short_questions", 5)

    try:
        document_text = get_document_text(document_id)
        if not document_text:
            return jsonify({"success": False, "error": "Upload a document before generating a quiz."}), 400

        mcqs = generate_mcq_quiz(document_text, num_questions=num_mcqs)
        short_questions = generate_short_questions(document_text, num_questions=num_short_questions)

        return jsonify({"success": True, "mcqs": mcqs, "short_questions": short_questions}), 200
    except DocumentError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except LLMRouterError:
        logger.exception("Quiz generation failed through LLM router")
        return jsonify({"success": False, "error": "Quiz generation is temporarily unavailable."}), 503
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        logger.exception("Unexpected quiz generation route error")
        return jsonify({"success": False, "error": "Unexpected server error."}), 500


@quiz_bp.post("/quiz/submit")
def submit_quiz() -> tuple[object, int]:
    """Submit MCQ answers and receive an intelligent learning report."""
    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers")
    quiz_data = payload.get("quiz_data")
    user_id = payload.get("user_id")

    if not isinstance(answers, list):
        return jsonify({"success": False, "error": "Answers must be a list."}), 400
    if not isinstance(quiz_data, list):
        return jsonify({"success": False, "error": "Quiz data must be provided as a list."}), 400

    try:
        report = evaluate_mcq(answers, quiz_data)
        if user_id is not None:
            try:
                learner_model_result = calculate_comprehension_score(report)
                save_learner_comprehension_profile(int(user_id), learner_model_result)
            except Exception:
                logger.exception("Failed to persist learner comprehension profile")
        return jsonify({"success": True, "report": report}), 200
    except (LLMRouterError, ValueError):
        logger.exception("Quiz submission evaluation failed. Returning local fallback report.")
        total = len(quiz_data)
        return jsonify({
            "success": True,
            "report": {
                "score": 0,
                "total": total,
                "percentage": 0,
                "correct_answers": 0,
                "incorrect_answers": total,
                "mistakes": [],
                "strengths": [],
                "weaknesses": ["Core Concept"] if total else [],
                "recommendations": ["Review the quiz material and try the questions again."],
                "revision_material": [
                    {
                        "topic": "Core Concept",
                        "revision_note": "Review the main ideas from the uploaded document.",
                        "practice_question": "What are the most important ideas in this topic?",
                    }
                ] if total else [],
            },
        }), 200
    except Exception:
        logger.exception("Unexpected quiz submission route error. Returning local fallback report.")
        total = len(quiz_data)
        return jsonify({
            "success": True,
            "report": {
                "score": 0,
                "total": total,
                "percentage": 0,
                "correct_answers": 0,
                "incorrect_answers": total,
                "mistakes": [],
                "strengths": [],
                "weaknesses": ["Core Concept"] if total else [],
                "recommendations": ["Review the quiz material and try the questions again."],
                "revision_material": [
                    {
                        "topic": "Core Concept",
                        "revision_note": "Review the main ideas from the uploaded document.",
                        "practice_question": "What are the most important ideas in this topic?",
                    }
                ] if total else [],
            },
        }), 200


@quiz_bp.post("/quiz/evaluate-short")
def evaluate_short() -> tuple[object, int]:
    """Evaluate a single short answer response intelligently."""
    payload = request.get_json(silent=True) or {}
    student_answer = payload.get("student_answer")
    expected_answer = payload.get("expected_answer")

    try:
        evaluation = evaluate_short_answer(student_answer, expected_answer)
        return jsonify({"success": True, "evaluation": evaluation}), 200
    except (LLMRouterError, ValueError):
        logger.exception("Short answer evaluation failed. Returning local fallback result.")
        evaluation = evaluate_short_answer_locally(student_answer, expected_answer)
        return jsonify({"success": True, "evaluation": evaluation}), 200
    except Exception:
        logger.exception("Unexpected short answer route error. Returning local fallback result.")
        evaluation = evaluate_short_answer_locally(student_answer, expected_answer)
        return jsonify({"success": True, "evaluation": evaluation}), 200
