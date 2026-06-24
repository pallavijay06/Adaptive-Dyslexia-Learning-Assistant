"""Tests for the dedicated Formula Assistant extraction pipeline."""

from backend.stem.formula_extractor import extract_formulas


def test_extract_formulas_detects_simple_equations():
    text = "F = ma\n\nV = IR"

    assert extract_formulas(text) == ["F = ma", "V = IR"]


def test_extract_formulas_removes_duplicates():
    text = "F = ma\nF = ma\nf = ma"

    assert extract_formulas(text) == ["F = ma"]


def test_extract_formulas_empty_input_returns_empty_list():
    assert extract_formulas("") == []
    assert extract_formulas("   ") == []


def test_extract_formulas_detects_multiple_operator_styles():
    text = "x = y + 2\nA = b * h\nc^2 = a^2 + b^2\nr = \u221aA"

    assert extract_formulas(text) == [
        "x = y + 2",
        "A = b * h",
        "c^2 = a^2 + b^2",
        "r = \u221aA",
    ]


def test_extract_formulas_ignores_ordinary_sentences():
    text = "This sentence has words and no formula.\nThe circuit diagram is below."

    assert extract_formulas(text) == []


def test_extract_formulas_rejects_simple_variable_assignments():
    text = "m = 5\na = 2\nR = 4\nI = 10\nF = ma\nV = IR"

    assert extract_formulas(text) == ["F = ma", "V = IR"]


def test_extract_formulas_detects_unicode_multiplication():
    """Test detection of Unicode multiplication symbol (×)."""
    text = "V = I × R"
    assert extract_formulas(text) == ["V = I × R"]


def test_extract_formulas_detects_unicode_division():
    """Test detection of Unicode division symbol (÷)."""
    text = "x ÷ y = z"
    assert extract_formulas(text) == ["x ÷ y = z"]


def test_extract_formulas_detects_unicode_minus():
    """Test detection of Unicode minus symbol (−)."""
    text = "a − b = c"
    assert extract_formulas(text) == ["a − b = c"]


def test_extract_formulas_detects_formula_after_colon():
    """Test detection of formulas appearing after a colon (common in PDFs)."""
    text = "Formula: V = I × R"
    assert extract_formulas(text) == ["V = I × R"]


def test_extract_formulas_detects_formula_with_where_clause():
    """Test detection of formulas in real PDF context."""
    text = """Ohm's Law is a fundamental principle.
Formula: V = I × R
Where V = Voltage (volts), I = Current (amperes), R = Resistance (ohms)."""
    # The first line should extract the main formula
    extracted = extract_formulas(text)
    assert "V = I × R" in extracted


def test_extract_formulas_mixed_unicode_and_ascii_operators():
    """Test detection of formulas with mixed Unicode and ASCII operators."""
    text = "V = I × R\na = b - c\nx ÷ y = z"
    assert extract_formulas(text) == ["V = I × R", "a = b - c", "x ÷ y = z"]

