"""Formula Assistant for Prototype 3 STEM Support.

The assistant extracts formulas from document text and asks the existing
project LLM facade for concise, structured, dyslexia-friendly explanations.
It is isolated from app-level UI and routing code.
"""

from __future__ import annotations

import json
import re
from typing import Any

from backend.llm import chat_with_gemini
from backend.stem.formula_extractor import extract_formulas
from backend.stem.formula_library import (
    get_formula_library_explanation,
    normalize_formula_key,
)


MAX_LLM_ATTEMPTS = 2
REQUIRED_RESPONSE_KEYS = {"formula", "terms", "meaning", "example"}
FORMULA_EXPLANATION_CACHE: dict[str, dict[str, Any]] = {}


def explain_formula(formula: str) -> dict[str, Any]:
    """Generate a structured AI explanation for one formula."""

    cleaned_formula = (formula or "").strip()
    if not cleaned_formula:
        return {
            "formula": "",
            "terms": {},
            "meaning": "",
            "example": "",
        }

    library_explanation = get_formula_library_explanation(cleaned_formula)
    if library_explanation is not None:
        return library_explanation

    normalized_key = normalize_formula_key(cleaned_formula)
    cached_response = FORMULA_EXPLANATION_CACHE.get(normalized_key)
    if cached_response is not None:
        return cached_response

    for attempt in range(MAX_LLM_ATTEMPTS):
        try:
            # Formula explanations are short — enforce token limit when invoking chat
            response = chat_with_gemini(
                    _build_formula_prompt(cleaned_formula, retry=attempt > 0),
                )
            explanation = _parse_formula_response(response, cleaned_formula)
            FORMULA_EXPLANATION_CACHE[normalized_key] = explanation
            return explanation
        except Exception:
            continue

    fallback_explanation = _fallback_formula_explanation(cleaned_formula)
    FORMULA_EXPLANATION_CACHE[normalized_key] = fallback_explanation
    return fallback_explanation


def get_formula_explanations(text: str) -> list[dict[str, Any]]:
    """Extract formulas from text and return AI explanations for each one."""

    return [explain_formula(formula) for formula in extract_formulas(text)]


def _build_formula_prompt(formula: str, retry: bool = False) -> str:
    """Build the dyslexia-friendly Formula Assistant prompt."""

    retry_instruction = ""
    if retry:
        retry_instruction = (
            "\nYour previous response did not follow the required JSON-only "
            "format. Return only valid JSON this time.\n"
        )

    return (
        "You are a Formula Assistant for dyslexic learners.\n"
        f"{retry_instruction}"
        "Return JSON only.\n"
        "Never return paragraphs.\n"
        "Never return markdown.\n"
        "Never return bullet lists.\n"
        "Never include extra text before or after the JSON.\n"
        "Never return more than: formula, terms, meaning, example.\n\n"
        f"Formula to explain: {formula}\n\n"
        "Required JSON shape:\n"
        "{\n"
        f'  "formula": "{formula}",\n'
        '  "terms": {\n'
        '    "F": "Force (Push or Pull)",\n'
        '    "m": "Mass (How heavy something is)",\n'
        '    "a": "Acceleration (How quickly speed changes)"\n'
        "  },\n"
        '  "meaning": "Heavier objects need more force to speed up.",\n'
        '  "example": "A full shopping cart needs more pushing force than an empty one."\n'
        "}\n\n"
        "Rules:\n"
        "Each term explanation should be under 10 words when possible.\n"
        "Meaning must be exactly one short sentence, maximum 20 words.\n"
        "Example must be exactly one short real-world sentence, maximum 20 words.\n"
        "Use everyday words only.\n"
        "Avoid mathematical jargon and textbook wording."
    )


def _parse_formula_response(response: str, expected_formula: str) -> dict[str, Any]:
    """Parse and validate the strict Formula Assistant JSON response."""

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError("Formula Assistant response was not pure JSON.") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Formula Assistant response must be a JSON object.")

    if set(parsed.keys()) != REQUIRED_RESPONSE_KEYS:
        raise ValueError("Formula Assistant response has unexpected fields.")

    terms = parsed["terms"]
    meaning = parsed["meaning"]
    example = parsed["example"]

    if not isinstance(terms, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in terms.items()
    ):
        raise ValueError("Formula Assistant terms must be a string dictionary.")

    if not isinstance(meaning, str) or not _is_short_sentence(meaning):
        raise ValueError("Formula Assistant meaning must be one short sentence.")

    if not isinstance(example, str) or not _is_short_sentence(example):
        raise ValueError("Formula Assistant example must be one short sentence.")

    return {
        "formula": expected_formula,
        "terms": {key.strip(): value.strip() for key, value in terms.items()},
        "meaning": meaning.strip(),
        "example": example.strip(),
    }


def _fallback_formula_explanation(formula: str) -> dict[str, Any]:
    """Return a safe fallback explanation when AI output cannot be parsed."""
    return {
        "formula": formula,
        "terms": {},
        "meaning": "Formula explanation unavailable.",
        "example": "No example available.",
    }


def _is_short_sentence(value: str) -> bool:
    """Return whether text is one short sentence of at most 20 words."""

    cleaned = value.strip()
    if not cleaned:
        return False

    if len(re.findall(r"[.!?]", cleaned)) > 1:
        return False

    return len(re.findall(r"\b[\w'-]+\b", cleaned)) <= 20
