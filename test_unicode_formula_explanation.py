"""Test formula explanation with Unicode operators."""

from backend.stem.formula_assistant import explain_formula

formulas_to_test = [
    "V = I × R",
    "F = ma",
    "a ÷ b",
    "x − y",
]

print("=" * 80)
print("Formula Explanation Tests with Unicode Operators")
print("=" * 80)

for formula in formulas_to_test:
    result = explain_formula(formula)
    print(f"\nFormula: {formula}")
    print(f"  Meaning: {result.get('meaning', 'N/A')}")
    print(f"  Example: {result.get('example', 'N/A')}")

print("\n" + "=" * 80)
