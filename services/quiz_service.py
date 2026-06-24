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

logger = logging.getLogger(__name__)

_QUIZ_GENERATION_FALLBACK_USED = False

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
        return copy.deepcopy(cached_mcqs)
    logger.info("[CACHE MISS] Quiz MCQ")

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

    try:
        response = _run_quiz_prompt(prompt, text)
        mcqs = _parse_json_response(response)
        if not isinstance(mcqs, list):
            logger.warning("[Quiz Parser] Parsed MCQ response is not a list or is empty.")
            mcqs = None
    except Exception:
        logger.exception("[Quiz Parser] MCQ generation failed. Falling back to local quiz generation.")
        mcqs = None

    if mcqs is None:
        _QUIZ_GENERATION_FALLBACK_USED = True
        logger.warning("[Quiz Parser] Falling back to local quiz generation")
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
                "question": question,
                "options": [str(opt).strip() for opt in options],
                "answer": answer,
            }
        )

    if not validated_mcqs:
        logger.warning("[Quiz] MCQ parsing returned no valid questions. Using local fallback quiz generation.")
        _QUIZ_GENERATION_FALLBACK_USED = True
        validated_mcqs = _local_generate_mcq_quiz(text, num_questions)

    set_cache_value(cache_key, validated_mcqs, ttl_hours=QUIZ_CACHE_TTL_HOURS)
    return copy.deepcopy(validated_mcqs)


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
        return copy.deepcopy(cached_questions)

    prompt = (
        "Create a list of learner-friendly short answer questions from the document below. "
        f"Generate exactly {num_questions} questions. "
        "Return only a JSON array where each element has the keys:\n"
        "- question\n"
        "- answer\n"
        "Use simple language and keep the expected answers concise."
    )

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
        validated_questions.append({"question": question, "answer": answer})

    if not validated_questions:
        logger.warning("[Quiz] Short question parsing returned no valid questions. Using local fallback quiz generation.")
        _QUIZ_GENERATION_FALLBACK_USED = True
        validated_questions = _local_generate_short_questions(text, num_questions)

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
        "- result (\"Correct\", \"Partially Correct\", or \"Incorrect\")\n"
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
    evaluation["result"] = _normalize_evaluation_result(evaluation.get("result"))
    if evaluation["result"] not in {"Correct", "Partially Correct", "Incorrect"}:
        evaluation["result"] = _result_from_score(local_score, evaluation["max_score"])

    explanation = _build_question_explanation(question_text, student_answer_text, expected_answer_text, evaluation["result"])
    if not _is_explanation_consistent_with_result(evaluation["result"], explanation) or not _teaches_concept(explanation, expected_answer_text):
        explanation = _build_question_explanation(question_text, student_answer_text, expected_answer_text, evaluation["result"])

    evaluation["feedback"] = _shorten_sentences(
        explanation,
        fallback=explanation,
        max_sentences=3,
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
    # Add spelling note when LLM result seems correct but student had a minor typo
    spelling_note = _detect_spelling_note(student_answer_text, expected_answer_text)
    if spelling_note:
        evaluation["spelling_note"] = f'The correct spelling is "{spelling_note}".'
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

        evaluations.append(
            {
                "question": question,
                "your_answer": student_answer or "No answer",
                "correct_answer": expected_answer,
                "result": result,
                "explanation": _shorten_sentences(explanation, fallback=explanation, max_sentences=3),
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
    payload = _extract_json_payload(text)
    logger.info("[Quiz Parser] Raw response received")
    print("\n========== RAW QUIZ RESPONSE ==========")
    print(payload)
    print("=======================================\n")

    if not payload:
        logger.warning("[Quiz Parser] No JSON payload found in model response.")
        return None

    cleaned = _strip_markdown_wrappers(payload)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    try:
        return ast.literal_eval(cleaned)
    except Exception:
        pass

    repaired = _repair_json_text(cleaned)
    try:
        parsed = json.loads(repaired)
        logger.info("[Quiz Parser] JSON repaired successfully")
        return parsed
    except json.JSONDecodeError:
        pass

    try:
        parsed = ast.literal_eval(repaired)
        logger.info("[Quiz Parser] JSON repaired successfully")
        return parsed
    except Exception:
        pass

    fallback = _extract_quiz_structures_from_text(text)
    if fallback is not None:
        logger.warning("[Quiz Parser] Falling back to extracted quiz structures from raw response")
        return fallback

    logger.exception("[Quiz Parser] JSON parsing failed for quiz service response.")
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


def _local_generate_mcq_quiz(text: str, num_questions: int) -> list[dict[str, str]]:
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
    return mcqs[:num_questions]


def _local_generate_short_questions(text: str, num_questions: int) -> list[dict[str, str]]:
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

    return questions


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
    if result_text in {"Perfectly Correct", "Perfect"}:
        return "Correct"
    if result_text in {"Partially", "Partially Correct"}:
        return "Partially Correct"
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
