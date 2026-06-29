from components.quiz_interactive import get_quiz_submission_attempt_metadata


def test_first_attempt_success_only_marks_initial_attempts() -> None:
    attempt_number, first_attempt_success = get_quiz_submission_attempt_metadata(1, True)
    assert attempt_number == 1
    assert first_attempt_success is True


def test_retakes_do_not_overwrite_first_attempt_success() -> None:
    attempt_number, first_attempt_success = get_quiz_submission_attempt_metadata(2, True)
    assert attempt_number == 2
    assert first_attempt_success is False
