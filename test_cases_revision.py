"""Verification script for the Revision step fix."""
import sys
sys.path.insert(0, ".")

from services.understanding_decision_engine import get_understanding_decision_from_data
import services.understanding_decision_engine as ude


def run_case(label, doc_concepts, weak_concepts, retention, trend):
    original = ude._load_revision_topics

    def fake_load(user_id, document_concepts=None):
        doc_set = {c.strip().lower() for c in (document_concepts or [])}
        return [c for c in weak_concepts if c.lower() in doc_set][:5]

    ude._load_revision_topics = fake_load
    try:
        d = get_understanding_decision_from_data(
            comprehension_score=40.0,
            quiz_accuracy_score=40.0,
            retention_score=retention,
            learning_trend=trend,
            document_concepts=doc_concepts,
        )
    finally:
        ude._load_revision_topics = original

    ok = not (d.revision_required and not d.revision_topics)
    print(label)
    print(f"  revision_required : {d.revision_required}")
    print(f"  revision_topics   : {d.revision_topics}")
    print("  PASS" if ok else "  FAIL")
    assert ok, f"INVARIANT BROKEN in {label}"
    print()


run_case(
    "Case 1: Ohm's Law + weak Voltage/Resistance  -> Revision step expected",
    doc_concepts=["Voltage", "Resistance", "Current", "Ohm"],
    weak_concepts=["Voltage", "Resistance"],
    retention=50.0,
    trend="Stable",
)

run_case(
    "Case 2: Ohm's Law + weak Chlorophyll/Photosynthesis  -> NO Revision step",
    doc_concepts=["Voltage", "Resistance", "Current", "Ohm"],
    weak_concepts=["Chlorophyll", "Photosynthesis"],
    retention=50.0,
    trend="Stable",
)

run_case(
    "Case 3: Photosynthesis + weak Chlorophyll/Leaves  -> Revision step expected",
    doc_concepts=["Chlorophyll", "Leaves", "Sunlight", "Glucose"],
    weak_concepts=["Chlorophyll", "Leaves"],
    retention=50.0,
    trend="Stable",
)

print("All cases passed.")
