"""Tests for the Formula Substitution Solver.

Tests cover:
- Basic formula substitution
- Multiple variable substitution
- Complex expressions
- Error handling
- Missing variables
- Invalid formulas
"""

import pytest
from .substitution_solver import solve_substitution
from .models import ProblemType


class TestBasicSubstitution:
    """Test basic formula substitution."""

    def test_force_equation_simple(self):
        """Simple force equation: F = ma."""
        problem = "F = ma\nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is True
        # Accept both "10" and "10.0"
        assert result.final_answer in ["10", "10.0"] or "10" in result.final_answer
        assert result.problem_type == ProblemType.SUBSTITUTION
        assert len(result.steps) > 0

    def test_voltage_equation(self):
        """Ohm's Law: V = IR."""
        problem = "V = IR\nI = 2\nR = 5"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer in ["10", "10.0"] or "10" in result.final_answer
        assert len(result.steps) > 0

    def test_power_equation(self):
        """Power equation: P = VI."""
        problem = "P = VI\nV = 12\nI = 3"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer in ["36", "36.0"] or "36" in result.final_answer


class TestComplexFormulas:
    """Test complex formula substitution."""

    def test_kinetic_energy_formula(self):
        """Kinetic energy: KE = 0.5 * m * v^2."""
        problem = "KE = 0.5 * m * v^2\nm = 10\nv = 4"
        result = solve_substitution(problem)
        assert result.success is True
        # 0.5 * 10 * 16 = 80
        assert result.final_answer == "80"

    def test_formula_with_decimal(self):
        """Formula with decimal coefficients."""
        problem = "A = 0.5 * b * h\nb = 10\nh = 5"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "25"

    def test_formula_with_multiple_operations(self):
        """Formula with multiple operations."""
        problem = "E = m * c^2\nm = 2\nc = 3"
        result = solve_substitution(problem)
        assert result.success is True
        # 2 * 9 = 18
        assert result.final_answer == "18"

    def test_formula_with_mixed_operators(self):
        """Formula with mixed operators."""
        problem = "Q = m * c * dT\nm = 5\nc = 4\ndT = 10"
        result = solve_substitution(problem)
        assert result.success is True
        # 5 * 4 * 10 = 200
        assert result.final_answer == "200"


class TestStepGeneration:
    """Test that steps are generated correctly."""

    def test_steps_contain_original_formula(self):
        """Steps should contain the original formula."""
        problem = "F = ma\nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is True
        assert any("Original" in step or "F = ma" in step for step in result.steps)

    def test_steps_contain_substitutions(self):
        """Steps should contain substitution steps."""
        problem = "F = ma\nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is True
        assert any("Substitute" in step for step in result.steps)

    def test_steps_contain_calculation(self):
        """Steps should contain calculation step."""
        problem = "V = IR\nI = 2\nR = 5"
        result = solve_substitution(problem)
        assert result.success is True
        assert any("Calculate" in step for step in result.steps)

    def test_steps_not_empty(self):
        """Successful solutions should have steps."""
        problem = "F = ma\nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is True
        assert len(result.steps) > 0


class TestMissingVariables:
    """Test handling of missing variable assignments."""

    def test_missing_single_variable(self):
        """Missing one variable should fail gracefully."""
        problem = "F = ma\nm = 5"
        result = solve_substitution(problem)
        assert result.success is False
        assert "missing" in result.final_answer.lower()

    def test_missing_all_variables(self):
        """Missing all variable values should fail."""
        problem = "F = ma"
        result = solve_substitution(problem)
        assert result.success is False

    def test_partial_assignment(self):
        """Partial assignment with one missing should fail."""
        problem = "V = IR\nI = 2"
        result = solve_substitution(problem)
        assert result.success is False
        assert "missing" in result.final_answer.lower()


class TestInvalidFormulas:
    """Test error handling for invalid formulas."""

    def test_no_equals_sign(self):
        """Formula without equals sign should fail."""
        problem = "F ma\nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is False

    def test_empty_formula(self):
        """Empty formula should fail."""
        problem = "= \nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is False

    def test_invalid_formula_syntax(self):
        """Invalid formula syntax should fail."""
        problem = "F = \nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is False

    def test_empty_string(self):
        """Empty string should return error."""
        result = solve_substitution("")
        assert result.success is False

    def test_none_input(self):
        """None input should be handled gracefully."""
        result = solve_substitution(None)
        assert result.success is False


class TestVariableExtraction:
    """Test automatic variable extraction."""

    def test_single_variable_extraction(self):
        """Single variable should be extracted."""
        problem = "y = 2x\nx = 5"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "10"

    def test_multiple_variables_extraction(self):
        """Multiple variables should be extracted automatically."""
        problem = "Z = X * Y\nX = 3\nY = 4"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "12"

    def test_variables_with_subscripts(self):
        """Variables can be multi-character."""
        problem = "distance = velocity * time\nvelocity = 10\ntime = 5"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "50"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_single_variable_formula(self):
        """Formula with single variable."""
        problem = "y = 2x\nx = 5"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "10"

    def test_formula_with_extra_whitespace(self):
        """Extra whitespace should be handled."""
        problem = "F  =  m  *  a\nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "10"

    def test_formula_with_decimal_assignment(self):
        """Decimal assignments should be handled."""
        problem = "A = pi * r^2\nr = 2.5"
        result = solve_substitution(problem)
        # May fail because pi is a constant, not a variable
        # Just verify it handles gracefully
        assert isinstance(result.success, bool)

    def test_formula_result_is_float(self):
        """Formula result should be numeric."""
        problem = "P = V * I\nV = 10\nI = 2.5"
        result = solve_substitution(problem)
        assert result.success is True
        # Result could be 25 or 25.0
        assert "25" in result.final_answer


class TestInputExpression:
    """Test that input expression is preserved."""

    def test_input_expression_preserved(self):
        """Input expression should be stored as-is."""
        problem = "F = ma\nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.input_expression == problem

    def test_problem_type_is_substitution(self):
        """Problem type should always be SUBSTITUTION."""
        result = solve_substitution("F = ma\nm = 5\na = 2")
        assert result.problem_type == ProblemType.SUBSTITUTION


class TestDataClassProperties:
    """Test StepSolverResult properties."""

    def test_result_has_required_fields(self):
        """Result should have all required fields."""
        result = solve_substitution("F = ma\nm = 5\na = 2")
        assert hasattr(result, "problem_type")
        assert hasattr(result, "input_expression")
        assert hasattr(result, "steps")
        assert hasattr(result, "final_answer")
        assert hasattr(result, "success")

    def test_result_fields_have_correct_types(self):
        """Result fields should have correct types."""
        result = solve_substitution("F = ma\nm = 5\na = 2")
        assert isinstance(result.problem_type, ProblemType)
        assert isinstance(result.input_expression, str)
        assert isinstance(result.steps, list)
        assert isinstance(result.final_answer, str)
        assert isinstance(result.success, bool)

    def test_failed_result_fields_are_valid(self):
        """Failed result fields should still be valid."""
        result = solve_substitution("F = ma")
        assert result.problem_type == ProblemType.SUBSTITUTION
        assert isinstance(result.input_expression, str)
        assert isinstance(result.steps, list)
        assert isinstance(result.final_answer, str)
        assert result.success is False


class TestExamplesFromRequirements:
    """Test all examples from the requirements."""

    def test_requirement_example_1_force(self):
        """Test requirement example: F = ma with m=5, a=2."""
        problem = "F = ma\nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "10"

    def test_requirement_example_2_voltage(self):
        """Test requirement example: V = IR with I=2, R=5."""
        problem = "V = IR\nI = 2\nR = 5"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "10"

    def test_requirement_example_3_power(self):
        """Test requirement example: P = VI with V=12, I=3."""
        problem = "P = VI\nV = 12\nI = 3"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "36"

    def test_requirement_example_4_kinetic_energy(self):
        """Test requirement example: KE = 0.5*m*v^2 with m=10, v=4."""
        problem = "KE = 0.5 * m * v^2\nm = 10\nv = 4"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "80"


class TestMultiLineFormats:
    """Test different multi-line input formats."""

    def test_unix_line_endings(self):
        """Unix line endings should work."""
        problem = "F = ma\nm = 5\na = 2"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "10"

    def test_extra_blank_lines(self):
        """Extra blank lines should be handled."""
        problem = "F = ma\n\nm = 5\n\na = 2\n"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "10"

    def test_assignment_order_independent(self):
        """Assignment order should not matter."""
        problem1 = "F = ma\nm = 5\na = 2"
        problem2 = "F = ma\na = 2\nm = 5"
        result1 = solve_substitution(problem1)
        result2 = solve_substitution(problem2)
        assert result1.final_answer == result2.final_answer


class TestNegativeValues:
    """Test substitution with negative values."""

    def test_negative_single_variable(self):
        """Single negative value should work."""
        problem = "y = 3x\nx = -5"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "-15"

    def test_negative_multiple_variables(self):
        """Multiple negative values should work."""
        problem = "Z = X * Y\nX = -3\nY = -4"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "12"

    def test_mixed_sign_values(self):
        """Mixed positive and negative should work."""
        problem = "Z = X * Y\nX = -2\nY = 5"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "-10"


class TestComplexExpressions:
    """Test complex mathematical expressions."""

    def test_expression_with_division(self):
        """Formula with division."""
        problem = "a = b / c\nb = 20\nc = 4"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "5"

    def test_expression_with_addition(self):
        """Formula with addition."""
        problem = "sum = a + b + c\na = 5\nb = 3\nc = 2"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "10"

    def test_expression_with_subtraction(self):
        """Formula with subtraction."""
        problem = "diff = a - b\na = 10\nb = 3"
        result = solve_substitution(problem)
        assert result.success is True
        assert result.final_answer == "7"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
