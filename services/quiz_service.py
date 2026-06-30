"""Intelligent quiz generation and evaluation for the cHEAL assistant."""

from __future__ import annotations

import ast
import copy
import difflib
import json
import logging
import random
import re
import time
from collections import Counter
from typing import Any

from services.cache_service import (
    QUIZ_CACHE_TTL_HOURS,
    get_cache_value,
    make_quiz_cache_key,
    set_cache_value,
)
from services.llm_router import LLMRouterError, generate_content
import traceback
import inspect

logger = logging.getLogger(__name__)

_QUIZ_GENERATION_FALLBACK_USED = False
_QUIZ_RESPONSE_TRUNCATED = False

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

_SYNONYM_MAP = {
    "produce": "make",
    "produces": "make",
    "produced": "make",
    "clorophyll": "chlorophyll",
    "photosyntesis": "photosynthesis",
    "photosythesis": "photosynthesis",
    "evapouration": "evaporation",
    "oxyen": "oxygen",
    "oxigen": "oxygen",
    "oxegen": "oxygen",
}

# Concept equivalences for semantic matching and richer explanations
_CONCEPT_EQUIVALENCE = {
    "chlorophyll": {"green", "green pigment"},
    "oxygen": {"oxygen", "o2", "release oxygen", "give out oxygen"},
    "carbon dioxide": {"carbon dioxide", "co2"},
    "photosynthesis": {"photosynthesis", "making food", "make food", "produce food", "create food"},
}

_ALLOWED_DIFFICULTIES = ("Easy", "Medium", "Hard")
_ALLOWED_SKILLS = (
    "Concept Understanding",
    "Definition Recall",
    "Formula Application",
    "Numerical Problem Solving",
    "Diagram Interpretation",
    "Real-world Application",
)


def generate_mcq_quiz(text: str, num_questions: int = 10) -> list[dict[str, str]]:
    """Generate high-quality multiple choice questions from document content."""
    global _QUIZ_GENERATION_FALLBACK_USED
    if not text or not text.strip():
        raise ValueError("Document text cannot be empty for quiz generation.")

    _QUIZ_GENERATION_FALLBACK_USED = False

    cache_key = make_quiz_cache_key(text, "mcq", num_questions)
    cached_mcqs = get_cache_value(cache_key)
    if cached_mcqs is not None:
        logger.info("[CACHE HIT] Quiz MCQ")
        return _ensure_quiz_metadata(copy.deepcopy(cached_mcqs), "MCQ")
    logger.info("[CACHE MISS] Quiz MCQ")

    prompt = _build_mcq_generation_prompt(num_questions)

    requested_questions = num_questions
    retry_attempted = False
    try:
        response = _run_quiz_prompt(prompt, text)
        # Log raw response from LLM for instrumentation
        try:
            logger.info("[Quiz Gen] Raw LLM response (len=%s)", len(response) if response is not None else 0)
            logger.debug("[Quiz Gen] Raw LLM response head: %s", (response or "")[:300])
            logger.debug("[Quiz Gen] Raw LLM response tail: %s", (response or "")[-150:])
        except Exception:
            logger.exception("[Quiz Gen] Failed to log raw LLM response")

        mcqs = _parse_json_response(response)
        # If parser detected truncation, perform one retry with half the requested questions
        global _QUIZ_RESPONSE_TRUNCATED
        if mcqs is None and _QUIZ_RESPONSE_TRUNCATED and not retry_attempted:
            logger.info("Requested MCQs: %d", requested_questions)
            logger.warning("Attempt 1: Parser failed (truncated response). Retrying with half the questions.")
            retry_attempted = True
            _QUIZ_RESPONSE_TRUNCATED = False
            retry_num = max(1, requested_questions // 2)
            logger.info("Retry: Requested MCQs: %d", retry_num)
            # build new prompt for retry
            retry_prompt = _build_mcq_generation_prompt(retry_num)
            try:
                retry_response = _run_quiz_prompt(retry_prompt, text)
                logger.info("[Quiz Gen] Raw LLM response (retry len=%s)", len(retry_response) if retry_response is not None else 0)
                mcqs = _parse_json_response(retry_response)
                if mcqs is not None:
                    logger.info("Retry succeeded. Returning %d questions.", len(mcqs) if isinstance(mcqs, list) else 0)
            except Exception:
                logger.exception("[Quiz Parser] Retry generation failed.")

        if not isinstance(mcqs, list):
            logger.warning("[Quiz Parser] Parsed MCQ response is not a list or is empty.")
            mcqs = None
    except Exception:
        logger.exception("[Quiz Parser] MCQ generation failed. Falling back to local quiz generation.")
        mcqs = None

    if mcqs is None:
        _QUIZ_GENERATION_FALLBACK_USED = True
        logger.warning("[Quiz Parser] Falling back to local quiz generation")
        logger.info("Requested MCQs: %d; Retry attempted: %s", requested_questions, retry_attempted)
        return _local_generate_mcq_quiz(text, num_questions)

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
                **_extract_question_metadata(item, "MCQ", question, answer),
                "question": question,
                "options": [str(opt).strip() for opt in options],
                "answer": answer,
            }
        )

    if not validated_mcqs:
        logger.warning("[Quiz] MCQ parsing returned no valid questions. Using local fallback quiz generation.")
        _QUIZ_GENERATION_FALLBACK_USED = True
        validated_mcqs = _local_generate_mcq_quiz(text, num_questions)

    validated_mcqs = _ensure_quiz_metadata(validated_mcqs, "MCQ")
    set_cache_value(cache_key, validated_mcqs, ttl_hours=QUIZ_CACHE_TTL_HOURS)

    # Final instrumentation: log validated_mcqs and final return value
    try:
        logger.info("[Quiz Gen] validated_mcqs (count=%d)", len(validated_mcqs))
        logger.debug("[Quiz Gen] first validated question head: %s", (validated_mcqs[0].get('question') if validated_mcqs else '')[:300])
    except Exception:
        logger.exception("[Quiz Gen] Failed to log validated_mcqs")

    final_return = copy.deepcopy(validated_mcqs)
    try:
        logger.info("[Quiz Gen] Returning final mcqs (count=%d)", len(final_return))
    except Exception:
        logger.exception("[Quiz Gen] Failed to log final return")
    return final_return


def generate_short_questions(text: str, num_questions: int = 5) -> list[dict[str, str]]:
    """Generate short answer questions from document content."""
    global _QUIZ_GENERATION_FALLBACK_USED
    if not text or not text.strip():
        raise ValueError("Document text cannot be empty for short question generation.")

    # Ensure cache key exists and support cache lookups for short questions
    cache_key = make_quiz_cache_key(text, "short", num_questions)
    cached_questions = get_cache_value(cache_key)
    if cached_questions is not None:
        logger.info("[CACHE HIT] Quiz Short")
        return _ensure_quiz_metadata(copy.deepcopy(cached_questions), "Short Answer")

    prompt = _build_short_answer_generation_prompt(num_questions)

    try:
        response = _run_quiz_prompt(prompt, text)
        questions = _parse_json_response(response)
        if not isinstance(questions, list):
            logger.warning("[Quiz Parser] Parsed short question response is not a list or is empty.")
            questions = None
    except Exception:
        logger.exception("[Quiz Parser] Short question generation failed. Falling back to local quiz generation.")
        questions = None

    if questions is None:
        logger.warning("[Quiz Parser] Falling back to local quiz generation")
        _QUIZ_GENERATION_FALLBACK_USED = True
        return _local_generate_short_questions(text, num_questions)

    validated_questions = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if not question or not answer:
            continue
        validated_questions.append(
            {
                **_extract_question_metadata(item, "Short Answer", question, answer),
                "question": question,
                "options": [],
                "answer": answer,
            }
        )

    if not validated_questions:
        logger.warning("[Quiz] Short question parsing returned no valid questions. Using local fallback quiz generation.")
        _QUIZ_GENERATION_FALLBACK_USED = True
        validated_questions = _local_generate_short_questions(text, num_questions)

    validated_questions = _ensure_quiz_metadata(validated_questions, "Short Answer")
    set_cache_value(cache_key, validated_questions, ttl_hours=QUIZ_CACHE_TTL_HOURS)
    return copy.deepcopy(validated_questions)


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

        score = 1 if is_correct else 0
        feedback = _build_mcq_feedback(concept, correct_answer)
        question_feedback.append(
            _build_question_assessment_result(
                question_item=question_item,
                index=index,
                question=question,
                student_answer=student_answer,
                correct_answer=correct_answer,
                is_correct=is_correct,
                score=score,
                feedback=feedback,
                question_type="MCQ",
                options=options,
            )
        )

    percentage = round((correct_count / total) * 100) if total else 0

    analysis = _generate_mcq_learning_report(question_feedback)
    evidence = _build_raw_assessment_evidence(question_feedback, percentage)
    assessment_analytics = _build_assessment_analytics(question_feedback)

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
        "question_results": question_feedback,
        "wrong_concepts": evidence["wrong_concepts"],
        "correct_concepts": evidence["correct_concepts"],
        "concept_frequency": evidence["concept_frequency"],
        "skill_performance": evidence["skill_performance"],
        "difficulty_performance": evidence["difficulty_performance"],
        "raw_assessment_evidence": evidence,
        "assessment_analytics": assessment_analytics,
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
        evaluation = _extend_short_answer_assessment(evaluation, student_answer_text, expected_answer_text, question_text)
        logger.info("[Quiz] Short answer local evaluation completed in %.2fs", time.perf_counter() - start_time)
        return evaluation
    if not student_answer_text:
        evaluation = _fallback_short_answer_evaluation(student_answer_text, expected_answer_text, question_text)
        evaluation = _extend_short_answer_assessment(evaluation, student_answer_text, expected_answer_text, question_text)
        logger.info("[Quiz] Short answer local evaluation completed in %.2fs", time.perf_counter() - start_time)
        return evaluation

    local_evaluation = _fallback_short_answer_evaluation(student_answer_text, expected_answer_text, question_text)
    local_score = _safe_int(local_evaluation.get("score"), default=0)

    prompt = (
        "Compare the student answer to the expected answer. "
        "Evaluate the response based on meaning, not exact wording. "
        "Return only a JSON object with the fields:\n"
        "- score (integer between 0 and 5)\n"
        "- max_score (integer)\n"
        "- result (\"Correct\", \"Partially Correct\", or \"Incorrect\")\n"
        "- concept (2-4 words naming the topic)\n"
        "- feedback\n"
        "- improvement_tip\n"
        "Rules:\n"
        "- feedback must be 1-2 short sentences.\n"
        "- improvement_tip must be 1 question-specific sentence.\n"
        "- Do not use generic tips like 'review the key idea'.\n"
        "- Treat semantically equivalent answers as Correct, even with different wording, abbreviations, formulas, symbols, capitalization, punctuation, or minor spelling mistakes.\n"
        "- Mark these as Correct when they match the expected meaning: V=IR; V = I x R; V = I × R; Voltage = Current × Resistance; Voltage equals Current multiplied by Resistance.\n"
        "- Mark related but incomplete answers such as 'Voltage and Current' or 'Current is proportional to voltage' as Partially Correct.\n"
        "- Mark scientifically incorrect relationships such as 'Current is directly proportional to resistance' as Incorrect.\n"
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
        return _extend_short_answer_assessment(local_evaluation, student_answer_text, expected_answer_text, question_text)

    concept = str(evaluation.get("concept") or "").strip() or _infer_concept("", expected_answer_text)
    evaluation.setdefault("max_score", 5)
    evaluation.setdefault("score", 0)
    evaluation.setdefault("result", "Partially Correct")
    evaluation["concept"] = concept
    evaluation["result"] = _normalize_evaluation_result(evaluation.get("result"))
    if evaluation["result"] not in {"Correct", "Partially Correct", "Incorrect"}:
        evaluation["result"] = _result_from_score(local_score, evaluation["max_score"])

    explanation = _build_question_explanation(question_text, student_answer_text, expected_answer_text, evaluation["result"])
    if not _is_explanation_consistent_with_result(evaluation["result"], explanation) or not _teaches_concept(explanation, expected_answer_text):
        explanation = _build_question_explanation(question_text, student_answer_text, expected_answer_text, evaluation["result"])

    local_feedback = _shorten_sentences(
        explanation,
        fallback=explanation,
        max_sentences=3,
    )
    evaluation["local_feedback"] = local_feedback
    evaluation["local_explanation"] = local_feedback
    if not str(evaluation.get("feedback") or "").strip():
        evaluation["feedback"] = local_feedback
    if not str(evaluation.get("improvement_tip") or "").strip():
        evaluation["improvement_tip"] = _build_tip(concept, expected_answer_text)

    if not isinstance(evaluation["score"], int):
        try:
            evaluation["score"] = int(str(evaluation["score"]).strip())
        except Exception:
            evaluation["score"] = local_score

    evaluation["score"] = max(0, min(5, evaluation["score"]))
    # Add spelling note when LLM result seems correct but student had a minor typo
    spelling_note = _detect_spelling_note(student_answer_text, expected_answer_text)
    if spelling_note:
        evaluation["spelling_note"] = f'The correct spelling is "{spelling_note}".'
    evaluation["source"] = "llm"
    evaluation = _extend_short_answer_assessment(evaluation, student_answer_text, expected_answer_text, question_text)
    logger.info("[Quiz] Short answer LLM evaluation completed in %.2fs", time.perf_counter() - start_time)
    return evaluation


def evaluate_short_answer_locally(
    student_answer: str,
    expected_answer: str,
    question_text: str | None = None,
) -> dict[str, Any]:
    """Evaluate a short answer without any LLM dependency."""
    student_answer_text = str(student_answer or "").strip()
    expected_answer_text = str(expected_answer or "").strip()
    question_text_value = str(question_text or "").strip()
    evaluation = _fallback_short_answer_evaluation(
        student_answer_text,
        expected_answer_text,
        question_text_value,
    )
    return _extend_short_answer_assessment(
        evaluation,
        student_answer_text,
        expected_answer_text,
        question_text_value,
    )


def _detect_spelling_note(student_answer: str, expected_answer: str) -> str | None:
    """Detect minor single-word spelling mistakes and return the corrected spelling note.

    Returns the correct expected spelling (as a string) when a small typo is detected,
    otherwise None.
    """
    s = str(student_answer or "").strip()
    e = str(expected_answer or "").strip()
    if not s or not e:
        return None
    if " " in e or " " in s:
        # focus on short answers or single-word corrections
        # allow 1-2 word expected answers
        pass
    sim = _fuzzy_text_similarity(s, e)
    if sim >= 0.80 and _normalize_answer(s) != _normalize_answer(e):
        return e
    return None


def _semantic_match(student_answer: str, expected_answer: str) -> bool:
    """Return True when student answer preserves the core concept of expected answer.

    Uses normalized tokens, concept equivalences, and simple verb/object heuristics.
    """
    s_norm = _normalize_answer(student_answer)
    e_norm = _normalize_answer(expected_answer)
    if not s_norm or not e_norm:
        return False

    s_tokens = _content_tokens(s_norm)
    e_tokens = _content_tokens(e_norm)

    # direct strong overlap
    if not e_tokens:
        return False
    overlap = len(s_tokens & e_tokens) / max(1, len(e_tokens))
    if overlap >= 0.66:
        return True

    # handle concept equivalences: if any expected token maps to an equivalent token present in student
    for et in e_tokens:
        for canon, equivalents in _CONCEPT_EQUIVALENCE.items():
            if et == canon or et in equivalents:
                # check if student mentions any equivalent
                if any(eq in s_norm for eq in equivalents) or canon in s_norm:
                    return True

    # verb/object heuristic: look for 'make/produce/create' + 'food' style matches
    verbs = {"make", "produce", "create", "give", "release", "absorb", "capture"}
    if any(v in s_tokens for v in verbs) and any(v in e_tokens for v in verbs):
        # also require shared object token (like food, oxygen, pigment)
        shared = s_tokens & e_tokens
        if shared:
            return True

    return False


def _keyword_overlap_score(student_answer: str, expected_answer: str) -> float:
    s_tokens = _content_tokens(_normalize_answer(student_answer))
    e_tokens = _content_tokens(_normalize_answer(expected_answer))
    return _match_tokens(e_tokens, s_tokens)


def combine_quiz_report_with_short_answers(
    mcq_report: dict[str, Any],
    short_feedback: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge short-answer evaluations into a question-by-question quiz report."""
    report = dict(mcq_report)
    evaluations = list(report.get("evaluations") or [])
    question_results = list(report.get("question_results") or [])
    correct_count = _safe_int(report.get("correct_answers"), default=_safe_int(report.get("score"), default=0))
    total_count = _safe_int(report.get("total"), default=0)
    weak_count = _safe_int(report.get("incorrect_answers"), default=max(total_count - correct_count, 0))

    for index, item in enumerate(short_feedback, start=len(question_results) + 1):
        evaluation = item.get("evaluation", {}) if isinstance(item, dict) else {}
        score = _safe_int(evaluation.get("score"), default=0)
        max_score = max(_safe_int(evaluation.get("max_score"), default=5), 1)
        question = str(item.get("question", "")).strip()
        expected_answer = str(item.get("expected_answer", "")).strip()
        student_answer = str(item.get("student_answer", "")).strip()
        explicit_result = _normalize_evaluation_result(str(evaluation.get("result") or ""))
        result = explicit_result if explicit_result in {"Correct", "Partially Correct", "Incorrect"} else _result_from_score(score, max_score)
        total_count += 1
        if result == "Correct":
            correct_count += 1
        else:
            weak_count += 1

        explanation = _build_question_explanation(question, student_answer, expected_answer, result)
        if not _is_explanation_consistent_with_result(result, explanation):
            explanation = _build_question_explanation(question, student_answer, expected_answer, result)
        local_explanation = _shorten_sentences(explanation, fallback=explanation, max_sentences=3)
        feedback_text = str(evaluation.get("feedback") or "").strip()
        improvement_tip = str(evaluation.get("improvement_tip") or "").strip()

        evaluations.append(
            {
                "question": question,
                "your_answer": student_answer or "No answer",
                "correct_answer": expected_answer,
                "result": result,
                "explanation": feedback_text or local_explanation,
                "feedback": feedback_text,
                "improvement_tip": improvement_tip,
                "local_explanation": str(evaluation.get("local_explanation") or "").strip() or local_explanation,
            }
        )
        question_results.append(
            _build_question_assessment_result(
                question_item=item if isinstance(item, dict) else {},
                index=index,
                question=question,
                student_answer=student_answer,
                correct_answer=expected_answer,
                is_correct=result == "Correct",
                score=score,
                feedback=feedback_text or local_explanation,
                question_type="Short Answer",
                options=[],
            )
        )
        question_results[-1]["improvement_tip"] = improvement_tip
        question_results[-1]["local_explanation"] = str(evaluation.get("local_explanation") or "").strip() or local_explanation

    report["evaluations"] = evaluations
    report["score"] = correct_count
    report["total"] = total_count
    report["percentage"] = round((correct_count / total_count) * 100) if total_count else 0
    report["correct_answers"] = correct_count
    report["incorrect_answers"] = weak_count
    report["strengths"] = _build_strengths_summary(correct_count, total_count)
    report["weaknesses"] = _build_weaknesses_summary(weak_count, total_count)
    report["recommendations"] = _build_recommendation_summary(weak_count, total_count)
    evidence = _build_raw_assessment_evidence(question_results, report["percentage"])
    assessment_analytics = _build_assessment_analytics(question_results)
    report["question_results"] = question_results
    report["wrong_concepts"] = evidence["wrong_concepts"]
    report["correct_concepts"] = evidence["correct_concepts"]
    report["concept_frequency"] = evidence["concept_frequency"]
    report["skill_performance"] = evidence["skill_performance"]
    report["difficulty_performance"] = evidence["difficulty_performance"]
    report["raw_assessment_evidence"] = evidence
    report["assessment_analytics"] = assessment_analytics
    return report


def _fallback_short_answer_evaluation(
    student_answer: str,
    expected_answer: str,
    question_text: str = "",
) -> dict[str, Any]:
    """Evaluate a short answer locally with token overlap, fuzzy matching, and meaning."""
    # PRIMARY evaluation pipeline
    concept = _infer_concept(question_text, expected_answer)
    s = str(student_answer or "").strip()
    e = str(expected_answer or "").strip()

    # Step 1: normalize
    s_norm = _normalize_answer(s)
    e_norm = _normalize_answer(e)

    # Step 2: exact match
    if s_norm and s_norm == e_norm:
        score = 5
        result = "Correct"
        spelling_note = None
    else:
        # Step 3: spelling similarity (single/short answers)
        spelling_note = _detect_spelling_note(s, e)
        if spelling_note is not None:
            score = 5
            result = "Correct"
        else:
            # Step 4: keyword overlap
            token_overlap = _keyword_overlap_score(s, e)
            # Step 5: semantic equivalence
            semantic_ok = _semantic_match(s, e)

            if semantic_ok:
                # preserve core concept
                score = 5
                result = "Correct"
            else:
                # partially correct if some core tokens present
                if token_overlap >= 0.5:
                    score = 3
                    result = "Partially Correct"
                else:
                    # fall back to blended similarity scoring
                    normalized_student = s_norm
                    normalized_expected = e_norm
                    fuzzy_match = _fuzzy_text_similarity(normalized_student, normalized_expected)
                    sequence = difflib.SequenceMatcher(None, normalized_student, normalized_expected).ratio()
                    token_match = _match_tokens(_content_tokens(e_norm), _content_tokens(s_norm))
                    similarity = (
                        token_match * 0.55
                        + sequence * 0.25
                        + fuzzy_match * 0.20
                    )
                    score = max(0, min(5, round(similarity * 5)))
                    if score >= 4 and token_match < 0.6:
                        # guard small-token false positives
                        score = 4
                    if score >= 4 and token_overlap >= 0.5:
                        result = "Partially Correct" if token_overlap < 0.66 else "Correct"
                    else:
                        result = _result_from_score(score, 5)

    score = max(0, min(5, int(score)))

    # Build explanation and feedback
    explanation = _build_question_explanation(question_text, s, e, result)
    if not _teaches_concept(explanation, e):
        explanation = _build_question_explanation(question_text, s, e, result)

    feedback = _shorten_sentences(explanation, fallback=explanation, max_sentences=3)
    improvement = _build_tip(concept, e) or "Review the key concept."

    out: dict[str, Any] = {
        "score": score,
        "max_score": 5,
        "result": result,
        "concept": concept,
        "feedback": feedback,
        "improvement_tip": improvement,
        "source": "local",
    }
    if spelling_note:
        out["spelling_note"] = f'The correct spelling is "{spelling_note}".'
    return out


def _build_question_assessment_result(
    question_item: dict[str, Any],
    index: int,
    question: str,
    student_answer: str,
    correct_answer: str,
    is_correct: bool,
    score: int,
    feedback: str,
    question_type: str,
    options: list[str] | None = None,
) -> dict[str, Any]:
    metadata = _get_assessment_question_metadata(question_item, index, question, correct_answer, question_type)
    return {
        **metadata,
        "question": question,
        "options": options or [],
        "student_answer": student_answer,
        "your_answer": student_answer or "No answer",
        "correct_answer": correct_answer,
        "answer": correct_answer,
        "is_correct": bool(is_correct),
        "score": score,
        "feedback": feedback,
        "attempt_count": 1,
        "time_taken_seconds": None,
        "hint_used": False,
        "explanation_requests": 0,
    }


def _get_assessment_question_metadata(
    question_item: dict[str, Any],
    index: int,
    question: str,
    correct_answer: str,
    question_type: str,
) -> dict[str, str]:
    concept = str(question_item.get("concept") or "").strip() or _infer_concept(question, correct_answer)
    skill = _normalize_skill(question_item.get("skill"), question, correct_answer)
    return {
        "question_id": str(question_item.get("question_id") or "").strip() or _format_question_id(index),
        "question_type": str(question_item.get("question_type") or "").strip() or question_type,
        "concept": concept,
        "subcategory": str(question_item.get("subcategory") or "").strip()
        or _infer_subcategory(question, correct_answer, skill),
        "difficulty": _normalize_difficulty(question_item.get("difficulty"), question, correct_answer),
        "skill": skill,
        "learning_objective": str(question_item.get("learning_objective") or "").strip()
        or _build_learning_objective(skill, concept, question_type),
    }


def _build_raw_assessment_evidence(
    question_results: list[dict[str, Any]],
    accuracy: int,
) -> dict[str, Any]:
    wrong_concepts = _unique_preserving_order(
        [str(item.get("concept") or "").strip() for item in question_results if not item.get("is_correct")]
    )
    correct_concepts = _unique_preserving_order(
        [str(item.get("concept") or "").strip() for item in question_results if item.get("is_correct")]
    )
    concept_frequency = dict(
        Counter(str(item.get("concept") or "").strip() for item in question_results if str(item.get("concept") or "").strip())
    )

    return {
        "accuracy": accuracy,
        "retry_count": 0,
        "average_time": None,
        "wrong_concepts": wrong_concepts,
        "correct_concepts": correct_concepts,
        "concept_frequency": concept_frequency,
        "skill_performance": _summarize_performance_by_field(question_results, "skill"),
        "difficulty_performance": _summarize_performance_by_field(question_results, "difficulty"),
        "question_results": question_results,
    }


def _summarize_performance_by_field(
    question_results: list[dict[str, Any]],
    field_name: str,
) -> dict[str, dict[str, int]]:
    performance: dict[str, dict[str, int]] = {}
    for item in question_results:
        key = str(item.get(field_name) or "").strip()
        if not key:
            continue
        if key not in performance:
            performance[key] = {"correct": 0, "total": 0}
        performance[key]["total"] += 1
        if item.get("is_correct"):
            performance[key]["correct"] += 1
    return performance


def _build_assessment_analytics(question_results: list[dict[str, Any]]) -> dict[str, Any]:
    concept_accuracy = _build_concept_accuracy(question_results)
    skill_performance = _summarize_performance_by_field(question_results, "skill")
    difficulty_performance = _summarize_performance_by_field(question_results, "difficulty")
    skill_breakdown = _performance_accuracy_breakdown(skill_performance)
    difficulty_breakdown = _performance_accuracy_breakdown(difficulty_performance)
    question_distribution = {
        "difficulty": _distribution_by_field(question_results, "difficulty"),
        "concept": _distribution_by_field(question_results, "concept"),
        "skill": _distribution_by_field(question_results, "skill"),
        "question_type": _distribution_by_field(question_results, "question_type"),
    }
    assessment_summary = _build_assessment_summary(
        question_results,
        concept_accuracy,
        skill_breakdown,
    )

    return {
        "concept_accuracy": concept_accuracy,
        "skill_breakdown": skill_breakdown,
        "difficulty_breakdown": difficulty_breakdown,
        "question_distribution": question_distribution,
        "assessment_summary": assessment_summary,
        "assessment_insights": _build_assessment_insights(
            question_results,
            concept_accuracy,
            skill_breakdown,
            difficulty_breakdown,
            assessment_summary,
        ),
    }


def _build_concept_accuracy(question_results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    performance = _summarize_performance_by_field(question_results, "concept")
    concept_accuracy: dict[str, dict[str, int]] = {}
    for concept, values in performance.items():
        total = values.get("total", 0)
        correct = values.get("correct", 0)
        concept_accuracy[concept] = {
            "correct": correct,
            "total": total,
            "accuracy": round((correct / total) * 100) if total else 0,
        }
    return concept_accuracy


def _performance_accuracy_breakdown(performance: dict[str, dict[str, int]]) -> dict[str, int]:
    breakdown = {}
    for key, values in performance.items():
        total = values.get("total", 0)
        correct = values.get("correct", 0)
        breakdown[key] = round((correct / total) * 100) if total else 0
    return breakdown


def _distribution_by_field(question_results: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    return dict(
        Counter(
            str(item.get(field_name) or "").strip()
            for item in question_results
            if str(item.get(field_name) or "").strip()
        )
    )


def _build_assessment_summary(
    question_results: list[dict[str, Any]],
    concept_accuracy: dict[str, dict[str, int]],
    skill_breakdown: dict[str, int],
) -> dict[str, Any]:
    questions_attempted = len(question_results)
    questions_correct = sum(1 for item in question_results if item.get("is_correct"))
    return {
        "questions_attempted": questions_attempted,
        "questions_correct": questions_correct,
        "overall_accuracy": round((questions_correct / questions_attempted) * 100) if questions_attempted else 0,
        "strongest_concept": _best_accuracy_key(concept_accuracy),
        "weakest_concept": _lowest_accuracy_key(concept_accuracy),
        "strongest_skill": _best_breakdown_key(skill_breakdown),
        "weakest_skill": _lowest_breakdown_key(skill_breakdown),
    }


def _best_accuracy_key(values: dict[str, dict[str, int]]) -> str | None:
    if not values:
        return None
    return max(values.items(), key=lambda item: (item[1].get("accuracy", 0), item[1].get("total", 0), item[0]))[0]


def _lowest_accuracy_key(values: dict[str, dict[str, int]]) -> str | None:
    if not values:
        return None
    return min(values.items(), key=lambda item: (item[1].get("accuracy", 0), -item[1].get("total", 0), item[0]))[0]


def _best_breakdown_key(values: dict[str, int]) -> str | None:
    if not values:
        return None
    return max(values.items(), key=lambda item: (item[1], item[0]))[0]


def _lowest_breakdown_key(values: dict[str, int]) -> str | None:
    if not values:
        return None
    return min(values.items(), key=lambda item: (item[1], item[0]))[0]


def _build_assessment_insights(
    question_results: list[dict[str, Any]],
    concept_accuracy: dict[str, dict[str, int]],
    skill_breakdown: dict[str, int],
    difficulty_breakdown: dict[str, int],
    assessment_summary: dict[str, Any],
) -> list[str]:
    insights = []
    if not question_results:
        return ["No quiz questions were evaluated in this assessment."]

    strongest_concept = assessment_summary.get("strongest_concept")
    weakest_concept = assessment_summary.get("weakest_concept")
    strongest_skill = assessment_summary.get("strongest_skill")
    weakest_skill = assessment_summary.get("weakest_skill")

    if strongest_concept:
        accuracy = concept_accuracy.get(strongest_concept, {}).get("accuracy", 0)
        insights.append(f"{strongest_concept} questions had the highest concept accuracy at {accuracy}%.")
    if weakest_concept and weakest_concept != strongest_concept:
        accuracy = concept_accuracy.get(weakest_concept, {}).get("accuracy", 0)
        insights.append(f"{weakest_concept} questions had the lowest concept accuracy at {accuracy}%.")
    if strongest_skill:
        insights.append(f"{strongest_skill} questions had the highest skill accuracy at {skill_breakdown[strongest_skill]}%.")
    if weakest_skill and weakest_skill != strongest_skill:
        insights.append(f"{weakest_skill} questions had the lowest skill accuracy at {skill_breakdown[weakest_skill]}%.")

    best_difficulty = _best_breakdown_key(difficulty_breakdown)
    weakest_difficulty = _lowest_breakdown_key(difficulty_breakdown)
    if best_difficulty:
        insights.append(f"{best_difficulty} questions had {difficulty_breakdown[best_difficulty]}% accuracy in this assessment.")
    if weakest_difficulty and weakest_difficulty != best_difficulty:
        insights.append(f"{weakest_difficulty} questions had {difficulty_breakdown[weakest_difficulty]}% accuracy in this assessment.")

    return insights[:6]


def _extend_short_answer_assessment(
    evaluation: dict[str, Any],
    student_answer: str,
    expected_answer: str,
    question_text: str,
) -> dict[str, Any]:
    result = dict(evaluation)
    identified_keywords = _identified_keywords(student_answer, expected_answer)
    missing_keywords = _missing_keywords(student_answer, expected_answer)
    misconceptions = _misconceptions(student_answer, expected_answer, result.get("result"))
    max_score = max(_safe_int(result.get("max_score"), default=5), 1)
    score = _safe_int(result.get("score"), default=0)

    result["student_answer"] = student_answer
    result["correct_answer"] = expected_answer
    result["is_correct"] = result.get("result") == "Correct"
    result["identified_keywords"] = identified_keywords
    result["missing_keywords"] = missing_keywords
    result["misconceptions"] = misconceptions
    result["confidence"] = round(score / max_score, 2)
    result["attempt_count"] = 1
    result["time_taken_seconds"] = None
    result["hint_used"] = False
    result["explanation_requests"] = 0
    result.setdefault("question_id", "Q001")
    result.setdefault("question_type", "Short Answer")
    result.setdefault("concept", _infer_concept(question_text, expected_answer))
    result.setdefault("subcategory", _infer_subcategory(question_text, expected_answer, _normalize_skill("", question_text, expected_answer)))
    result.setdefault("difficulty", _normalize_difficulty("", question_text, expected_answer))
    result.setdefault("skill", _normalize_skill("", question_text, expected_answer))
    result.setdefault(
        "learning_objective",
        _build_learning_objective(str(result.get("skill") or ""), str(result.get("concept") or ""), "Short Answer"),
    )
    return result


def _identified_keywords(student_answer: str, expected_answer: str) -> list[str]:
    student_tokens = _content_tokens(_normalize_answer(student_answer))
    expected_tokens = _content_tokens(_normalize_answer(expected_answer))
    return sorted(expected_tokens & student_tokens)


def _missing_keywords(student_answer: str, expected_answer: str) -> list[str]:
    student_tokens = _content_tokens(_normalize_answer(student_answer))
    expected_tokens = _content_tokens(_normalize_answer(expected_answer))
    return sorted(expected_tokens - student_tokens)


def _misconceptions(student_answer: str, expected_answer: str, result: Any) -> list[str]:
    if str(result or "").strip().title() == "Correct":
        return []
    student_tokens = _content_tokens(_normalize_answer(student_answer))
    expected_tokens = _content_tokens(_normalize_answer(expected_answer))
    extra_tokens = sorted(student_tokens - expected_tokens)
    return extra_tokens[:5]


def _run_quiz_prompt(prompt: str, document_text: str | None = None) -> str:
    full_prompt = prompt
    if document_text is not None:
        full_prompt = (
            f"{prompt}\n\n"
            "DOCUMENT CONTENT:\n"
            f"{document_text.strip()}"
        )

    try:
        # Quiz generation may be large—limit completion size to 800 tokens
        return generate_content(full_prompt, max_tokens=800)
    except LLMRouterError:
        raise
    except Exception as exc:
        logger.exception("Unexpected quiz service error.")
        raise LLMRouterError("Quiz generation is temporarily unavailable.") from exc


def _parse_json_response(text: str) -> Any:
    # Start detailed logging of parser pipeline for debugging
    try:
        raw_text = text or ""
        # Emit the complete raw LLM response exactly as received (no modification)
        try:
            print("\n================ RAW LLM RESPONSE ================")
            print(raw_text)
            print("==================================================\n")
        except Exception:
            # If printing fails, fall back to logging the repr
            logger.exception("[Quiz Parser] Failed to print raw LLM response")
        logger.info("[Quiz Parser] Raw response received (len=%d)", len(raw_text))
        logger.debug("[Quiz Parser] Raw response head: %s", raw_text[:300])
        logger.debug("[Quiz Parser] Raw response tail: %s", raw_text[-150:])

        # Extract JSON-like payload
        payload = _extract_json_payload(raw_text)
        logger.info("[Quiz Parser] _extract_json_payload returned (type=%s len=%s)", type(payload).__name__, len(payload) if payload is not None else None)
        logger.debug("[Quiz Parser] payload head: %s", (payload or "")[:300])

        if not payload:
            logger.warning("[Quiz Parser] No JSON payload found in model response.")
            return None

        cleaned = _strip_markdown_wrappers(payload)
        print("\n[Quiz Parser] Original first 20 characters:")
        print(raw_text[:20])
        print("[Quiz Parser] Cleaned first 20 characters:")
        print((cleaned or "")[:20])
        # Basic truncation detection: ensure response appears to be a JSON array or object
        try:
            s = cleaned.strip()
            if not ((s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}"))):
                # mark truncated and avoid aggressive repair attempts
                global _QUIZ_RESPONSE_TRUNCATED
                _QUIZ_RESPONSE_TRUNCATED = True
                logger.warning("Detected incomplete/truncated LLM response.")
                logger.debug("[Quiz Parser] cleaned start: %s", s[:80])
                logger.debug("[Quiz Parser] cleaned end: %s", s[-80:])
                return None
        except Exception:
            logger.exception("[Quiz Parser] Error during truncation detection")
            return None
        logger.info("[Quiz Parser] _strip_markdown_wrappers output (len=%d)", len(cleaned))
        logger.debug("[Quiz Parser] cleaned head: %s", cleaned[:300])

        # Try json.loads on cleaned
        try:
            logger.info("[Quiz Parser] Attempting json.loads on cleaned payload")
            logger.debug("[Quiz Parser] json.loads input head: %s", cleaned[:300])
            parsed = json.loads(cleaned)
            logger.info("[Quiz Parser] json.loads succeeded (type=%s len=%s)", type(parsed).__name__, len(parsed) if isinstance(parsed, (list, dict)) else None)
            return parsed
        except Exception as exc_json:
            tb = traceback.format_exc()
            logger.warning("[Quiz Parser] json.loads(cleaned) failed: %s", repr(exc_json))
            logger.debug("[Quiz Parser] json.loads(cleaned) traceback:\n%s", tb)

        # Try ast.literal_eval on cleaned
        try:
            logger.info("[Quiz Parser] Attempting ast.literal_eval on cleaned payload")
            parsed_ast = ast.literal_eval(cleaned)
            logger.info("[Quiz Parser] ast.literal_eval succeeded (type=%s len=%s)", type(parsed_ast).__name__, len(parsed_ast) if isinstance(parsed_ast, (list, dict)) else None)
            return parsed_ast
        except Exception as exc_ast:
            tb = traceback.format_exc()
            logger.warning("[Quiz Parser] ast.literal_eval(cleaned) failed: %s", repr(exc_ast))
            logger.debug("[Quiz Parser] ast.literal_eval(cleaned) traceback:\n%s", tb)

        # Attempt repair
        repaired = _repair_json_text(cleaned)
        logger.info("[Quiz Parser] _repair_json_text produced (len=%d)", len(repaired))
        logger.debug("[Quiz Parser] repaired head: %s", repaired[:300])

        try:
            logger.info("[Quiz Parser] Attempting json.loads on repaired payload")
            parsed_repaired = json.loads(repaired)
            logger.info("[Quiz Parser] json.loads(repaired) succeeded (type=%s len=%s)", type(parsed_repaired).__name__, len(parsed_repaired) if isinstance(parsed_repaired, (list, dict)) else None)
            return parsed_repaired
        except Exception as exc_json2:
            tb = traceback.format_exc()
            logger.warning("[Quiz Parser] json.loads(repaired) failed: %s", repr(exc_json2))
            logger.debug("[Quiz Parser] json.loads(repaired) traceback:\n%s", tb)

        try:
            logger.info("[Quiz Parser] Attempting ast.literal_eval on repaired payload")
            parsed_ast2 = ast.literal_eval(repaired)
            logger.info("[Quiz Parser] ast.literal_eval(repaired) succeeded (type=%s len=%s)", type(parsed_ast2).__name__, len(parsed_ast2) if isinstance(parsed_ast2, (list, dict)) else None)
            return parsed_ast2
        except Exception as exc_ast2:
            tb = traceback.format_exc()
            logger.warning("[Quiz Parser] ast.literal_eval(repaired) failed: %s", repr(exc_ast2))
            logger.debug("[Quiz Parser] ast.literal_eval(repaired) traceback:\n%s", tb)

        # Fallback text extraction
        fallback = _extract_quiz_structures_from_text(raw_text)
        if fallback is not None:
            logger.warning("[Quiz Parser] Falling back to extracted quiz structures from raw response (type=%s len=%s)", type(fallback).__name__, len(fallback) if isinstance(fallback, (list, dict)) else None)
            logger.debug("[Quiz Parser] fallback head: %s", (repr(fallback)[:300]))
            return fallback

        logger.exception("[Quiz Parser] JSON parsing failed for quiz service response.")
        return None
    except Exception:
        logger.exception("[Quiz Parser] Unexpected error in parser instrumentation")
        return None



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


def _strip_markdown_wrappers(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"^json\s*(?=[\{\[])", "", text, flags=re.IGNORECASE)
    return text.strip()


def _repair_json_text(text: str) -> str:
    repaired = str(text or "").strip()
    repaired = repaired.replace("\r", " ").replace("\t", " ")
    repaired = repaired.replace("“", '"').replace("”", '"')
    repaired = repaired.replace("‘", "'").replace("’", "'")
    repaired = _escape_newlines_in_json_strings(repaired)
    repaired = _escape_unescaped_control_chars(repaired)
    repaired = re.sub(r",\s*([\]}])", r"\1", repaired)
    repaired = _quote_json_keys(repaired)
    repaired = _convert_single_quotes_to_double_quotes(repaired)
    repaired = re.sub(r"\s+$", "", repaired)
    return repaired


def _escape_newlines_in_json_strings(text: str) -> str:
    def replacement(match: re.Match) -> str:
        inner = match.group(1)
        inner = inner.replace("\n", "\\n").replace("\r", "\\n").replace("\t", "\\t")
        return '"' + inner + '"'

    return re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', replacement, text, flags=re.S)


def _escape_unescaped_control_chars(text: str) -> str:
    return re.sub(r"[\x00-\x1f]", " ", text)


def _quote_json_keys(text: str) -> str:
    def replacement(match: re.Match) -> str:
        prefix = match.group(1)
        key = match.group(2).strip()
        suffix = match.group(3)
        return f"{prefix}\"{key}\"{suffix}"

    return re.sub(r'([\{,]\s*)([A-Za-z_][A-Za-z0-9_ ]*)(\s*):', replacement, text)


def _convert_single_quotes_to_double_quotes(text: str) -> str:
    return re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', text)


def _extract_quiz_structures_from_text(text: str) -> Any:
    if not text or not text.strip():
        return None

    qas = []
    qa_pairs = re.findall(r"(?im)^(?:question\s*\d*[:\).\-]*\s*)(.*?)\s*(?:answer\s*\d*[:\).\-]*\s*)(.*?)(?=\n(?:question|answer|$))", text, re.S)
    if qa_pairs:
        for question, answer in qa_pairs[:10]:
            qas.append({"question": question.strip(), "answer": answer.strip()})
        return qas

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if re.match(r"^(?:\d+\.|[A-Da-d][\).]|Q\d*[:\).])", line):
            content = re.sub(r"^(?:\d+\.|[A-Da-d][\).]|Q\d*[:\).])\s*", "", line).strip()
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.lower().startswith("answer"):
                    qas.append({"question": content, "answer": next_line})
    return qas if qas else None


def quiz_generation_used_fallback() -> bool:
    global _QUIZ_GENERATION_FALLBACK_USED
    used = _QUIZ_GENERATION_FALLBACK_USED
    _QUIZ_GENERATION_FALLBACK_USED = False
    return used


def _build_mcq_generation_prompt(num_questions: int) -> str:
    return (
        "Generate a learner-friendly multiple choice quiz from the document below. "
        f"Create exactly {num_questions} questions. "
        "IMPORTANT: Return exactly one JSON array and nothing else. Do NOT include any text before or after the array. "
        "Do NOT include explanations, comments, or notes. Do NOT use Markdown, fenced code blocks, or prepend the word 'json'. "
        "Return only a valid JSON array. Do not add any additional text outside the JSON array.\n"
        "Start the response with '[' and end the response with ']'.\n"
        "For each question, return exactly these keys:\n"
        "- question_id (Q001, Q002, Q003, unique within this quiz)\n"
        "- question_type (must be exactly \"MCQ\")\n"
        "- concept (2-5 words naming the main topic from the document)\n"
        "- subcategory (one natural label such as Formula, Definition, Diagram, Theory, Application, or Calculation)\n"
        "- difficulty (must be exactly one of: Easy, Medium, Hard)\n"
        "- skill (must be exactly one of: Concept Understanding, Definition Recall, Formula Application, "
        "Numerical Problem Solving, Diagram Interpretation, Real-world Application)\n"
        "- learning_objective (one concise measurable sentence describing what the learner demonstrates)\n"
        "- question\n"
        "- options (a list of exactly 4 answer choices)\n"
        "- answer (the correct answer exactly as one of the options)\n"
        "Balance the quiz as well as possible across Easy, Medium, and Hard difficulty. "
        "Also vary the learning skills where the document supports them. "
        "Do not invent unsupported facts or extra fields. "
        "Use simple language and keep answer choices clear and short."
    )


def _build_short_answer_generation_prompt(num_questions: int) -> str:
    return (
        "Create a list of learner-friendly short answer questions from the document below. "
        f"Generate exactly {num_questions} questions. "
        "Return only a valid JSON array. Do not add any additional text outside the JSON array.\n"
        "For each question, return exactly these keys:\n"
        "- question_id (Q001, Q002, Q003, unique within this quiz)\n"
        "- question_type (must be exactly \"Short Answer\")\n"
        "- concept (2-5 words naming the main topic from the document)\n"
        "- subcategory (one natural label such as Formula, Definition, Diagram, Theory, Application, or Calculation)\n"
        "- difficulty (must be exactly one of: Easy, Medium, Hard)\n"
        "- skill (must be exactly one of: Concept Understanding, Definition Recall, Formula Application, "
        "Numerical Problem Solving, Diagram Interpretation, Real-world Application)\n"
        "- learning_objective (one concise measurable sentence describing what the learner demonstrates)\n"
        "- question\n"
        "- options (an empty list)\n"
        "- answer\n"
        "Balance the quiz as well as possible across Easy, Medium, and Hard difficulty. "
        "Also vary the learning skills where the document supports them. "
        "Do not invent unsupported facts or extra fields. "
        "Use simple language and keep expected answers concise."
    )


def _ensure_quiz_metadata(questions: list[dict[str, Any]], question_type: str) -> list[dict[str, Any]]:
    enriched = []
    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        metadata = _extract_question_metadata(item, question_type, question, answer)
        metadata["question_id"] = _format_question_id(index)
        metadata["question_type"] = question_type

        normalized_item = {**item, **metadata}
        if question_type == "MCQ":
            normalized_item["options"] = [str(opt).strip() for opt in item.get("options", [])]
        else:
            normalized_item["options"] = item.get("options") if isinstance(item.get("options"), list) else []
        enriched.append(normalized_item)
    return enriched


def _extract_question_metadata(
    item: dict[str, Any],
    question_type: str,
    question: str,
    answer: str,
) -> dict[str, str]:
    concept = str(item.get("concept") or "").strip() or _infer_concept(question, answer)
    difficulty = _normalize_difficulty(item.get("difficulty"), question, answer)
    skill = _normalize_skill(item.get("skill"), question, answer)
    subcategory = str(item.get("subcategory") or "").strip() or _infer_subcategory(question, answer, skill)
    objective = str(item.get("learning_objective") or "").strip()
    if not objective:
        objective = _build_learning_objective(skill, concept, question_type)

    return {
        "question_id": str(item.get("question_id") or "").strip(),
        "question_type": question_type,
        "concept": concept,
        "subcategory": subcategory,
        "difficulty": difficulty,
        "skill": skill,
        "learning_objective": objective,
    }


def _format_question_id(index: int) -> str:
    return f"Q{index:03d}"


def _normalize_difficulty(value: Any, question: str, answer: str) -> str:
    difficulty = str(value or "").strip().title()
    if difficulty in _ALLOWED_DIFFICULTIES:
        return difficulty

    word_count = len(f"{question} {answer}".split())
    if word_count <= 14:
        return "Easy"
    if word_count >= 28:
        return "Hard"
    return "Medium"


def _normalize_skill(value: Any, question: str, answer: str) -> str:
    skill = str(value or "").strip()
    for allowed in _ALLOWED_SKILLS:
        if skill.lower() == allowed.lower():
            return allowed

    text = f"{question} {answer}".lower()
    if re.search(r"\b(calculate|solve|number|total|amount|value|current|voltage|force)\b", text):
        return "Numerical Problem Solving"
    if re.search(r"\b(formula|equation|law|rule)\b", text):
        return "Formula Application"
    if re.search(r"\b(diagram|figure|chart|graph|label)\b", text):
        return "Diagram Interpretation"
    if re.search(r"\b(example|real|daily|application|use)\b", text):
        return "Real-world Application"
    if re.search(r"\b(define|definition|meaning|what is)\b", text):
        return "Definition Recall"
    return "Concept Understanding"


def _infer_subcategory(question: str, answer: str, skill: str) -> str:
    text = f"{question} {answer}".lower()
    if skill == "Formula Application" or re.search(r"\b(formula|equation|law)\b", text):
        return "Formula"
    if skill == "Numerical Problem Solving" or re.search(r"\b(calculate|solve|number|amount|value)\b", text):
        return "Calculation"
    if skill == "Diagram Interpretation" or re.search(r"\b(diagram|figure|chart|graph)\b", text):
        return "Diagram"
    if skill == "Real-world Application" or re.search(r"\b(example|real|use|application)\b", text):
        return "Application"
    if skill == "Definition Recall" or re.search(r"\b(define|meaning|what is)\b", text):
        return "Definition"
    return "Theory"


def _build_learning_objective(skill: str, concept: str, question_type: str) -> str:
    concept = concept or "the concept"
    if skill == "Definition Recall":
        return f"Recall the definition or meaning of {concept}."
    if skill == "Formula Application":
        return f"Apply the relevant formula to answer a question about {concept}."
    if skill == "Numerical Problem Solving":
        return f"Solve a numerical problem related to {concept}."
    if skill == "Diagram Interpretation":
        return f"Interpret a diagram or visual representation of {concept}."
    if skill == "Real-world Application":
        return f"Connect {concept} to a real-world use or example."
    if question_type == "MCQ":
        return f"Identify the correct idea related to {concept}."
    return f"Explain the key idea related to {concept}."


def _local_generate_mcq_quiz(text: str, num_questions: int) -> list[dict[str, Any]]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    facts = []
    for sentence in sentences:
        match = re.search(r"([A-Z][^.!?]{20,120}?) (is|are|has|have|uses|means|contains) ([^.!?]+)", sentence, re.I)
        if match:
            subject = match.group(1).strip()
            verb = match.group(2).strip()
            remainder = match.group(3).strip().rstrip(".")
            facts.append((subject, verb, remainder))
        if len(facts) >= num_questions * 2:
            break

    if not facts:
        key_terms = re.findall(r"\b[a-zA-Z]{4,}\b", text)
        key_terms = [term for term in key_terms if term.lower() not in _STOPWORDS]
        facts = [(term.capitalize(), "is", "important") for term in key_terms[:num_questions]]

    mcqs = []
    distractors = list({t for t in re.findall(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", text) if t.lower() not in _STOPWORDS})
    random.shuffle(distractors)

    for subject, verb, remainder in facts[:num_questions]:
        correct = f"{verb} {remainder}" if verb.lower() != "is" else remainder
        question = f"What does {subject} {verb}?" if verb.lower() != "is" else f"What is {subject}?"
        options = [correct]
        for candidate in distractors:
            if candidate.lower() != remainder.lower() and candidate.lower() not in {opt.lower() for opt in options}:
                options.append(candidate)
            if len(options) == 4:
                break
        while len(options) < 4:
            options.append("more detail")
        random.shuffle(options)
        mcqs.append({"question": question, "options": options, "answer": correct})

    if len(mcqs) < num_questions:
        while len(mcqs) < num_questions:
            mcqs.append({
                "question": f"What is a key idea from this document?",
                "options": ["A key idea", "A different idea", "A wrong idea", "A missing idea"],
                "answer": "A key idea",
            })
    return _ensure_quiz_metadata(mcqs[:num_questions], "MCQ")


def _local_generate_short_questions(text: str, num_questions: int) -> list[dict[str, Any]]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    questions = []
    for sentence in sentences:
        if len(questions) >= num_questions:
            break
        if " is " in sentence.lower() or " are " in sentence.lower() or " can " in sentence.lower() or " uses " in sentence.lower():
            question = sentence
            answer = sentence.rstrip('.').strip()
            if len(answer.split()) > 4:
                answer = answer
            else:
                continue
            questions.append({"question": f"What does this mean: {answer.split()[0]}?", "answer": answer})

    if len(questions) < num_questions:
        key_phrases = []
        for sentence in sentences:
            words = [word for word in re.findall(r"\b[a-zA-Z]{4,}\b", sentence) if word.lower() not in _STOPWORDS]
            if len(words) >= 2:
                key_phrases.append((words[0], " ".join(words[1:3])))
        for subject, detail in key_phrases:
            if len(questions) >= num_questions:
                break
            questions.append({"question": f"What does {subject} do?", "answer": detail})

    if len(questions) < num_questions:
        for i in range(len(questions), num_questions):
            questions.append({"question": f"What is one important idea from the document?", "answer": "A main idea from the document."})

    return _ensure_quiz_metadata(questions, "Short Answer")


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

    # Compare option text values ignoring letter prefixes and minor spelling errors.
    for option in options:
        normalized_option = _normalize_answer(option)
        if normalized_option == normalized_student:
            return normalized_option == normalized_correct
        if _fuzzy_text_similarity(normalized_option, normalized_student) >= 0.86:
            return normalized_option == normalized_correct

    return False


def _normalize_answer(answer: str) -> str:
    clean = str(answer or "").strip().lower()
    clean = re.sub(r"^\s*[abcd]\s*[\).:-]*\s*", "", clean)
    clean = re.sub(r"[^a-z0-9\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    normalized_tokens = []
    for token in clean.split():
        normalized_tokens.append(_SYNONYM_MAP.get(token, token))
    return " ".join(token for token in normalized_tokens if token)


def _normalize_evaluation_result(result: str) -> str:
    result_text = str(result or "").strip().title()
    if result_text in {"Correct", "Perfectly Correct", "Perfect"}:
        return "Correct"
    if result_text in {"Partially", "Partially Correct"}:
        return "Partially Correct"
    if result_text == "Incorrect":
        return "Incorrect"
    return "Incorrect"


def _levenshtein_distance(a: str, b: str) -> int:
    a = str(a or "")
    b = str(b or "")
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i]
        for j, char_b in enumerate(b, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = previous_row[j] + 1
            replace_cost = previous_row[j - 1] + (char_a != char_b)
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        previous_row = current_row

    return previous_row[-1]


def _fuzzy_text_similarity(a: str, b: str) -> float:
    a = _normalize_answer(a)
    b = _normalize_answer(b)
    if not a or not b:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    distance = _levenshtein_distance(a, b)
    edit_score = 1.0 - (distance / max(len(a), len(b), 1))
    return (ratio + edit_score) / 2.0


def _match_tokens(expected_tokens: set[str], student_tokens: set[str]) -> float:
    if not expected_tokens:
        return 0.0

    matched = 0
    for expected in expected_tokens:
        for student in student_tokens:
            if expected == student or _fuzzy_text_similarity(expected, student) >= 0.8:
                matched += 1
                break

    return matched / len(expected_tokens)


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
                "question_id": item.get("question_id"),
                "question_type": item.get("question_type"),
                "concept": item.get("concept"),
                "subcategory": item.get("subcategory"),
                "difficulty": item.get("difficulty"),
                "skill": item.get("skill"),
                "learning_objective": item.get("learning_objective"),
                "student_answer": student_answer,
                "is_correct": bool(item.get("is_correct")),
                "score": item.get("score", 0),
                "feedback": item.get("feedback", ""),
                "attempt_count": item.get("attempt_count", 1),
                "time_taken_seconds": item.get("time_taken_seconds"),
                "hint_used": item.get("hint_used", False),
                "explanation_requests": item.get("explanation_requests", 0),
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


def _derive_conceptual_score_from_weak_concepts(weak_concepts: list[str]) -> float:
    if not weak_concepts:
        return 90.0
    score = 100.0 - min(len(weak_concepts) * 12.0, 60.0)
    return round(max(score, 30.0), 1)


def _calculate_learning_support_dependency(weak_dependency_count: int, total_questions: int) -> float:
    if total_questions <= 0:
        return 100.0
    ratio = min(1.0, weak_dependency_count / float(total_questions))
    return round(max(0.0, 100.0 - ratio * 80.0), 1)


def _calculate_response_efficiency_score(avg_response_time: float) -> float:
    if avg_response_time <= 30:
        return 100.0
    if avg_response_time >= 120:
        return 0.0
    return round(100.0 - ((avg_response_time - 30.0) / 90.0) * 100.0, 1)


def _choose_suggested_learning_mode(
    conceptual_score: float,
    response_efficiency_score: float,
    learning_support_dependency_score: float,
    first_attempt_success_rate: float,
) -> str:
    if conceptual_score < 65.0:
        return "Visual Learning"
    if learning_support_dependency_score < 50.0:
        return "AI Tutor"
    if response_efficiency_score < 50.0:
        return "Audio Learning"
    if first_attempt_success_rate < 70.0:
        return "Simplified Notes"
    return "Simplified Notes"


def generate_personalized_quiz_feedback(
    quiz_accuracy: float,
    conceptual_score: float | None = None,
    avg_response_time: float = 0.0,
    support_count: int = 0,
    total_questions: int = 0,
    first_attempt_success_rate: float = 0.0,
    weak_concepts: list[str] | None = None,
) -> dict[str, str]:
    weak_concepts = weak_concepts or []
    conceptual_score = conceptual_score if conceptual_score is not None else _derive_conceptual_score_from_weak_concepts(weak_concepts)
    response_efficiency_score = _calculate_response_efficiency_score(avg_response_time)
    support_dependency_score = _calculate_learning_support_dependency(support_count, total_questions)
    suggested_learning_mode = _choose_suggested_learning_mode(
        conceptual_score,
        response_efficiency_score,
        support_dependency_score,
        first_attempt_success_rate,
    )

    strengths: list[str] = []
    if quiz_accuracy >= 80.0:
        strengths.append("Strong quiz accuracy")
    if conceptual_score >= 75.0:
        strengths.append("Good conceptual understanding")
    if response_efficiency_score >= 70.0:
        strengths.append("Efficient response pace")
    if first_attempt_success_rate >= 70.0:
        strengths.append("Good first-attempt recall")
    if support_dependency_score >= 70.0:
        strengths.append("Low support dependency")
    if not strengths:
        strengths.append("You have a solid starting point to improve with focused review.")

    weaknesses: list[str] = []
    if quiz_accuracy < 70.0:
        weaknesses.append("Quiz accuracy needs improvement")
    if conceptual_score < 70.0:
        weaknesses.append("Concept understanding is still developing")
    if response_efficiency_score < 60.0:
        weaknesses.append("Take a bit more time to answer carefully")
    if support_dependency_score < 60.0:
        weaknesses.append("Reduce reliance on support hints")
    if first_attempt_success_rate < 60.0:
        weaknesses.append("Aim for better first-try answers")
    if not weaknesses:
        weaknesses.append("No major weaknesses identified from this quiz attempt.")

    if weak_concepts:
        recommended_concepts = ", ".join(weak_concepts[:3])
    else:
        recommended_concepts = "Review the concepts behind the questions you missed."

    return {
        "feedback_strengths": ", ".join(strengths),
        "feedback_weaknesses": ", ".join(weaknesses),
        "feedback_recommended_concepts": recommended_concepts,
        "feedback_suggested_learning_mode": suggested_learning_mode,
    }


def _build_question_explanation(question: str, student_answer: str, correct_answer: str, result: str) -> str:
    correct_trim = _trim_text(correct_answer, max_words=20)
    student_trim = _trim_text(student_answer, max_words=18)
    student_answer_text = student_trim or "no answer"
    reason = _build_reason_text(question, correct_answer)

    # Educational, dyslexia-friendly phrasing
    if result == "Correct":
        # Two short sentences: confirmation + simple teaching
        teach = reason.capitalize()
        return f"Correct. {correct_trim.capitalize()} is right. {teach}."

    if result == "Partially Correct":
        detail = student_answer_text if student_answer_text != "no answer" else "you have part of the idea"
        teach = reason.capitalize()
        return (
            f"You have some of the idea: {detail}. "
            f"The fuller answer is {correct_trim}. {teach}."
        )

    # Incorrect
    teach = reason.capitalize()
    return (
        f"Your answer was {student_answer_text}. "
        f"The correct answer is {correct_trim}. {teach}."
    )


def _build_reason_text(question: str, correct_answer: str) -> str:
    lower_question = str(question or "").strip().lower()
    answer = str(correct_answer or "").strip().rstrip(".")
    lower_answer = answer.lower()

    if not answer:
        return "it matches the key idea in the question"

    # Concept explanation map (educational and short)
    concept_map = {
        "chlorophyll": "Chlorophyll is the green pigment in leaves that absorbs sunlight for photosynthesis",
        "oxygen": "Plants release oxygen as a by-product of photosynthesis",
        "carbon dioxide": "Plants absorb carbon dioxide from the air to make food",
        "leaves": "Photosynthesis mainly occurs in leaves because they contain chlorophyll",
        "water": "Water is one of the raw materials plants use to make food",
        "sunlight": "Sunlight provides the energy needed for photosynthesis",
        "photosynthesis": "Photosynthesis is the process plants use to make food from sunlight, water, and carbon dioxide",
    }

    # Use direct mapping when a known concept is present
    for key, explanation in concept_map.items():
        if re.search(rf"\b{re.escape(key)}\b", lower_answer) or re.search(rf"\b{re.escape(key)}\b", lower_question):
            return explanation

    # Question-specific heuristics
    if "where" in lower_question or "place" in lower_question or "location" in lower_question:
        return f"it happens in {answer}"

    if "what gas" in lower_question and "oxygen" in lower_answer:
        return concept_map.get("oxygen")

    if "what is photosynthesis" in lower_question or "describe photosynthesis" in lower_question:
        return concept_map.get("photosynthesis")

    # fallback to simpler teaching sentence
    return f"{answer} is important because it helps explain the idea in the question"


def _build_memory_tip_text(correct_answer: str, student_answer: str | None = None) -> str:
    answer = str(correct_answer or "").strip().lower()
    student_lower = str(student_answer or "").strip().lower()

    if "leaves" in answer and "roots" in student_lower:
        return "leaves make food, roots absorb water"
    if "roots" in answer and "leaves" in student_lower:
        return "roots take in water, leaves make food"
    if "oxygen" in answer and "carbon dioxide" in student_lower:
        return "plants take in carbon dioxide and release oxygen"
    if "leaves" in answer:
        return "leaves are the plant's food-making organs"
    if "oxygen" in answer:
        return "oxygen is the gas plants release when making food"
    if "sunlight" in answer or "water" in answer or "carbon dioxide" in answer:
        return "sunlight, water, and carbon dioxide help plants make food"
    if answer:
        return answer
    return "the correct idea for this question"


def _teaches_concept(explanation: str, correct_answer: str) -> bool:
    text = str(explanation or "").strip().lower()
    if not text or "because" not in text:
        return False
    normalized_answer = _normalize_answer(correct_answer)
    if normalized_answer and normalized_answer not in _normalize_answer(text):
        return False
    if len(re.findall(r"[.!?]", text)) < 1:
        return False
    return True


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
    return f"The main idea is {answer}."


def _is_explanation_consistent_with_result(result: str, explanation: str) -> bool:
    text = str(explanation or "").lower()
    if result == "Incorrect" and re.search(r"\b(correct|accurate|good answer)\b", text):
        return False
    if result == "Correct" and re.search(r"\b(incorrect|wrong|not the right|not correct)\b", text):
        return False
    return True


def _build_short_feedback(concept: str, expected_answer: str) -> str:
    answer = _trim_text(expected_answer, max_words=14)
    return f"You identified the concept of {concept}. To improve, include this key idea: {answer}."


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
    return _trim_text(short or fallback, max_words=40 if max_sentences > 1 else 16)


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
