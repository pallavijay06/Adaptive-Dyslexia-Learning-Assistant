"""Debug the full extraction logic for the detector test."""

from backend.stem.formula_extractor import _clean_formula, _is_formula_candidate

text_fragment = "Area = length * width. Use sqrt(16) / 2 and x^2."

print("=" * 80)
print("Full Extraction Debug")
print("=" * 80)

print(f"\nRaw fragment: {repr(text_fragment)}")

cleaned = _clean_formula(text_fragment)
print(f"After clean_formula(): {repr(cleaned)}")

is_candidate = _is_formula_candidate(cleaned)
print(f"is_formula_candidate(): {is_candidate}")

print("\n" + "=" * 80)
print("Breakdown of _is_formula_candidate checks:")
print("=" * 80)

# Check each condition in _is_formula_candidate
import re
FORMULA_OPERATOR_PATTERN = re.compile(r"(=|\+|-|\*|/|\^|\u221a|\u00d7|\u22c5|\u00f7|\u2212)")

print(f"1. has_operator: {bool(FORMULA_OPERATOR_PATTERN.search(cleaned))}")
print(f"2. length <= 120: {len(cleaned) <= 120} (actual: {len(cleaned)})")
print(f"3. not_sentence (no [.!?]\\s+[A-Z]): {not bool(re.search(r'[.!?]\s+[A-Z]', cleaned))}")

tokens = cleaned.split()
print(f"4. tokens <= 12: {len(tokens) <= 12} (actual: {len(tokens)} tokens)")
print(f"   Tokens: {tokens}")
