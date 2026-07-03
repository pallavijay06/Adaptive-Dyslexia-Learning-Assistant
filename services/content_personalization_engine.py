"""Content Personalization Engine.

Single responsibility: answer "Within the uploaded document, which concepts
should receive greater emphasis?"

IMPORTANT: This engine is document-driven. It NEVER decides what topic to
teach. It ONLY personalizes the uploaded content by cross-referencing the
learner's difficulty profile against the concepts extracted from the document.

Inputs (read-only):
  - difficulty_profile_service → get_difficult_concepts (difficulty_score,
    error_frequency, attempts, accuracy per concept)
  - document_concepts: list[str] — extracted from the uploaded document by the
    caller (parser pipeline). The engine does NOT extract concepts itself.

Outputs: ContentPersonalizationDecision dataclass.

Decision method: Evidence-Based Decision (EBD) framework.
  Each available signal (difficulty score, error frequency, attempt count,
  recent improvement) contributes weighted evidence toward a priority level
  for every document concept. The priority with the highest accumulated
  evidence wins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Output contract  (unchanged)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContentPersonalizationDecision:
    high_priority_concepts: list[str]
    medium_priority_concepts: list[str]
    low_priority_concepts: list[str]
    extra_examples: list[str]
    quiz_focus: list[str]
    revision_focus: list[str]
    confidence: float
    reasoning: list[str]


# ---------------------------------------------------------------------------
# EBD evidence weights  (kept as module-level constants)
# ---------------------------------------------------------------------------

# Importance  : Very High  → weight 5
# Importance  : High       → weight 4
# Importance  : Medium     → weight 3
# Importance  : Supporting → weight 2

_W_DIFFICULTY_SCORE  = 5   # Very High  — primary signal
_W_ERROR_FREQUENCY   = 4   # High       — how often the learner gets it wrong
_W_ATTEMPT_COUNT     = 3   # Medium     — exposure depth
_W_IMPROVEMENT       = 2   # Supporting — recent accuracy change (negative = regressing)

_MIN_ATTEMPTS_FOR_SIGNAL = 1

# Priority candidates
_CANDIDATES = ("High Priority", "Medium Priority", "Low Priority")

# Soft boundary centres for each priority on a 0-100 difficulty scale.
#   High Priority   centre = 75   (very hard concepts)
#   Medium Priority centre = 45   (moderately hard)
#   Low Priority    centre = 15   (easy / no history)
_CENTRES: dict[str, float] = {
    "High Priority":   75.0,
    "Medium Priority": 45.0,
    "Low Priority":    15.0,
}
_HALF_WIDTH: dict[str, float] = {
    "High Priority":   30.0,
    "Medium Priority": 30.0,
    "Low Priority":    20.0,
}

# Secondary signal centres (error_frequency is also 0-100)
_ERROR_CENTRES: dict[str, float] = {
    "High Priority":   70.0,
    "Medium Priority": 40.0,
    "Low Priority":    10.0,
}
_ERROR_HALF_WIDTH: dict[str, float] = {
    "High Priority":   35.0,
    "Medium Priority": 35.0,
    "Low Priority":    20.0,
}

# Attempt count: more attempts → more data → stronger signal for High/Medium
# Normalised to 0-100 by capping at 20 attempts = 100.
_MAX_ATTEMPTS_NORM = 20.0

# Extra-examples / quiz-focus / revision-focus thresholds on the
# *winning evidence score* for High Priority (not raw difficulty).
# These are applied after the EBD winner is determined.
_EXTRA_EXAMPLES_MIN_EVIDENCE  = 3.0   # High Priority evidence ≥ this
_QUIZ_FOCUS_MIN_EVIDENCE      = 2.0
_REVISION_FOCUS_MIN_EVIDENCE  = 3.5


# ---------------------------------------------------------------------------
# Public API  (signatures unchanged)
# ---------------------------------------------------------------------------

def get_content_personalization_decision(
    user_id: int,
    document_concepts: list[str],
) -> ContentPersonalizationDecision:
    """Compute content personalization for the given document concepts."""
    if not document_concepts:
        return _empty_decision("No document concepts provided.")
    full_profile = _load_full_profile(user_id)
    return _decide(document_concepts, full_profile)


def get_content_personalization_decision_from_data(
    document_concepts: list[str],
    difficulty_map: dict[str, float],
) -> ContentPersonalizationDecision:
    """Pure-function variant — accepts a pre-built difficulty map (for Master Decision Engine).

    The difficulty_map is {concept_name: difficulty_score}.  When only a
    difficulty_score is available (no error_frequency / attempts), the EBD
    framework uses only the primary signal and reduces confidence accordingly.
    """
    if not document_concepts:
        return _empty_decision("No document concepts provided.")
    # Wrap the flat map into the richer profile format expected by _decide
    full_profile = {
        name: {"difficulty_score": score, "error_frequency": None, "attempts": None, "accuracy": None}
        for name, score in difficulty_map.items()
    }
    return _decide(document_concepts, full_profile)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_full_profile(user_id: int) -> dict[str, dict[str, Any]]:
    """Return {concept_name: {difficulty_score, error_frequency, attempts, accuracy}}."""
    from services.difficulty_profile_service import get_difficult_concepts

    entries = get_difficult_concepts(user_id, limit=200, min_attempts=_MIN_ATTEMPTS_FOR_SIGNAL)
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        name = str(entry.get("concept") or "").strip()
        if not name:
            continue
        result[name] = {
            "difficulty_score": float(entry.get("difficulty_score") or 0.0),
            "error_frequency":  _safe_float(entry.get("error_frequency")),
            "attempts":         _safe_float(entry.get("attempts")),
            "accuracy":         _safe_float(entry.get("accuracy")),
        }
    return result


# ---------------------------------------------------------------------------
# EBD core helpers
# ---------------------------------------------------------------------------

def _membership(value: float, centre: float, half_width: float) -> float:
    """Triangular membership: 1.0 at centre, 0.0 at ±half_width."""
    return round(max(0.0, 1.0 - abs(value - centre) / half_width), 4)


def _accumulate(
    value: float,
    weight: int,
    centres: dict[str, float],
    half_widths: dict[str, float],
    evidence: dict[str, float],
    contributions: dict[str, list[str]],
    label: str,
) -> None:
    for candidate in _CANDIDATES:
        m = _membership(value, centres[candidate], half_widths[candidate])
        contrib = weight * m
        evidence[candidate] = evidence.get(candidate, 0.0) + contrib
        if m > 0.05:
            contributions[candidate].append(
                f"{label} (value={value:.1f}, membership={m:.2f}, "
                f"weight={weight}, contribution={contrib:.2f})"
            )


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

def _decide(
    document_concepts: list[str],
    full_profile: dict[str, dict[str, Any]],
) -> ContentPersonalizationDecision:

    # Normalise document concepts for case-insensitive lookup
    doc_concepts = [c.strip() for c in document_concepts if c.strip()]
    profile_lower = {k.lower(): (k, v) for k, v in full_profile.items()}

    high_priority:   list[str] = []
    medium_priority: list[str] = []
    low_priority:    list[str] = []
    extra_examples:  list[str] = []
    quiz_focus:      list[str] = []
    revision_focus:  list[str] = []

    all_reasoning: list[str] = []
    known_count = 0
    concept_confidences: list[float] = []

    for concept in doc_concepts:
        profile_entry = profile_lower.get(concept.lower())
        has_history   = profile_entry is not None

        if has_history:
            known_count += 1
            _, data = profile_entry
        else:
            data = {"difficulty_score": 0.0, "error_frequency": None, "attempts": None, "accuracy": None}

        evidence: dict[str, float]          = {c: 0.0 for c in _CANDIDATES}
        contributions: dict[str, list[str]] = {c: []  for c in _CANDIDATES}

        # Signal 1: Difficulty score (weight 5, Very High)
        diff_score = float(data.get("difficulty_score") or 0.0)
        _accumulate(diff_score, _W_DIFFICULTY_SCORE, _CENTRES, _HALF_WIDTH,
                    evidence, contributions, "Difficulty score")

        # Signal 2: Error frequency (weight 4, High) — if available
        err_freq = _safe_float(data.get("error_frequency"))
        if err_freq is not None:
            _accumulate(err_freq, _W_ERROR_FREQUENCY, _ERROR_CENTRES, _ERROR_HALF_WIDTH,
                        evidence, contributions, "Error frequency")

        # Signal 3: Attempt count normalised to 0-100 (weight 3, Medium)
        # More attempts → more exposure → stronger evidence for the difficulty signal
        attempts = _safe_float(data.get("attempts"))
        if attempts is not None:
            attempts_norm = min(100.0, (attempts / _MAX_ATTEMPTS_NORM) * 100.0)
            _accumulate(attempts_norm, _W_ATTEMPT_COUNT, _CENTRES, _HALF_WIDTH,
                        evidence, contributions, f"Attempt count (normalised {attempts_norm:.1f})")

        # Signal 4: Recent improvement — accuracy inverted to difficulty direction (weight 2, Supporting)
        # accuracy is 0-100; low accuracy = high difficulty = supports High Priority
        accuracy = _safe_float(data.get("accuracy"))
        if accuracy is not None:
            inverted_accuracy = 100.0 - accuracy   # convert to difficulty direction
            _accumulate(inverted_accuracy, _W_IMPROVEMENT, _CENTRES, _HALF_WIDTH,
                        evidence, contributions, f"Inverted accuracy (difficulty proxy {inverted_accuracy:.1f})")

        # --- Winner for this concept ---
        winner = max(evidence, key=lambda c: evidence[c])
        winner_score = evidence[winner]

        # --- Per-concept confidence ---
        total_ev = sum(evidence.values())
        agreement = (winner_score / total_ev) if total_ev > 0 else 0.0
        sorted_ev = sorted(evidence.values(), reverse=True)
        runner_up_ev = sorted_ev[1] if len(sorted_ev) > 1 else 0.0
        conflict = (runner_up_ev / winner_score) if winner_score > 0 else 0.0
        signals_present = sum([
            diff_score > 0 or has_history,
            err_freq is not None,
            attempts is not None,
            accuracy is not None,
        ])
        completeness = signals_present / 4.0
        concept_conf = round(min(1.0, agreement * (1.0 - 0.4 * conflict) * (0.4 + 0.6 * completeness)), 2)
        concept_confidences.append(concept_conf)

        # --- Assign to priority bucket ---
        if winner == "High Priority":
            high_priority.append(concept)
        elif winner == "Medium Priority":
            medium_priority.append(concept)
        else:
            low_priority.append(concept)

        # --- Secondary flags based on High Priority evidence score ---
        high_ev = evidence["High Priority"]
        if high_ev >= _EXTRA_EXAMPLES_MIN_EVIDENCE:
            extra_examples.append(concept)
        if high_ev >= _QUIZ_FOCUS_MIN_EVIDENCE:
            quiz_focus.append(concept)
        if high_ev >= _REVISION_FOCUS_MIN_EVIDENCE:
            revision_focus.append(concept)

        # --- Per-concept reasoning ---
        contrib_lines = contributions[winner]
        if contrib_lines:
            all_reasoning.append(
                f"'{concept}' → {winner} (evidence {winner_score:.2f}): "
                + "; ".join(contrib_lines)
            )
        elif not has_history:
            all_reasoning.append(
                f"'{concept}' → Low Priority — no quiz history for this concept."
            )
        else:
            all_reasoning.append(f"'{concept}' → {winner} (evidence {winner_score:.2f}).")

    # --- Overall confidence ---
    total = len(doc_concepts)
    data_completeness = known_count / total if total > 0 else 0.0
    avg_concept_conf  = sum(concept_confidences) / len(concept_confidences) if concept_confidences else 0.0
    confidence = round(min(1.0, avg_concept_conf * (0.5 + 0.5 * data_completeness)), 2)

    if known_count == 0:
        all_reasoning.append(
            "No quiz history found for any document concept — "
            "all concepts assigned Low Priority. Confidence is 0."
        )
        confidence = 0.0
    else:
        all_reasoning.append(
            f"{known_count}/{total} document concepts have quiz history. "
            f"Overall confidence: {confidence:.2f}."
        )

    return ContentPersonalizationDecision(
        high_priority_concepts=high_priority,
        medium_priority_concepts=medium_priority,
        low_priority_concepts=low_priority,
        extra_examples=extra_examples,
        quiz_focus=quiz_focus,
        revision_focus=revision_focus,
        confidence=confidence,
        reasoning=all_reasoning,
    )


def _empty_decision(reason: str) -> ContentPersonalizationDecision:
    return ContentPersonalizationDecision(
        high_priority_concepts=[],
        medium_priority_concepts=[],
        low_priority_concepts=[],
        extra_examples=[],
        quiz_focus=[],
        revision_focus=[],
        confidence=0.0,
        reasoning=[reason],
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
