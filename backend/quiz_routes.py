"""Quiz-focused backend routes for the cHEAL assistant."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request

from database.db import (
    attach_learning_support_logs_to_quiz,
    get_behavior_events,
    save_learning_support_log,
    save_quiz_question_responses,
    save_quiz_score,
)
from services.behavior_tracking_service import track_quiz_completed
from services.document_context import DocumentError, get_document_text
from services.llm_router import LLMRouterError
from services.progress_dashboard_service import calculate_quiz_comprehension_score
from services.quiz_service import (
    evaluate_mcq,
    evaluate_short_answer,
    evaluate_short_answer_locally,
    generate_mcq_quiz,
    generate_personalized_quiz_feedback,
    generate_short_questions,
)
from services.learner_model_service import refresh_learner_profiles_from_quiz
from services.learning_mode_effectiveness_service import finalize_learning_session_on_quiz

quiz_bp = Blueprint("quiz", __name__)
logger = logging.getLogger(__name__)

_ALLOWED_SUPPORT_TYPES = {
    "hint",
    "explain_again",
    "simplify",
    "example",
    "audio",
    "visual",
    "formula",
    "vocabulary",
    "diagram",
}


def _stamp_question_start_times(questions: list[dict[str, Any]], start_time: datetime) -> list[dict[str, Any]]:
    """Attach hidden timing metadata for API clients that submit the quiz unchanged."""
    start_value = start_time.isoformat()
    stamped_questions = []
    for question in questions:
        if isinstance(question, dict):
            stamped_questions.append({**question, "question_start_time": start_value})
    return stamped_questions


def _parse_question_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.utcfromtimestamp(value)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _infer_quiz_topic(quiz_data: list[dict[str, Any]]) -> str:
    for question in quiz_data:
        if isinstance(question, dict):
            topic = str(question.get("concept") or question.get("subcategory") or "").strip()
            if topic:
                return topic
    return "Document Quiz"


def _persist_api_question_timings(
    user_id: int | None,
    quiz_data: list[dict[str, Any]],
    report: dict[str, Any],
    question_timings: list[dict[str, Any]] | None,
) -> None:
    """Persist question-level timing for API quiz submissions when user data is supplied."""
    if user_id is None:
        return

    submit_time = datetime.utcnow()
    topic = _infer_quiz_topic(quiz_data)
    total_questions = len(quiz_data)
    quiz_accuracy = round((int(report.get("score") or 0) / total_questions) * 100.0, 1) if total_questions else 0.0
    avg_time_per_question = 0.0
    if total_questions:
        total_seconds = sum(
            max(0, int(round((submit_time - _parse_question_time(
                question.get("question_start_time") or question.get("start_time")
            )).total_seconds())))
            for question in quiz_data if isinstance(question, dict)
        )
        avg_time_per_question = round(total_seconds / total_questions, 1)

    weak_concepts = report.get("wrong_concepts") if isinstance(report.get("wrong_concepts"), list) else []
    comprehension_score = calculate_quiz_comprehension_score(
        quiz_accuracy=quiz_accuracy,
        conceptual_score=quiz_accuracy,
        support_count=0,
        total_questions=total_questions,
        first_attempt_success_rate=quiz_accuracy,
        avg_time_per_question=avg_time_per_question,
    ) if total_questions else 0.0
    feedback_fields = generate_personalized_quiz_feedback(
        quiz_accuracy=quiz_accuracy,
        conceptual_score=quiz_accuracy,
        avg_response_time=avg_time_per_question,
        support_count=0,
        total_questions=total_questions,
        first_attempt_success_rate=quiz_accuracy,
        weak_concepts=weak_concepts,
    )
    quiz_attempt = save_quiz_score(
        user_id=user_id,
        topic=topic,
        score=int(report.get("score") or 0),
        total_questions=total_questions,
        comprehension_score=comprehension_score,
        **feedback_fields,
    )

    question_results = report.get("question_results") or []
    timing_payload = question_timings or []
    records = []
    for index, question in enumerate(quiz_data):
        if not isinstance(question, dict):
            continue
        timing = timing_payload[index] if index < len(timing_payload) and isinstance(timing_payload[index], dict) else {}
        start_time = (
            _parse_question_time(timing.get("question_start_time"))
            or _parse_question_time(timing.get("start_time"))
            or _parse_question_time(question.get("question_start_time"))
            or submit_time
        )
        result = question_results[index] if index < len(question_results) and isinstance(question_results[index], dict) else {}
        is_correct = bool(result.get("is_correct"))
        records.append(
            {
                "user_id": user_id,
                "quiz_id": quiz_attempt.id,
                "question_id": str(question.get("question_id") or f"Q{index + 1:03d}"),
                "question_type": str(question.get("question_type") or "MCQ"),
                "topic": str(question.get("concept") or topic),
                "difficulty": str(question.get("difficulty") or ""),
                "question_start_time": start_time,
                "question_submit_time": submit_time,
                "time_taken_seconds": max(0, int(round((submit_time - start_time).total_seconds()))),
                "is_correct": is_correct,
                "attempt_number": 1,
                "first_attempt_success": is_correct,
            }
        )

    if records:
        save_quiz_question_responses(records)
        attach_learning_support_logs_to_quiz(
            user_id=user_id,
            quiz_id=quiz_attempt.id,
            question_ids=[record["question_id"] for record in records],
        )


@quiz_bp.get("/quiz/health")
def quiz_health() -> tuple[object, int]:
    """Return a simple health check for the quiz service."""
    return jsonify({"status": "Quiz service running"}), 200


@quiz_bp.post("/quiz/support-log")
def log_quiz_support_event() -> tuple[object, int]:
    """Record a learning support request without changing quiz evaluation flow."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    quiz_id = payload.get("quiz_id")
    question_id = str(payload.get("question_id") or "").strip()
    support_type = str(payload.get("support_type") or "").strip().lower()
    timestamp = _parse_question_time(payload.get("timestamp")) or datetime.utcnow()

    if not user_id or not question_id or not support_type:
        return jsonify({"success": False, "error": "user_id, question_id, and support_type are required."}), 400
    if support_type not in _ALLOWED_SUPPORT_TYPES:
        return jsonify({"success": False, "error": "Unsupported support_type."}), 400

    try:
        user_id_value = int(user_id)
        quiz_id_value = int(quiz_id) if quiz_id is not None else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "user_id and quiz_id must be integers when provided."}), 400

    try:
        log_record = save_learning_support_log(
            user_id=user_id_value,
            quiz_id=quiz_id_value,
            question_id=question_id,
            support_type=support_type,
            timestamp=timestamp,
        )
        return jsonify({"success": True, "support_log_id": log_record.id}), 200
    except Exception:
        logger.exception("Failed to save quiz support event")
        return jsonify({"success": False, "error": "Could not save support event."}), 500


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

        question_start_time = datetime.utcnow()
        mcqs = _stamp_question_start_times(generate_mcq_quiz(document_text, num_questions=num_mcqs), question_start_time)
        short_questions = _stamp_question_start_times(
            generate_short_questions(document_text, num_questions=num_short_questions),
            question_start_time,
        )

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
    question_timings = payload.get("question_timings")
    user_id = payload.get("user_id")

    if not isinstance(answers, list):
        return jsonify({"success": False, "error": "Answers must be a list."}), 400
    if not isinstance(quiz_data, list):
        return jsonify({"success": False, "error": "Quiz data must be provided as a list."}), 400
    if question_timings is not None and not isinstance(question_timings, list):
        return jsonify({"success": False, "error": "question_timings must be a list when provided."}), 400
    try:
        user_id_for_tracking = int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "user_id must be an integer when provided."}), 400

    try:
        report = evaluate_mcq(answers, quiz_data)
        try:
            _persist_api_question_timings(user_id_for_tracking, quiz_data, report, question_timings)
        except Exception:
            logger.exception("Failed to save API quiz timing data")

        if user_id_for_tracking is not None:
            try:
                total_questions = len(quiz_data)
                quiz_accuracy = round((int(report.get("score") or 0) / total_questions) * 100.0, 1) if total_questions else 0.0
                track_quiz_completed(
                    user_id=user_id_for_tracking,
                    metadata={
                        "quiz_accuracy": quiz_accuracy,
                        "score": quiz_accuracy,
                        "mode": "Quiz",
                    },
                )
                profile_result = refresh_learner_profiles_from_quiz(
                    user_id_for_tracking,
                    quiz_evaluation=report,
                )
                comprehension_score = profile_result.get("comprehension", {}).get("comprehension_score")
                if comprehension_score is None:
                    comprehension_score = quiz_accuracy
                finalize_learning_session_on_quiz(
                    user_id_for_tracking,
                    quiz_accuracy=quiz_accuracy,
                    comprehension_score=float(comprehension_score),
                    document_id=payload.get("document_id"),
                    document_name=payload.get("document_name"),
                    behavior_events=get_behavior_events(user_id_for_tracking, limit=500),
                )
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
