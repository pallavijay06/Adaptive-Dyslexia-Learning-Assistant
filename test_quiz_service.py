import re

from services.quiz_service import evaluate_short_answer_locally, _fuzzy_text_similarity


def test_fuzzy_spellings_are_recognized_as_correct():
    expected = "oxygen"
    for answer in ["Oxyen", "oxigen", "oxegen"]:
        evaluation = evaluate_short_answer_locally(answer, expected, question_text="What gas is released?")
        assert evaluation["result"] in {"Correct", "Partially Correct"}
        assert "oxygen" in evaluation["feedback"].lower() or "oxygen" in evaluation["improvement_tip"].lower()


def test_similar_concept_partial_credit():
    expected = "plants make food using sunlight"
    student = "plants make food"
    evaluation = evaluate_short_answer_locally(student, expected, question_text="What is photosynthesis?")
    assert evaluation["result"] == "Partially Correct"
    assert re.search(r"sunlight", evaluation["feedback"].lower())


def test_fuzzy_text_similarity_threshold():
    assert _fuzzy_text_similarity("oxygen", "oxyen") >= 0.86
    assert _fuzzy_text_similarity("photosynthesis", "photosythesis") >= 0.92
    assert _fuzzy_text_similarity("evaporation", "evapouration") >= 0.86


def test_equivalent_answers_are_correct():
    evaluation = evaluate_short_answer_locally(
        "leaves",
        "in the leaves",
        question_text="Where does photosynthesis mainly occur?",
    )
    assert evaluation["result"] == "Correct"
    assert evaluation["feedback"].startswith("Correct.")
    assert "leaves" in evaluation["feedback"].lower()


def test_incorrect_answers_get_clear_explanations():
    evaluation = evaluate_short_answer_locally(
        "roots",
        "leaves",
        question_text="Where does photosynthesis mainly occur?",
    )
    assert evaluation["result"] == "Incorrect"
    assert "incorrect" in evaluation["feedback"].lower()
    assert "leaves" in evaluation["feedback"].lower()
    assert "roots" in evaluation["feedback"].lower()


def test_correct_feedback_teaches_the_concept():
    evaluation = evaluate_short_answer_locally(
        "leaves",
        "leaves",
        question_text="Where does photosynthesis mainly occur?",
    )
    feedback = evaluation["feedback"].lower()
    assert evaluation["result"] == "Correct"
    assert "because" in feedback
    assert "leaves" in feedback
    assert "remember:" in feedback


def test_partially_correct_feedback_mentions_missing_details():
    evaluation = evaluate_short_answer_locally(
        "plants make food",
        "plants make food using sunlight",
        question_text="What is photosynthesis?",
    )
    feedback = evaluation["feedback"].lower()
    assert evaluation["result"] == "Partially Correct"
    assert "full answer" in feedback or "correct answer" in feedback
    assert "because" in feedback
    assert "remember:" in feedback


def test_incorrect_feedback_ends_with_memory_tip():
    evaluation = evaluate_short_answer_locally(
        "roots",
        "leaves",
        question_text="Where does photosynthesis mainly occur?",
    )
    feedback = evaluation["feedback"].lower()
    assert feedback.endswith("leaves make food, roots absorb water") or "remember:" in feedback
