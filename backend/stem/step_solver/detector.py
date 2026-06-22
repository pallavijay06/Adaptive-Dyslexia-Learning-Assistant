"""Problem type detector for Step Solver.

Detects problem types using rule-based pattern matching:
- REARRANGEMENT: Formula + Find/Solve for keywords
- SUBSTITUTION: Formula + variable assignments (no Find/Solve)
- ALGEBRA: Equations with unknown variables
- ARITHMETIC: Numeric expressions only
- UNKNOWN: Everything else
"""

import re
from .models import ProblemType


def _has_formula(text: str) -> bool:
    """
    Detect if text contains a formula (equation with assignment).

    Formulas match patterns like:
    - F = ma
    - V = IR
    - P = VI
    - E = mc²

    Args:
        text: The text to analyze

    Returns:
        True if a formula is detected, False otherwise
    """
    # Pattern: variable/expression = expression
    # Matches: single letter or multi-letter variables with optional operators
    pattern = r'\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Za-z0-9\s\+\-\*/\(\)^²³]+'
    return bool(re.search(pattern, text))


def _has_find_or_solve_keywords(text: str) -> bool:
    """
    Detect Find/Solve keywords that indicate rearrangement problems.

    Keywords:
    - Find [variable]
    - Solve for [variable]

    Args:
        text: The text to analyze

    Returns:
        True if rearrangement keywords are detected, False otherwise
    """
    # Match "Find x", "Find m", "Solve for x", etc.
    pattern = r'\b(Find|Solve\s+for)\s+[A-Za-z_]\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _has_variable_assignments(text: str) -> bool:
    """
    Detect variable-value assignments in the text.

    Assignments match patterns like:
    - m = 5
    - a = 2
    - I = 2.5
    - V = 12

    Args:
        text: The text to analyze

    Returns:
        True if variable assignments are detected, False otherwise
    """
    # Pattern: variable = number
    # This should NOT match formula definitions (lowercase single letters)
    lines = text.split('\n')
    assignment_count = 0

    for line in lines:
        line = line.strip()
        # Skip empty lines and formula definitions (they contain variables/operators on right side)
        if not line:
            continue

        # Match: single or multi-letter variable = number (with optional decimals/negatives)
        # This is a simpler assignment, not a formula
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*=\s*-?\d+\.?\d*$', line):
            assignment_count += 1

    return assignment_count >= 1


def _is_rearrangement(text: str) -> bool:
    """
    Detect rearrangement problems.

    Rearrangement problems:
    1. Contain a formula (e.g., F = ma)
    2. Contain Find/Solve for keywords (e.g., "Find m", "Solve for R")
    3. May contain variable assignments (e.g., m = 5)

    Examples:
    - F = ma
      Find m
      F = 20
      a = 5

    - V = IR
      Solve for R
      V = 12
      I = 2

    Args:
        text: The text to analyze

    Returns:
        True if text is a rearrangement problem, False otherwise
    """
    has_formula = _has_formula(text)
    has_keywords = _has_find_or_solve_keywords(text)

    return has_formula and has_keywords


def _is_substitution(text: str) -> bool:
    """
    Detect substitution problems.

    Substitution problems:
    1. Contain a formula (e.g., F = ma)
    2. Contain variable assignments (e.g., m = 5, a = 2)
    3. Do NOT contain Find/Solve keywords

    Examples:
    - F = ma
      m = 5
      a = 2

    - V = IR
      I = 2
      R = 5

    Args:
        text: The text to analyze

    Returns:
        True if text is a substitution problem, False otherwise
    """
    has_formula = _has_formula(text)
    has_assignments = _has_variable_assignments(text)
    has_keywords = _has_find_or_solve_keywords(text)

    # Must have formula and assignments, but NOT Find/Solve keywords
    return has_formula and has_assignments and not has_keywords


def _is_algebra(text: str) -> bool:
    """
    Detect algebra problems.

    Algebra problems:
    1. Contain equations with unknown variables (x, y, z, etc.)
    2. Support linear and quadratic equations
    3. Must NOT be classified as substitution or rearrangement

    Examples:
    - x + 5 = 12
    - 2x - 4 = 10
    - x² + 3x + 2 = 0
    - 3x + 7 = 22

    Args:
        text: The text to analyze

    Returns:
        True if text is an algebra problem, False otherwise
    """
    # Must NOT be substitution or rearrangement
    if _is_substitution(text) or _is_rearrangement(text):
        return False

    # Pattern: equation containing algebraic variables
    # Look for: variable (x, y, z) with potential coefficients/operators
    algebra_pattern = r'[0-9]*\s*[xyz]\b|[xyz]\s*[+\-*/^²³]|\^[0-9]'

    # Must have an equals sign (equation)
    has_equation = '=' in text

    # Must have algebraic variables
    has_algebra_vars = bool(re.search(algebra_pattern, text, re.IGNORECASE))

    return has_equation and has_algebra_vars


def _is_arithmetic(text: str) -> bool:
    """
    Detect arithmetic problems.

    Arithmetic problems:
    1. Only contain numbers and basic operators
    2. No variables (x, y, z, etc.)
    3. No formulas or assignments
    4. Operators allowed: +, -, *, /, ^, parentheses

    Examples:
    - 10 + 5 * 2
    - 20 / 4
    - (8 + 2) * 3
    - 3^2 + 4^2

    Args:
        text: The text to analyze

    Returns:
        True if text is an arithmetic problem, False otherwise
    """
    # Must NOT contain variables
    if re.search(r'[a-zA-Z]', text):
        return False

    # Must NOT contain assignment (=)
    if '=' in text:
        return False

    # Pattern: only numbers, operators, and parentheses
    # Valid characters: 0-9, +, -, *, /, ^, (, ), ., spaces
    arithmetic_pattern = r'^[\d\s\+\-*/()^.]+$'

    # Must have at least one operator or parentheses (otherwise just a number)
    has_operator = bool(re.search(r'[\+\-*/^()]', text))

    return bool(re.match(arithmetic_pattern, text)) and has_operator


def detect_problem_type(text: str) -> ProblemType:
    """
    Detect the type of problem from the input text.

    Detection order (first match wins):
    1. REARRANGEMENT: Formula + Find/Solve keywords
    2. SUBSTITUTION: Formula + variable assignments (no Find/Solve)
    3. ALGEBRA: Equations with variables
    4. ARITHMETIC: Numeric expressions only
    5. UNKNOWN: Everything else

    Args:
        text: The problem text to analyze

    Returns:
        ProblemType enum value identifying the problem category

    Examples:
        >>> detect_problem_type("F = ma\\nFind m\\nF = 20\\na = 5")
        ProblemType.REARRANGEMENT

        >>> detect_problem_type("F = ma\\nm = 5\\na = 2")
        ProblemType.SUBSTITUTION

        >>> detect_problem_type("x + 5 = 12")
        ProblemType.ALGEBRA

        >>> detect_problem_type("10 + 5 * 2")
        ProblemType.ARITHMETIC

        >>> detect_problem_type("Hello world")
        ProblemType.UNKNOWN
    """
    # Normalize text: strip whitespace and convert to lowercase for pattern matching
    text_normalized = text.strip()

    # Detection order is critical - stop at first match
    if _is_rearrangement(text_normalized):
        return ProblemType.REARRANGEMENT

    if _is_substitution(text_normalized):
        return ProblemType.SUBSTITUTION

    if _is_algebra(text_normalized):
        return ProblemType.ALGEBRA

    if _is_arithmetic(text_normalized):
        return ProblemType.ARITHMETIC

    # Default to unknown if no patterns match
    return ProblemType.UNKNOWN
