"""Tests for algebra solver."""

import pytest
from .algebra_solver import solve_algebra
from .models import ProblemType


class TestAlgebraSolver:
    def test_linear_equation_simple(self):
        problem = "x + 5 = 12"
        result = solve_algebra(problem)

        assert result.success is True
        assert result.problem_type == ProblemType.ALGEBRA
        assert result.input_expression == problem
        assert result.final_answer == "x = 7"
        assert any("x + 5 = 12" in step for step in result.steps)
        assert any("Step 2" in step for step in result.steps)

    def test_linear_equation_with_coefficient(self):
        problem = "2x - 4 = 10"
        result = solve_algebra(problem)

        assert result.success is True
        assert result.final_answer == "x = 7"
        assert any("2*x = 14" in step or "2x = 14" in step for step in result.steps)

    def test_linear_equation_scaled(self):
        problem = "5x = 25"
        result = solve_algebra(problem)

        assert result.success is True
        assert result.final_answer == "x = 5"

    def test_quadratic_equation_two_roots(self):
        problem = "x^2 + 3x + 2 = 0"
        result = solve_algebra(problem)

        assert result.success is True
        assert result.final_answer == "x = -2, -1"
        assert any("x = -2" in step for step in result.steps)
        assert any("x = -1" in step for step in result.steps)

    def test_quadratic_equation_two_roots_ordered(self):
        problem = "x^2 - 5x + 6 = 0"
        result = solve_algebra(problem)

        assert result.success is True
        assert result.final_answer == "x = 2, 3"
        assert any("x = 2" in step for step in result.steps)
        assert any("x = 3" in step for step in result.steps)

    def test_invalid_equation_returns_error(self):
        problem = "x +"
        result = solve_algebra(problem)

        assert result.success is False
        assert "=" in result.final_answer or "Invalid" in result.final_answer
