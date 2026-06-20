"""Intelligent quiz generation and evaluation for the cHEAL assistant."""

from __future__ import annotations

import ast
import difflib
import json
import logging
import re
import time
from collections import Counter
from typing import Any

from services.llm_router import LLMRouterError, generate_content

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "about",
    "after",
    "answer",
    "because",
    "before",
    "between",
    "correct",
    "define",
    "describe",
    "does",
    "during",
    "explain",
    "from",
    "happen",
    "happens",
    "important",
    "means",
    "name",
    "process",
    "question",
    "should",
    "student",
    "these",
    "this",
    "through",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "your",
    "cause",
    "causes",
    "cycle",
    "idea",
    "main",
}

_CONCEPT_KEYWORDS = [
    "groundwater",
    "evaporation",
    "condensation",
    "precipitation",
    "collection",
    "photosynthesis",
    "chlorophyll",
    "mitochondria",
    "nucleus",
    "cell membrane",
    "cell structure",
    "networking",
    "router",
    "internet",
    "algorithm",
]


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
    start_time = time.perf_counter()
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
        concept = str(question_item.get("concept") or "").strip() or _infer_concept(question, correct_answer)

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
                "concept": concept,
            }
        )

    percentage = round((correct_count / total) * 100) if total else 0

    analysis = _generate_mcq_learning_report(question_feedback)

    total_attempted = len(question_feedback)
    report: dict[str, Any] = {
        "score": correct_count,
        "total": total,
        "percentage": percentage,
        "correct_answers": correct_count,
        "incorrect_answers": total - correct_count,
        "strengths": _build_strengths_summary(correct_count, total_attempted),
        "weaknesses": _build_weaknesses_summary(total - correct_count, total_attempted),
        "recommendations": _build_recommendation_summary(total - correct_count, total_attempted),
        "evaluations": analysis.get("evaluations", []),
    }

    logger.info("[Quiz] MCQ evaluation completed in %.2fs", time.perf_counter() - start_time)
    return report


def evaluate_short_answer(
    student_answer: str,
    expected_answer: str,
    question_text: str | None = None,
) -> dict[str, Any]:
    """Evaluate a short answer semantically and return friendly feedback."""
    start_time = time.perf_counter()
    logger.info("[Quiz] Starting short-answer evaluation")
    student_answer_text = str(student_answer or "").strip()
    expected_answer_text = str(expected_answer or "").strip()
    question_text = str(question_text or "").strip()

    if not expected_answer_text:
        evaluation = _fallback_short_answer_evaluation(student_answer_text, expected_answer_text, question_text)
        logger.info("[Quiz] Short answer local evaluation completed in %.2fs", time.perf_counter() - start_time)
        return evaluation
    if not student_answer_text:
        evaluation = _fallback_short_answer_evaluation(student_answer_text, expected_answer_text, question_text)
        logger.info("[Quiz] Short answer local evaluation completed in %.2fs", time.perf_counter() - start_time)
        return evaluation

    local_evaluation = _fallback_short_answer_evaluation(student_answer_text, expected_answer_text, question_text)
    local_score = _safe_int(local_evaluation.get("score"), default=0)
    if local_score >= 4 or local_score <= 1:
        logger.info("[Quiz] Short answer local evaluation completed in %.2fs", time.perf_counter() - start_time)
        return local_evaluation

    prompt = (
        "Compare the student answer to the expected answer. "
        "Evaluate the response based on meaning, not exact wording. "
        "Return only a JSON object with the fields:\n"
        "- score (integer between 0 and 5)\n"
        "- max_score (integer)\n"
        "- result (\"Perfectly Correct\", \"Partially Correct\", or \"Incorrect\")\n"
        "- concept (2-4 words naming the topic)\n"
        "- feedback\n"
        "- improvement_tip\n"
        "Rules:\n"
        "- feedback must be 1-2 short sentences.\n"
        "- improvement_tip must be 1 question-specific sentence.\n"
        "- Do not use generic tips like 'review the key idea'.\n"
        "- Keep language simple and dyslexia-friendly."
        f"\n\nQUESTION:\n{question_text or 'Short answer question'}\n\n"
        f"EXPECTED ANSWER:\n{expected_answer_text}\n\n"
        f"STUDENT ANSWER:\n{student_answer_text}"
    )

    try:
        response = _run_quiz_prompt(prompt)
        evaluation = _parse_json_response(response)
        if not isinstance(evaluation, dict):
            raise ValueError("Short answer evaluation did not return a JSON object.")
    except Exception:
        logger.exception(
            "[Quiz Evaluation] Short answer failed using LLM router. Question: %s. Falling back to local evaluation.",
            question_text or "<unknown>",
        )
        logger.info("[Quiz] Short answer local fallback completed in %.2fs", time.perf_counter() - start_time)
        return local_evaluation

    concept = str(evaluation.get("concept") or "").strip() or _infer_concept("", expected_answer_text)
    evaluation.setdefault("max_score", 5)
    evaluation.setdefault("score", 0)
    evaluation.setdefault("result", "Partially Correct")
    evaluation["concept"] = concept
    evaluation["feedback"] = _shorten_sentences(
        str(evaluation.get("feedback") or ""),
        fallback=_build_short_feedback(concept, expected_answer_text),
        max_sentences=2,
    )
    evaluation["improvement_tip"] = _shorten_sentences(
        str(evaluation.get("improvement_tip") or ""),
        fallback=_build_tip(concept, expected_answer_text),
        max_sentences=1,
    )

    if not isinstance(evaluation["score"], int):
        try:
            evaluation["score"] = int(str(evaluation["score"]).strip())
        except Exception:
            evaluation["score"] = local_score

    evaluation["score"] = max(0, min(5, evaluation["score"]))
    evaluation["source"] = "llm"
    logger.info("[Quiz] Short answer LLM evaluation completed in %.2fs", time.perf_counter() - start_time)
    return evaluation


def evaluate_short_answer_locally(
    student_answer: str,
    expected_answer: str,
    question_text: str | None = None,
) -> dict[str, Any]:
    """Evaluate a short answer without any LLM dependency."""
    return _fallback_short_answer_evaluation(
        str(student_answer or "").strip(),
        str(expected_answer or "").strip(),
        str(question_text or "").strip(),
    )


def combine_quiz_report_with_short_answers(
    mcq_report: dict[str, Any],
    short_feedback: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge short-answer evaluations into a question-by-question quiz report."""
    report = dict(mcq_report)
    evaluations = list(report.get("evaluations") or [])
    correct_count = _safe_int(report.get("correct_answers"), default=_safe_int(report.get("score"), default=0))
    total_count = _safe_int(report.get("total"), default=0)
    weak_count = _safe_int(report.get("incorrect_answers"), default=max(total_count - correct_count, 0))

    for item in short_feedback:
        evaluation = item.get("evaluation", {}) if isinstance(item, dict) else {}
        score = _safe_int(evaluation.get("score"), default=0)
        max_score = max(_safe_int(evaluation.get("max_score"), default=5), 1)
        question = str(item.get("question", "")).strip()
        expected_answer = str(item.get("expected_answer", "")).strip()
        student_answer = str(item.get("student_answer", "")).strip()
        result = _result_from_score(score, max_score)
        total_count += 1
        if result == "Correct":
            correct_count += 1
        else:
            weak_count += 1

        evaluations.append(
            {
                "question": question,
                "your_answer": student_answer or "No answer",
                "correct_answer": expected_answer,
                "result": result,
                "explanation": _shorten_sentences(
                    str(evaluation.get("feedback") or ""),
                    fallback=_build_question_explanation(question, student_answer, expected_answer, result),
                    max_sentences=3,
                ),
            }
        )

    report["evaluations"] = evaluations
    report["score"] = correct_count
    report["total"] = total_count
    report["percentage"] = round((correct_count / total_count) * 100) if total_count else 0
    report["correct_answers"] = correct_count
    report["incorrect_answers"] = weak_count
    report["strengths"] = _build_strengths_summary(correct_count, total_count)
    report["weaknesses"] = _build_weaknesses_summary(weak_count, total_count)
    report["recommendations"] = _build_recommendation_summary(weak_count, total_count)
    return report


def _fallback_short_answer_evaluation(
    student_answer: str,
    expected_answer: str,
    question_text: str = "",
) -> dict[str, Any]:
    """Evaluate a short answer locally with token overlap and sequence similarity."""
    concept = _infer_concept(question_text, expected_answer)
    student_tokens = _content_tokens(student_answer)
    expected_tokens = _content_tokens(expected_answer)

    if not student_tokens:
        score = 0
    elif not expected_tokens:
        score = 1
    else:
        overlap = len(student_tokens & expected_tokens) / max(len(expected_tokens), 1)
        sequence = difflib.SequenceMatcher(
            None,
            _normalize_answer(student_answer),
            _normalize_answer(expected_answer),
        ).ratio()
        similarity = (overlap * 0.65) + (sequence * 0.35)
        score = round(similarity * 5)

    score = max(0, min(5, score))
    if score >= 4:
        result = "Perfectly Correct"
        feedback = f"Good answer on {concept}. You included the main idea."
    elif score >= 2:
        result = "Partially Correct"
        feedback = "Basic evaluation completed. Some key details are missing."
    else:
        result = "Incorrect"
        feedback = "Basic evaluation completed. The answer misses the key idea."

    return {
        "score": score,
        "max_score": 5,
        "result": result,
        "concept": concept,
        "feedback": _shorten_sentences(feedback, fallback="Basic evaluation completed.", max_sentences=2),
        "improvement_tip": _build_tip(concept, expected_answer) or "Review the key concept.",
        "source": "local",
    }


def _run_quiz_prompt(prompt: str, document_text: str | None = None) -> str:
    full_prompt = prompt
    if document_text is not None:
        full_prompt = (
            f"{prompt}\n\n"
            "DOCUMENT CONTENT:\n"
            f"{document_text.strip()}"
        )

    try:
        return generate_content(full_prompt)
    except LLMRouterError:
        raise
    except Exception as exc:
        logger.exception("Unexpected quiz service error.")
        raise LLMRouterError("Quiz generation is temporarily unavailable.") from exc


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


def _content_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z-]+", str(text or "").lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _generate_mcq_learning_report(question_feedback: list[dict[str, Any]]) -> dict[str, Any]:
    evaluations = []

    for item in question_feedback:
        question = str(item.get("question", "")).strip()
        student_answer = str(item.get("student_answer", "")).strip() or "No answer"
        correct_answer = str(item.get("correct_answer", "")).strip()
        result = "Correct" if item.get("is_correct") else "Incorrect"
        evaluations.append(
            {
                "question": question,
                "your_answer": student_answer,
                "correct_answer": correct_answer,
                "result": result,
                "explanation": _build_question_explanation(question, student_answer, correct_answer, result),
            }
        )

    return {"evaluations": evaluations}


def _result_from_score(score: int, max_score: int) -> str:
    if score >= max_score * 0.8:
        return "Correct"
    if score >= max_score * 0.4:
        return "Partially Correct"
    return "Incorrect"


def _build_strengths_summary(correct_count: int, total_count: int) -> str:
    if total_count <= 0:
        return "Complete the quiz to see a summary of your strengths."

    if correct_count == total_count:
        return (
            "You demonstrated a strong understanding of the quiz material. "
            "Your answers consistently matched the expected ideas and showed clear recall."
        )
    if correct_count >= max(1, round(total_count * 0.6)):
        return (
            "You showed a good understanding of many core ideas in the quiz. "
            "Several answers correctly identified the main concepts, even where some details could be stronger."
        )
    if correct_count > 0:
        return (
            "You correctly answered some parts of the quiz, which shows a starting understanding of the material. "
            "Build on those correct answers by reviewing how each idea connects to the question."
        )
    return (
        "You attempted the quiz and created a clear starting point for review. "
        "Use the question evaluations below to focus on the ideas that need more practice."
    )


def _build_weaknesses_summary(weak_count: int, total_count: int) -> str:
    if total_count <= 0 or weak_count <= 0:
        return "No major weaknesses were identified in this attempt."

    if weak_count == total_count:
        return (
            "Most answers did not match the expected ideas yet. "
            "Focus on reading each question carefully and connecting your answer to the key fact being asked."
        )
    if weak_count >= max(1, round(total_count * 0.5)):
        return (
            "Some answers identified the general idea but missed important supporting details. "
            "Review the explanations below and practice answering with one clear reason or example."
        )
    return (
        "Only a few answers need improvement. "
        "Those responses were close, but they need more precise wording or one extra supporting detail."
    )


def _build_recommendation_summary(weak_count: int, total_count: int) -> str:
    if total_count <= 0:
        return "Generate and complete a quiz to receive a focused recommendation."
    if weak_count <= 0:
        return "Keep practicing with a harder quiz or explain the answers aloud to strengthen recall."
    return (
        "Review the questions marked incorrect or partially correct, then rewrite each answer in one clear sentence. "
        "Focus on why the correct answer fits the question."
    )


def _build_question_explanation(question: str, student_answer: str, correct_answer: str, result: str) -> str:
    question = _trim_text(question, max_words=18)
    correct_answer = _trim_text(correct_answer, max_words=18)
    student_answer = _trim_text(student_answer, max_words=18)

    if result == "Correct":
        return (
            f"Your answer matches the expected answer for this question. "
            f"The key idea is: {correct_answer}."
        )
    if result == "Partially Correct":
        return (
            f"Your answer is partly connected to the question, but it does not fully explain the expected idea. "
            f"A stronger answer would include: {correct_answer}."
        )
    return (
        f"This question asks about {question}. "
        f"Your answer, {student_answer}, does not match the expected idea: {correct_answer}."
    )


def _infer_concept(question: str, answer: str) -> str:
    text = f"{question} {answer}".strip()
    lowered = text.lower()
    for keyword in _CONCEPT_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            return keyword.title()

    phrases = re.findall(r"\b[A-Za-z][A-Za-z-]{3,}(?:\s+[A-Za-z][A-Za-z-]{3,})?\b", text)
    candidates = []
    for phrase in phrases:
        words = [
            word
            for word in re.findall(r"[A-Za-z][A-Za-z-]+", phrase.lower())
            if word not in _STOPWORDS
        ]
        if not words:
            continue
        candidates.append(" ".join(words[:2]).title())

    if candidates:
        return Counter(candidates).most_common(1)[0][0]

    words = [word for word in re.findall(r"[A-Za-z]+", text.lower()) if len(word) > 2 and word not in _STOPWORDS]
    if words:
        return words[0].title()
    return "Core Concept"


def _build_mcq_feedback(concept: str, correct_answer: str) -> str:
    answer = _trim_text(correct_answer, max_words=14)
    return f"This question was about {concept}. The key answer is {answer}."


def _build_short_feedback(concept: str, expected_answer: str) -> str:
    answer = _trim_text(expected_answer, max_words=14)
    return f"You were close on {concept}. Include this key idea: {answer}."


def _build_tip(concept: str, correct_answer: str) -> str:
    answer = _trim_text(correct_answer, max_words=10)
    if answer:
        return f"Link {concept} with: {answer}."
    return f"Focus on what {concept} means in the document."


def _build_recommendations(weaknesses: list[str], strengths: list[str]) -> list[str]:
    if weaknesses:
        weak_text = _format_concept_list(weaknesses[:3])
        recommendations = [f"You struggled with {weak_text}. Review those sections before retaking the quiz."]
        if strengths:
            recommendations.append(f"Keep using your strength in {_format_concept_list(strengths[:2])} to connect ideas.")
        recommendations.append("Retake only the missed topics first, then try the full quiz again.")
        return recommendations

    if strengths:
        return [f"Great work on {_format_concept_list(strengths[:3])}. Try a harder quiz next."]
    return ["Answer more questions so the system can find your learning pattern."]


def _build_revision_material(weaknesses: list[str], mistakes: list[dict[str, Any]]) -> list[dict[str, str]]:
    revision = []
    for concept in weaknesses:
        related = next((item for item in mistakes if item.get("concept") == concept), {})
        correct_answer = str(related.get("correct_answer") or "").strip()
        note = _trim_text(correct_answer, max_words=18)
        revision.append(
            {
                "topic": concept,
                "revision_note": f"{concept}: {note}" if note else f"Review the main idea of {concept}.",
                "practice_question": _build_practice_question(concept, correct_answer),
            }
        )
    return revision


def _build_practice_question(concept: str, correct_answer: str) -> str:
    if correct_answer:
        return f"How would you explain {concept} using this idea?"
    return f"What is the main idea of {concept}?"


def _rank_weaknesses(concepts: list[str]) -> list[str]:
    counts = Counter(concept for concept in concepts if concept)
    return [concept for concept, _ in counts.most_common()]


def _unique_preserving_order(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        clean = str(item or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        unique.append(clean)
    return unique


def _format_concept_list(concepts: list[str]) -> str:
    concepts = _unique_preserving_order(concepts)
    if not concepts:
        return "the missed topics"
    if len(concepts) == 1:
        return concepts[0]
    if len(concepts) == 2:
        return f"{concepts[0]} and {concepts[1]}"
    return f"{', '.join(concepts[:-1])}, and {concepts[-1]}"


def _shorten_sentences(text: str, fallback: str, max_sentences: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "").strip()) or fallback
    sentences = re.split(r"(?<=[.!?])\s+", text)
    short = " ".join(sentence.strip() for sentence in sentences[:max_sentences] if sentence.strip())
    return _trim_text(short or fallback, max_words=28 if max_sentences > 1 else 16)


def _trim_text(text: str, max_words: int) -> str:
    words = str(text or "").strip().split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,;:") + "."


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default
