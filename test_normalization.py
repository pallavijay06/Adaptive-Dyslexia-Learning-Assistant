"""Test formula normalization with various Unicode operators."""

from backend.stem.formula_library import normalize_formula_key

print("=" * 80)
print("Formula Normalization Tests")
print("=" * 80)

test_cases = [
    ("V = I × R", "v=ir"),  # Unicode multiplication
    ("V = I * R", "v=ir"),   # ASCII multiplication
    ("V=IR", "v=ir"),         # No spaces
    ("V = I R", "v=ir"),      # Space as implicit multiplication
    ("a − b", "a-b"),         # Unicode minus
    ("a - b", "a-b"),          # ASCII minus
    ("a ÷ b", "a/b"),         # Unicode division
    ("a / b", "a/b"),          # ASCII division
    ("a ⋅ b", "a*b"),         # Middle dot
    ("a · b", "a*b"),         # Regular dot
    ("F = ma", "f=ma"),       # Simple formula
    ("E = mc²", "e=mc²"),     # With superscript (won't be removed)
]

print("\nNormalization Results:")
for formula, expected in test_cases:
    result = normalize_formula_key(formula)
    status = "✓" if result == expected else "✗"
    print(f"{status} '{formula}' → '{result}' (expected: '{expected}')")

print("\n" + "=" * 80)
