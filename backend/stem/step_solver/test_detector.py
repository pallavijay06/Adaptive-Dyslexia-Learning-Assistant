"""Tests for the Step Solver problem detector.

Tests cover all detection categories:
- ARITHMETIC
- ALGEBRA
- SUBSTITUTION
- REARRANGEMENT
- UNKNOWN
"""

import pytest
from .detector import detect_problem_type, _is_arithmetic, _is_algebra, _is_substitution, _is_rearrangement
from .models import ProblemType


class TestArithmeticDetection:
    """Test arithmetic problem detection."""

    def test_simple_addition(self):
        """Simple addition should be detected as arithmetic."""
        result = detect_problem_type("10 + 5")
        assert result == ProblemType.ARITHMETIC

    def test_multiplication_and_addition(self):
        """Mixed arithmetic operations should be detected."""
        result = detect_problem_type("10 + 5 * 2")
        assert result == ProblemType.ARITHMETIC

    def test_parentheses(self):
        """Arithmetic with parentheses should be detected."""
        result = detect_problem_type("(8 + 2) * 3")
        assert result == ProblemType.ARITHMETIC

    def test_exponents(self):
        """Arithmetic with exponents should be detected."""
        result = detect_problem_type("3^2 + 4^2")
        assert result == ProblemType.ARITHMETIC

    def test_division(self):
        """Division should be detected as arithmetic."""
        result = detect_problem_type("20 / 4")
        assert result == ProblemType.ARITHMETIC

    def test_decimals(self):
        """Arithmetic with decimals should be detected."""
        result = detect_problem_type("5.5 + 2.3 * 1.1")
        assert result == ProblemType.ARITHMETIC

    def test_helper_function_arithmetic(self):
        """Test the arithmetic helper function directly."""
        assert _is_arithmetic("10 + 5") is True
        assert _is_arithmetic("(8 + 2) * 3") is True
        assert _is_arithmetic("20 / 4") is True


class TestAlgebraDetection:
    """Test algebra problem detection."""

    def test_simple_linear_equation(self):
        """Simple linear equation should be detected as algebra."""
        result = detect_problem_type("x + 5 = 12")
        assert result == ProblemType.ALGEBRA

    def test_linear_with_coefficient(self):
        """Linear equation with coefficient should be detected."""
        result = detect_problem_type("2x - 4 = 10")
        assert result == ProblemType.ALGEBRA

    def test_quadratic_equation(self):
        """Quadratic equation should be detected as algebra."""
        result = detect_problem_type("x² + 3x + 2 = 0")
        assert result == ProblemType.ALGEBRA

    def test_another_linear_equation(self):
        """Another linear equation example."""
        result = detect_problem_type("3x + 7 = 22")
        assert result == ProblemType.ALGEBRA

    def test_equation_with_y(self):
        """Equation with y variable should be detected."""
        result = detect_problem_type("y + 10 = 20")
        assert result == ProblemType.ALGEBRA

    def test_equation_with_z(self):
        """Equation with z variable should be detected."""
        result = detect_problem_type("2z - 3 = 5")
        assert result == ProblemType.ALGEBRA

    def test_helper_function_algebra(self):
        """Test the algebra helper function directly."""
        assert _is_algebra("x + 5 = 12") is True
        assert _is_algebra("2x - 4 = 10") is True
        assert _is_algebra("x² + 3x + 2 = 0") is True


class TestSubstitutionDetection:
    """Test substitution problem detection."""

    def test_force_formula_substitution(self):
        """Force formula with substitution should be detected."""
        text = "F = ma\nm = 5\na = 2"
        result = detect_problem_type(text)
        assert result == ProblemType.SUBSTITUTION

    def test_voltage_formula_substitution(self):
        """Voltage formula with substitution should be detected."""
        text = "V = IR\nI = 2\nR = 5"
        result = detect_problem_type(text)
        assert result == ProblemType.SUBSTITUTION

    def test_substitution_multiline(self):
        """Multiline substitution should be detected."""
        text = "P = VI\nV = 10\nI = 3"
        result = detect_problem_type(text)
        assert result == ProblemType.SUBSTITUTION

    def test_substitution_with_decimals(self):
        """Substitution with decimal values should be detected."""
        text = "E = mc²\nm = 2.5\nc = 3.0"
        result = detect_problem_type(text)
        assert result == ProblemType.SUBSTITUTION

    def test_helper_function_substitution(self):
        """Test the substitution helper function directly."""
        text = "F = ma\nm = 5\na = 2"
        assert _is_substitution(text) is True


class TestRearrangementDetection:
    """Test rearrangement problem detection."""

    def test_force_rearrangement_find(self):
        """Force formula rearrangement with Find should be detected."""
        text = "F = ma\nFind m\nF = 20\na = 5"
        result = detect_problem_type(text)
        assert result == ProblemType.REARRANGEMENT

    def test_voltage_rearrangement_solve_for(self):
        """Voltage formula rearrangement with Solve for should be detected."""
        text = "V = IR\nSolve for R\nV = 12\nI = 2"
        result = detect_problem_type(text)
        assert result == ProblemType.REARRANGEMENT

    def test_rearrangement_find_keyword(self):
        """Rearrangement with Find keyword should be detected."""
        text = "P = VI\nFind V\nP = 50\nI = 5"
        result = detect_problem_type(text)
        assert result == ProblemType.REARRANGEMENT

    def test_rearrangement_solve_keyword(self):
        """Rearrangement with Solve for keyword should be detected."""
        text = "E = mc²\nSolve for m\nE = 100\nc = 2"
        result = detect_problem_type(text)
        assert result == ProblemType.REARRANGEMENT

    def test_helper_function_rearrangement(self):
        """Test the rearrangement helper function directly."""
        text = "F = ma\nFind m\nF = 20\na = 5"
        assert _is_rearrangement(text) is True


class TestUnknownDetection:
    """Test unknown/non-matching text detection."""

    def test_plain_text(self):
        """Plain text should be detected as unknown."""
        result = detect_problem_type("Hello world")
        assert result == ProblemType.UNKNOWN

    def test_explanatory_text(self):
        """Explanatory physics text should be detected as unknown."""
        result = detect_problem_type("Explain Newton's Law")
        assert result == ProblemType.UNKNOWN

    def test_notes(self):
        """Physics notes should be detected as unknown."""
        result = detect_problem_type("Physics notes on motion")
        assert result == ProblemType.UNKNOWN

    def test_random_text(self):
        """Random text should be detected as unknown."""
        result = detect_problem_type("Random text without structure")
        assert result == ProblemType.UNKNOWN

    def test_empty_string(self):
        """Empty string should be detected as unknown."""
        result = detect_problem_type("")
        assert result == ProblemType.UNKNOWN

    def test_just_formula_no_context(self):
        """Just a formula without context or assignments should be unknown."""
        result = detect_problem_type("F = ma")
        # This is just a formula, not substitution or rearrangement
        assert result == ProblemType.UNKNOWN


class TestDetectionPriority:
    """Test that detection order is correctly prioritized."""

    def test_rearrangement_before_substitution(self):
        """Rearrangement should be detected before substitution."""
        # This has both formula and assignments, but also Find keyword
        # Should be classified as REARRANGEMENT, not SUBSTITUTION
        text = "F = ma\nFind m\nm = 5\na = 2"
        result = detect_problem_type(text)
        assert result == ProblemType.REARRANGEMENT

    def test_substitution_before_algebra(self):
        """Substitution should be detected before algebra."""
        # Formula with assignments should be SUBSTITUTION
        text = "a = b\na = 5\nb = 3"
        result = detect_problem_type(text)
        assert result == ProblemType.SUBSTITUTION

    def test_algebra_before_arithmetic(self):
        """Algebra should be detected before arithmetic."""
        # Equation with variable should be ALGEBRA
        result = detect_problem_type("x + 5 = 12")
        assert result == ProblemType.ALGEBRA


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiline_with_extra_spaces(self):
        """Multiline problems with extra spaces should be detected."""
        text = "F = ma\n\nm = 5\n\na = 2"
        result = detect_problem_type(text)
        assert result == ProblemType.SUBSTITUTION

    def test_uppercase_keywords(self):
        """Uppercase Find/Solve keywords should be detected."""
        text = "F = ma\nFIND m\nF = 20\na = 5"
        result = detect_problem_type(text)
        assert result == ProblemType.REARRANGEMENT

    def test_mixed_case_keywords(self):
        """Mixed case Find/Solve keywords should be detected."""
        text = "F = ma\nFiNd m\nF = 20\na = 5"
        result = detect_problem_type(text)
        assert result == ProblemType.REARRANGEMENT

    def test_negative_numbers(self):
        """Arithmetic with negative numbers should be detected."""
        result = detect_problem_type("10 + (-5) * 2")
        assert result == ProblemType.ARITHMETIC

    def test_complex_quadratic(self):
        """Complex quadratic equation should be detected."""
        result = detect_problem_type("x² - 5x + 6 = 0")
        assert result == ProblemType.ALGEBRA


class TestIntegration:
    """Integration tests combining multiple scenarios."""

    def test_all_categories_in_sequence(self):
        """Test that all categories are correctly identified."""
        test_cases = [
            ("F = ma\nFind m\nF = 20\na = 5", ProblemType.REARRANGEMENT),
            ("F = ma\nm = 5\na = 2", ProblemType.SUBSTITUTION),
            ("x + 5 = 12", ProblemType.ALGEBRA),
            ("10 + 5 * 2", ProblemType.ARITHMETIC),
            ("Hello world", ProblemType.UNKNOWN),
        ]

        for text, expected_type in test_cases:
            result = detect_problem_type(text)
            assert result == expected_type, f"Failed for: {text}"

    def test_realistic_physics_problems(self):
        """Test with realistic physics problem examples."""
        # Ohm's Law rearrangement
        ohm_rearrange = "V = IR\nSolve for I\nV = 12\nR = 4"
        assert detect_problem_type(ohm_rearrange) == ProblemType.REARRANGEMENT

        # Ohm's Law substitution
        ohm_sub = "V = IR\nI = 3\nR = 4"
        assert detect_problem_type(ohm_sub) == ProblemType.SUBSTITUTION

    def test_realistic_math_problems(self):
        """Test with realistic math problem examples."""
        # Quadratic equation
        assert detect_problem_type("x² + 2x - 3 = 0") == ProblemType.ALGEBRA

        # Complex arithmetic
        assert detect_problem_type("(5 + 3) * (2 - 1)") == ProblemType.ARITHMETIC


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
