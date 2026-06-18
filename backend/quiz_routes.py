from flask import Blueprint, jsonify, request

from services.quiz_service import (
    generate_mcq_quiz,
    generate_short_questions,
    evaluate_mcq,
    evaluate_short_answer
)

from services.document_context import get_document_text


quiz_bp = Blueprint("quiz", __name__)

# Temporary storage
current_quiz = []


@quiz_bp.route("/quiz/generate", methods=["POST"])
def generate_quiz():

    global current_quiz

    try:
        document_text = get_document_text()

        if not document_text:
            return jsonify({
                "error": "No uploaded document found."
            }), 400

        mcqs = generate_mcq_quiz(document_text)
        short_questions = generate_short_questions(document_text)

        current_quiz = mcqs

        return jsonify({
            "success": True,
            "mcqs": mcqs,
            "short_questions": short_questions
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@quiz_bp.route("/quiz/submit", methods=["POST"])
def submit_quiz():

    global current_quiz

    try:
        data = request.get_json() or {}

        user_answers = data.get("answers", [])

        result = evaluate_mcq(
            user_answers=user_answers,
            quiz_data=current_quiz
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@quiz_bp.route("/quiz/evaluate-short", methods=["POST"])
def evaluate_short_question():

    try:
        data = request.get_json() or {}

        student_answer = data.get("student_answer", "")
        expected_answer = data.get("expected_answer", "")

        result = evaluate_short_answer(
            student_answer,
            expected_answer
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@quiz_bp.route("/quiz/health", methods=["GET"])
def health():

    return jsonify({
        "status": "Quiz service running"
    })