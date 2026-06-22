"""Tests for the Arithmetic Solver.

Tests cover:
- Order of operations
- Parentheses
- Exponents
- Basic operations
- Edge cases
- Error handling
"""

import pytest
from .arithmetic_solver import solve_arithmetic
from .models import ProblemType


class TestBasicArithmetic:
    """Test basic arithmetic operations."""

    def test_simple_addition(self):
        """Simple addition should be solved correctly."""
        result = solve_arithmetic("10 + 5")
        assert result.success is True
        assert result.final_answer == "15"
        assert result.problem_type == ProblemType.ARITHMETIC
        assert len(result.steps) > 0

    def test_simple_subtraction(self):
        """Simple subtraction should be solved correctly."""
        result = solve_arithmetic("100 - 25")
        assert result.success is True
        assert result.final_answer == "75"
        assert len(result.steps) > 0

    def test_simple_multiplication(self):
        """Simple multiplication should be solved correctly."""
        result = solve_arithmetic("5 * 4")
        assert result.success is True
        assert result.final_answer == "20"
        assert len(result.steps) > 0

    def test_simple_division(self):
        """Simple division should be solved correctly."""
        result = solve_arithmetic("20 / 4")
        assert result.success is True
        # Could be "5" or "5.0" depending on SymPy
        assert result.final_answer in ["5", "5.0"]
        assert len(result.steps) > 0


class TestOrderOfOperations:
    """Test that order of operations (PEMDAS) is respected."""

    def test_multiplication_before_addition(self):
        """Multiplication should be performed before addition."""
        result = solve_arithmetic("10 + 5 * 2")
        assert result.success is True
        assert result.final_answer == "20"
        # Verify steps show multiplication first
        assert any("*" in step or "Multiply" in step or "multiply" in step
                   for step in result.steps)

    def test_division_before_addition(self):
        """Division should be performed before addition."""
        result = solve_arithmetic("10 + 20 / 4")
        assert result.success is True
        assert result.final_answer == "15"

    def test_multiplication_division_left_to_right(self):
        """Multiplication and division should be evaluated left to right."""
        result = solve_arithmetic("20 / 4 * 2")
        assert result.success is True
        assert result.final_answer == "10"

    def test_addition_subtraction_left_to_right(self):
        """Addition and subtraction should be evaluated left to right."""
        result = solve_arithmetic("10 - 5 + 3")
        assert result.success is True
        assert result.final_answer == "8"


class TestParentheses:
    """Test expressions with parentheses."""

    def test_simple_parentheses(self):
        """Simple parentheses should be evaluated first."""
        result = solve_arithmetic("(8 + 2) * 3")
        assert result.success is True
        assert result.final_answer == "30"
        assert len(result.steps) > 0
        # Verify parentheses step is present
        assert any("parenthese" in step.lower() or "(8 + 2)" in step
                   for step in result.steps)

    def test_nested_parentheses(self):
        """Nested parentheses should be handled correctly."""
        result = solve_arithmetic("((5 + 3) * 2) + 1")
        assert result.success is True
        assert result.final_answer == "17"

    def test_multiple_parentheses_groups(self):
        """Multiple parentheses groups should be evaluated."""
        result = solve_arithmetic("(10 + 5) * (2 + 3)")
        assert result.success is True
        assert result.final_answer == "75"


class TestExponents:
    """Test expressions with exponents."""

    def test_simple_exponent(self):
        """Simple exponents should be calculated correctly."""
        result = solve_arithmetic("3^2")
        assert result.success is True
        assert result.final_answer == "9"
        assert any("exponent" in step.lower() or "3^2" in step or "3**2" in step
                   for step in result.steps)

    def test_multiple_exponents(self):
        """Multiple exponents should be calculated correctly."""
        result = solve_arithmetic("3^2 + 4^2")
        assert result.success is True
        assert result.final_answer == "25"
        assert len(result.steps) > 0

    def test_exponent_in_expression(self):
        """Exponents in complex expressions should follow order of operations."""
        result = solve_arithmetic("2 * 3^2")
        assert result.success is True
        assert result.final_answer == "18"


class TestComplexExpressions:
    """Test complex expressions combining multiple operations."""

    def test_complex_expression_1(self):
        """Complex expression: 5 + 3 * 2 - 1."""
        result = solve_arithmetic("5 + 3 * 2 - 1")
        assert result.success is True
        assert result.final_answer == "10"

    def test_complex_expression_2(self):
        """Complex expression: (10 - 5) * (2 + 3)."""
        result = solve_arithmetic("(10 - 5) * (2 + 3)")
        assert result.success is True
        assert result.final_answer == "25"

    def test_complex_expression_3(self):
        """Complex expression: 100 / (2 + 3) + 10."""
        result = solve_arithmetic("100 / (2 + 3) + 10")
        assert result.success is True
        assert result.final_answer == "30"

    def test_complex_expression_with_exponents(self):
        """Complex expression with exponents and parentheses."""
        result = solve_arithmetic("(2 + 3)^2")
        assert result.success is True
        assert result.final_answer == "25"


class TestDecimalResults:
    """Test expressions that produce decimal results."""

    def test_division_with_decimal(self):
        """Division that produces decimals should be handled."""
        result = solve_arithmetic("10 / 4")
        assert result.success is True
        # Could be "2.5" or "5/2" depending on SymPy
        assert result.final_answer in ["2.5", "5/2"]

    def test_decimal_operands(self):
        """Decimal operands should be handled correctly."""
        result = solve_arithmetic("2.5 + 1.5")
        assert result.success is True
        # SymPy may return with different decimal precision
        assert "4" in result.final_answer


class TestErrorHandling:
    """Test error handling for invalid expressions."""

    def test_empty_string(self):
        """Empty string should return error."""
        result = solve_arithmetic("")
        assert result.success is False
        assert result.final_answer is not None

    def test_invalid_characters(self):
        """Invalid operators or syntax should be handled gracefully."""
        result = solve_arithmetic("10 @ 5")
        assert result.success is False

    def test_unbalanced_parentheses(self):
        """Unbalanced parentheses should return error."""
        result = solve_arithmetic("(10 + 5")
        assert result.success is False

    def test_invalid_operators(self):
        """Invalid operators should return error."""
        result = solve_arithmetic("10 + * 5")
        assert result.success is False

    def test_empty_parentheses(self):
        """Empty parentheses should return error."""
        result = solve_arithmetic("10 + () * 2")
        assert result.success is False

    def test_none_input(self):
        """None input should be handled gracefully."""
        result = solve_arithmetic(None)
        assert result.success is False

    def test_division_by_zero(self):
        """Division by zero should be handled."""
        result = solve_arithmetic("10 / 0")
        # SymPy may raise an error or return inf
        # Just verify it doesn't crash
        assert isinstance(result.success, bool)


class TestStepGeneration:
    """Test that steps are generated correctly."""

    def test_steps_contain_original_expression(self):
        """Steps should contain the original expression."""
        result = solve_arithmetic("10 + 5 * 2")
        assert result.success is True
        assert any("Original" in step or "10 + 5 * 2" in step
                   for step in result.steps)

    def test_steps_are_not_empty(self):
        """Successful solutions should have steps."""
        result = solve_arithmetic("10 + 5")
        assert result.success is True
        assert len(result.steps) > 0

    def test_steps_contain_final_answer(self):
        """Steps should lead to the final answer."""
        result = solve_arithmetic("10 + 5")
        assert result.success is True
        assert result.final_answer == "15"

    def test_multiple_steps_for_complex_expression(self):
        """Complex expressions should have multiple steps."""
        result = solve_arithmetic("(8 + 2) * 3 + 5")
        assert result.success is True
        assert len(result.steps) >= 2


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_single_number(self):
        """Single number should return itself."""
        result = solve_arithmetic("42")
        assert result.success is True
        assert result.final_answer == "42"

    def test_spaces_in_expression(self):
        """Extra spaces should be handled."""
        result = solve_arithmetic("10  +  5  *  2")
        assert result.success is True
        assert result.final_answer == "20"

    def test_negative_numbers(self):
        """Negative numbers should be handled."""
        result = solve_arithmetic("-5 + 10")
        assert result.success is True
        assert result.final_answer == "5"

    def test_consecutive_operators(self):
        """Consecutive operators (like + -) should be handled or error."""
        result = solve_arithmetic("10 + - 5")
        # Could parse as "10 + (-5)" = 5 or error
        # Just verify it handles gracefully
        assert isinstance(result.success, bool)

    def test_result_type_is_string(self):
        """Final answer should always be a string."""
        result = solve_arithmetic("10 + 5")
        assert isinstance(result.final_answer, str)


class TestInputExpression:
    """Test that input expression is preserved."""

    def test_input_expression_preserved(self):
        """Input expression should be stored as-is."""
        problem = "10 + 5 * 2"
        result = solve_arithmetic(problem)
        assert result.input_expression == problem

    def test_problem_type_is_arithmetic(self):
        """Problem type should always be ARITHMETIC."""
        result = solve_arithmetic("10 + 5")
        assert result.problem_type == ProblemType.ARITHMETIC


class TestDataClassProperties:
    """Test StepSolverResult properties."""

    def test_result_has_required_fields(self):
        """Result should have all required fields."""
        result = solve_arithmetic("10 + 5")
        assert hasattr(result, "problem_type")
        assert hasattr(result, "input_expression")
        assert hasattr(result, "steps")
        assert hasattr(result, "final_answer")
        assert hasattr(result, "success")

    def test_result_fields_have_correct_types(self):
        """Result fields should have correct types."""
        result = solve_arithmetic("10 + 5")
        assert isinstance(result.problem_type, ProblemType)
        assert isinstance(result.input_expression, str)
        assert isinstance(result.steps, list)
        assert isinstance(result.final_answer, str)
        assert isinstance(result.success, bool)

    def test_failed_result_fields_are_valid(self):
        """Failed result fields should still be valid."""
        result = solve_arithmetic("10 @ 5")
        assert result.problem_type == ProblemType.ARITHMETIC
        assert isinstance(result.input_expression, str)
        assert isinstance(result.steps, list)
        assert isinstance(result.final_answer, str)
        assert result.success is False


class TestExamplesFromRequirements:
    """Test all examples from the requirements."""

    def test_requirement_example_1(self):
        """Test requirement example: 10 + 5 * 2 = 20."""
        result = solve_arithmetic("10 + 5 * 2")
        assert result.success is True
        assert result.final_answer == "20"

    def test_requirement_example_2(self):
        """Test requirement example: (8 + 2) * 3 = 30."""
        result = solve_arithmetic("(8 + 2) * 3")
        assert result.success is True
        assert result.final_answer == "30"

    def test_requirement_example_3(self):
        """Test requirement example: 3^2 + 4^2 = 25."""
        result = solve_arithmetic("3^2 + 4^2")
        assert result.success is True
        assert result.final_answer == "25"

    def test_requirement_example_4(self):
        """Test requirement example: 100 - 25 = 75."""
        result = solve_arithmetic("100 - 25")
        assert result.success is True
        assert result.final_answer == "75"

    def test_requirement_example_5(self):
        """Test requirement example: 20 / 4 = 5."""
        result = solve_arithmetic("20 / 4")
        assert result.success is True
        assert result.final_answer in ["5", "5.0"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
