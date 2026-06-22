"""Tests for concise Formula Assistant response handling."""

import pytest

from backend.stem import formula_assistant
from backend.stem.formula_assistant import explain_formula


def test_explain_formula_returns_structured_json(monkeypatch):
    def fake_chat(prompt):
        assert "Return JSON only." in prompt
        return (
            '{"formula": "F = ma", '
            '"terms": {'
            '"F": "Force (Push or Pull)", '
            '"m": "Mass (How heavy something is)", '
            '"a": "Acceleration (How quickly speed changes)"'
            '}, '
            '"meaning": "Heavier objects need more force to speed up.", '
            '"example": "A full shopping cart needs more pushing force than an empty one."}'
        )

    monkeypatch.setattr(formula_assistant, "chat_with_gemini", fake_chat)

    assert explain_formula("F = ma") == {
        "formula": "F = ma",
        "terms": {
            "F": "Force (Push or Pull)",
            "m": "Mass (How heavy something is)",
            "a": "Acceleration (How quickly speed changes)",
        },
        "meaning": "Heavier objects need more force to speed up.",
        "example": "A full shopping cart needs more pushing force than an empty one.",
    }


def test_explain_formula_retries_after_invalid_text(monkeypatch):
    responses = iter(
        [
            "Here is a long explanation: F means force.",
            (
                '{"formula": "F = ma", '
                '"terms": {"F": "Force (Push or Pull)"}, '
                '"meaning": "Force makes things speed up.", '
                '"example": "A cart moves faster when you push it."}'
            ),
        ]
    )

    monkeypatch.setattr(
        formula_assistant,
        "chat_with_gemini",
        lambda prompt: next(responses),
    )

    result = explain_formula("F = ma")

    assert result["meaning"] == "Force makes things speed up."


def test_explain_formula_rejects_long_meaning(monkeypatch):
    monkeypatch.setattr(
        formula_assistant,
        "chat_with_gemini",
            lambda prompt: (
                '{"formula": "F = ma", '
                '"terms": {"F": "Force (Push or Pull)"}, '
                '"meaning": "This explanation has too many words because it keeps adding more and more ideas until it is hard to read for many learners.", '
                '"example": "A cart moves faster when pushed."}'
            ),
        )

    with pytest.raises(ValueError):
        explain_formula("F = ma")
