"""Tests for concise Formula Assistant response handling."""

import pytest

from backend.stem import formula_assistant
from backend.stem.formula_assistant import explain_formula


def test_explain_formula_returns_structured_json(monkeypatch):
    def fake_chat(prompt):
        assert "Return JSON only." in prompt
        return (
            '{"formula": "v = at", '
            '"terms": {'
            '"v": "Velocity", '
            '"a": "Acceleration", '
            '"t": "Time"'
            '}, '
            '"meaning": "Velocity is acceleration times time.", '
            '"example": "A car speeds up as it travels over time."}'
        )

    monkeypatch.setattr(formula_assistant, "chat_with_gemini", fake_chat)

    assert explain_formula("v = at") == {
        "formula": "v = at",
        "terms": {
            "v": "Velocity",
            "a": "Acceleration",
            "t": "Time",
        },
        "meaning": "Velocity is acceleration times time.",
        "example": "A car speeds up as it travels over time.",
    }


def test_explain_formula_retries_after_invalid_text(monkeypatch):
    responses = iter(
        [
            "Here is a long explanation: v means speed.",
            (
                '{"formula": "v = at", '
                '"terms": {"v": "Velocity"}, '
                '"meaning": "Velocity is acceleration times time.", '
                '"example": "A car speeds up as it travels over time."}'
            ),
        ]
    )

    monkeypatch.setattr(
        formula_assistant,
        "chat_with_gemini",
        lambda prompt: next(responses),
    )

    result = explain_formula("v = at")

    assert result["meaning"] == "Velocity is acceleration times time."


def test_explain_formula_uses_library_without_llm(monkeypatch):
    monkeypatch.setattr(
        formula_assistant,
        "chat_with_gemini",
        lambda prompt: (_ for _ in ()).throw(AssertionError("LLM should not be called for library formulas")),
    )

    result = explain_formula("F = ma")

    assert result == {
        "formula": "F = ma",
        "terms": {
            "F": "Force (push or pull)",
            "m": "Mass (how heavy something is)",
            "a": "Acceleration (how quickly speed changes)",
        },
        "meaning": "More force makes an object speed up faster.",
        "example": "A shopping cart needs more force when it is heavy.",
    }


def test_explain_formula_returns_fallback_when_response_is_invalid(monkeypatch):
    formula_assistant.FORMULA_EXPLANATION_CACHE.clear()

    responses = iter([
        'Not a JSON response at all.',
        '{"formula": "v = at", '
        '"terms": {"v": "Velocity"}, '
        '"meaning": "This response has wrong keys and must not be accepted.", '
        '"sentence": "Wrong JSON shape."}'
    ])

    monkeypatch.setattr(
        formula_assistant,
        "chat_with_gemini",
        lambda prompt: next(responses),
    )

    assert explain_formula("v = at") == {
        "formula": "v = at",
        "terms": {},
        "meaning": "Formula explanation unavailable.",
        "example": "No example available.",
    }
