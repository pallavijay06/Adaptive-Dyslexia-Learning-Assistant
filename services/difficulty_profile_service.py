"""Difficulty Profile Engine — third learner modelling dimension.

Identifies WHAT the learner struggles with across concepts, question types,
skills, difficulty levels, and error patterns. Updated after every quiz.
"""

from __future__ import annotations

from typing import Any, Mapping


DIFFICULTY_PROFILE_VERSION = "difficulty_profile_v1"

ACCURACY_DIMENSIONS = (
    "concept_difficulty",
    "question_type_difficulty",
    "skill_difficulty",
    "difficulty_level_analysis",
)

ERROR_FREQUENCY_GROUPS = (
    "concept",
    "question_type",
    "skill",
    "difficulty_level",
)


def empty_difficulty_profile() -> dict[str, Any]:
    """Return a fresh difficulty profile structure."""
    return {
        "concept_difficulty": {},
        "question_type_difficulty": {},
        "skill_difficulty": {},
        "difficulty_level_analysis": {},
        "error_frequency": {
            "concept": {},
            "question_type": {},
            "skill": {},
            "difficulty_level": {},
        },
        "version": DIFFICULTY_PROFILE_VERSION,
    }


def _new_accuracy_entry() -> dict[str, float | int]:
    return {
        "attempts": 0,
        "correct": 0,
        "accuracy": 0.0,
        "difficulty_score": 0.0,
    }


def _new_error_entry() -> dict[str, float | int]:
    return {
        "attempts": 0,
        "incorrect": 0,
        "error_frequency": 0.0,
    }


def _recalculate_accuracy_entry(entry: dict[str, Any]) -> None:
    attempts = int(entry.get("attempts") or 0)
    correct = int(entry.get("correct") or 0)
    if attempts <= 0:
        entry["accuracy"] = 0.0
        entry["difficulty_score"] = 0.0
        return
    accuracy = round((correct / attempts) * 100.0, 1)
    entry["accuracy"] = accuracy
    entry["difficulty_score"] = round(100.0 - accuracy, 1)


def _recalculate_error_entry(entry: dict[str, Any]) -> None:
    attempts = int(entry.get("attempts") or 0)
    incorrect = int(entry.get("incorrect") or 0)
    if attempts <= 0:
        entry["error_frequency"] = 0.0
        return
    entry["error_frequency"] = round((incorrect / attempts) * 100.0, 1)


def _update_accuracy_bucket(
    bucket: dict[str, dict[str, Any]],
    key: str,
    is_correct: bool,
) -> None:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return
    if normalized_key not in bucket:
        bucket[normalized_key] = _new_accuracy_entry()
    entry = bucket[normalized_key]
    entry["attempts"] = int(entry.get("attempts") or 0) + 1
    if is_correct:
        entry["correct"] = int(entry.get("correct") or 0) + 1
    _recalculate_accuracy_entry(entry)


def _update_error_bucket(
    bucket: dict[str, dict[str, Any]],
    key: str,
    is_correct: bool,
) -> None:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return
    if normalized_key not in bucket:
        bucket[normalized_key] = _new_error_entry()
    entry = bucket[normalized_key]
    entry["attempts"] = int(entry.get("attempts") or 0) + 1
    if not is_correct:
        entry["incorrect"] = int(entry.get("incorrect") or 0) + 1
    _recalculate_error_entry(entry)


def _extract_question_metadata(question: Mapping[str, Any]) -> dict[str, str]:
    """Read metadata fields already attached by the quiz engine."""
    return {
        "concept": str(question.get("concept") or "").strip(),
        "question_type": str(question.get("subcategory") or "").strip(),
        "skill": str(question.get("skill") or "").strip(),
        "difficulty_level": str(question.get("difficulty") or "").strip(),
    }


def update_difficulty_profile_from_question(
    profile: dict[str, Any],
    question_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Update all five difficulty dimensions from a single evaluated question."""
    metadata = _extract_question_metadata(question_result)
    is_correct = bool(question_result.get("is_correct"))

    _update_accuracy_bucket(profile["concept_difficulty"], metadata["concept"], is_correct)
    _update_accuracy_bucket(
        profile["question_type_difficulty"],
        metadata["question_type"],
        is_correct,
    )
    _update_accuracy_bucket(profile["skill_difficulty"], metadata["skill"], is_correct)
    _update_accuracy_bucket(
        profile["difficulty_level_analysis"],
        metadata["difficulty_level"],
        is_correct,
    )

    error_frequency = profile.setdefault(
        "error_frequency",
        {group: {} for group in ERROR_FREQUENCY_GROUPS},
    )
    _update_error_bucket(error_frequency["concept"], metadata["concept"], is_correct)
    _update_error_bucket(
        error_frequency["question_type"],
        metadata["question_type"],
        is_correct,
    )
    _update_error_bucket(error_frequency["skill"], metadata["skill"], is_correct)
    _update_error_bucket(
        error_frequency["difficulty_level"],
        metadata["difficulty_level"],
        is_correct,
    )

    profile["version"] = DIFFICULTY_PROFILE_VERSION
    return profile


def update_difficulty_profile_from_quiz(
    profile: dict[str, Any] | None,
    quiz_evaluation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Merge every evaluated question from a quiz into the learner difficulty profile."""
    merged = _normalize_profile(profile)
    if not quiz_evaluation:
        return merged

    question_results = quiz_evaluation.get("question_results") or []
    for question_result in question_results:
        if isinstance(question_result, Mapping):
            update_difficulty_profile_from_question(merged, question_result)

    return merged


def _normalize_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(profile, dict) or not profile:
        return empty_difficulty_profile()

    normalized = empty_difficulty_profile()
    for dimension in ACCURACY_DIMENSIONS:
        source = profile.get(dimension)
        if isinstance(source, dict):
            normalized[dimension] = dict(source)

    error_source = profile.get("error_frequency")
    if isinstance(error_source, dict):
        for group in ERROR_FREQUENCY_GROUPS:
            group_data = error_source.get(group)
            if isinstance(group_data, dict):
                normalized["error_frequency"][group] = dict(group_data)

    normalized["version"] = str(profile.get("version") or DIFFICULTY_PROFILE_VERSION)
    return normalized


def refresh_difficulty_profile_from_quiz(
    user_id: int,
    quiz_evaluation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load, update, and persist the difficulty profile after a completed quiz."""
    from database.db import get_difficulty_profile, save_difficulty_profile

    existing = get_difficulty_profile(user_id)
    updated = update_difficulty_profile_from_quiz(existing, quiz_evaluation)
    save_difficulty_profile(user_id, updated)
    return updated


def _sorted_by_difficulty_score(
    bucket: dict[str, dict[str, Any]],
    *,
    min_attempts: int = 1,
) -> list[tuple[str, dict[str, Any]]]:
    items = [
        (key, entry)
        for key, entry in bucket.items()
        if int(entry.get("attempts") or 0) >= min_attempts
    ]
    return sorted(
        items,
        key=lambda item: float(item[1].get("difficulty_score") or 0.0),
        reverse=True,
    )


def _sorted_by_error_frequency(
    error_frequency: dict[str, dict[str, Any]],
    *,
    min_attempts: int = 1,
) -> list[tuple[str, str, dict[str, Any]]]:
    rows: list[tuple[str, str, dict[str, Any]]] = []
    for group_name, bucket in error_frequency.items():
        if not isinstance(bucket, dict):
            continue
        for category, entry in bucket.items():
            if int(entry.get("attempts") or 0) >= min_attempts:
                rows.append((group_name, category, entry))
    return sorted(
        rows,
        key=lambda item: float(item[2].get("error_frequency") or 0.0),
        reverse=True,
    )


def get_difficult_concepts(
    user_id: int,
    *,
    limit: int = 5,
    min_attempts: int = 1,
) -> list[dict[str, Any]]:
    """Return concepts ranked by difficulty score (for Decision Engine)."""
    from database.db import get_difficulty_profile

    profile = _normalize_profile(get_difficulty_profile(user_id))
    ranked = _sorted_by_difficulty_score(
        profile["concept_difficulty"],
        min_attempts=min_attempts,
    )
    return [
        {"concept": name, **entry}
        for name, entry in ranked[:limit]
    ]


def get_difficult_skills(
    user_id: int,
    *,
    limit: int = 5,
    min_attempts: int = 1,
) -> list[dict[str, Any]]:
    """Return cognitive skills ranked by difficulty score (for Decision Engine)."""
    from database.db import get_difficulty_profile

    profile = _normalize_profile(get_difficulty_profile(user_id))
    ranked = _sorted_by_difficulty_score(
        profile["skill_difficulty"],
        min_attempts=min_attempts,
    )
    return [
        {"skill": name, **entry}
        for name, entry in ranked[:limit]
    ]


def get_difficult_question_types(
    user_id: int,
    *,
    limit: int = 5,
    min_attempts: int = 1,
) -> list[dict[str, Any]]:
    """Return question types ranked by difficulty score (for Decision Engine)."""
    from database.db import get_difficulty_profile

    profile = _normalize_profile(get_difficulty_profile(user_id))
    ranked = _sorted_by_difficulty_score(
        profile["question_type_difficulty"],
        min_attempts=min_attempts,
    )
    return [
        {"question_type": name, **entry}
        for name, entry in ranked[:limit]
    ]


def difficulty_score_band(score: float | None) -> tuple[str, str]:
    """Return (label, hex_color) for a difficulty score."""
    value = float(score or 0.0)
    if value <= 25:
        return "Low Difficulty", "#10b981"
    if value <= 50:
        return "Moderate", "#eab308"
    if value <= 75:
        return "High", "#f97316"
    return "Very High", "#ef4444"


def build_difficulty_dashboard_data(profile: dict[str, Any] | None) -> dict[str, Any]:
    """Shape stored profile data for the Progress Dashboard."""
    normalized = _normalize_profile(profile)
    has_data = any(
        normalized[dimension]
        for dimension in ACCURACY_DIMENSIONS
    )

    concept_ranked = _sorted_by_difficulty_score(normalized["concept_difficulty"])
    question_type_ranked = _sorted_by_difficulty_score(normalized["question_type_difficulty"])
    skill_ranked = _sorted_by_difficulty_score(normalized["skill_difficulty"])
    level_ranked = _sorted_by_difficulty_score(normalized["difficulty_level_analysis"])
    error_ranked = _sorted_by_error_frequency(normalized["error_frequency"])

    def _accuracy_rows(
        ranked: list[tuple[str, dict[str, Any]]],
        label_key: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name, entry in ranked:
            score = float(entry.get("difficulty_score") or 0.0)
            band_label, band_color = difficulty_score_band(score)
            rows.append(
                {
                    label_key: name,
                    "Attempts": int(entry.get("attempts") or 0),
                    "Accuracy": float(entry.get("accuracy") or 0.0),
                    "Difficulty Score": score,
                    "Band": band_label,
                    "Band Color": band_color,
                }
            )
        return rows

    error_rows: list[dict[str, Any]] = []
    for group_name, category, entry in error_ranked:
        error_rows.append(
            {
                "Category": category,
                "Type": group_name.replace("_", " ").title(),
                "Attempts": int(entry.get("attempts") or 0),
                "Incorrect": int(entry.get("incorrect") or 0),
                "Error Frequency": float(entry.get("error_frequency") or 0.0),
            }
        )

    def _top_item(
        ranked: list[tuple[str, dict[str, Any]]],
        label_key: str,
    ) -> dict[str, Any] | None:
        if not ranked:
            return None
        name, entry = ranked[0]
        score = float(entry.get("difficulty_score") or 0.0)
        band_label, band_color = difficulty_score_band(score)
        return {
            label_key: name,
            "Attempts": int(entry.get("attempts") or 0),
            "Accuracy": float(entry.get("accuracy") or 0.0),
            "Difficulty Score": score,
            "Band": band_label,
            "Band Color": band_color,
        }

    top_error = None
    if error_ranked:
        group_name, category, entry = error_ranked[0]
        top_error = {
            "Category": category,
            "Type": group_name.replace("_", " ").title(),
            "Attempts": int(entry.get("attempts") or 0),
            "Incorrect": int(entry.get("incorrect") or 0),
            "Error Frequency": float(entry.get("error_frequency") or 0.0),
        }

    return {
        "has_data": has_data,
        "summary": {
            "most_difficult_concept": _top_item(concept_ranked, "Concept"),
            "most_difficult_question_type": _top_item(question_type_ranked, "Question Type"),
            "most_difficult_skill": _top_item(skill_ranked, "Skill"),
            "most_difficult_level": _top_item(level_ranked, "Level"),
            "highest_error_frequency": top_error,
        },
        "concept_difficulty": _accuracy_rows(concept_ranked, "Concept"),
        "question_type_difficulty": _accuracy_rows(question_type_ranked, "Question Type"),
        "skill_difficulty": _accuracy_rows(skill_ranked, "Skill"),
        "difficulty_level_analysis": _accuracy_rows(level_ranked, "Level"),
        "error_frequency": error_rows,
        "raw_profile": normalized,
    }
