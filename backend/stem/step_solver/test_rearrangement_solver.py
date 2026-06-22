"""Tests for the Formula Rearrangement Solver."""

import pytest
from .rearrangement_solver import solve_rearrangement
from .models import ProblemType


class TestRearrangementSolver:
    def test_force_rearrangement_find_m(self):
        problem = "F = ma\nFind m\nF = 20\na = 5"
        result = solve_rearrangement(problem)

        assert result.success is True
        assert result.problem_type == ProblemType.REARRANGEMENT
        assert result.final_answer == "m = 4"
        assert any("Find m" in step or "Step" in step for step in result.steps)

    def test_ohms_law_find_R(self):
        problem = "V = IR\nSolve for R\nV = 12\nI = 2"
        result = solve_rearrangement(problem)

        assert result.success is True
        assert result.final_answer == "R = 6"
        assert any("R =" in step for step in result.steps)

    def test_power_equation_find_I(self):
        problem = "P = VI\nFind I\nP = 36\nV = 12"
        result = solve_rearrangement(problem)

        assert result.success is True
        assert result.final_answer == "I = 3"

    def test_kinetic_energy_find_v(self):
        problem = "KE = 0.5 * m * v^2\nFind v\nKE = 80\nm = 10"
        result = solve_rearrangement(problem)

        assert result.success is True
        assert result.final_answer in ["v = 4", "v = -4"]
        assert any("v =" in step for step in result.steps)

    def test_missing_variable_assignments(self):
        problem = "F = ma\nFind m\nF = 20"
        result = solve_rearrangement(problem)

        assert result.success is False
        assert "missing" in result.final_answer.lower()

    def test_invalid_formula_returns_error(self):
        problem = "F ma\nFind F\nm = 5\na = 2"
        result = solve_rearrangement(problem)

        assert result.success is False
        assert "invalid" in result.final_answer.lower() or "unable" in result.final_answer.lower() or "formula not found" in result.final_answer.lower()
