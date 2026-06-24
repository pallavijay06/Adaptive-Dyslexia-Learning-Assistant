"""Final Comprehensive Test - Formula Detection Pipeline"""

from backend.stem.stem_controller import process_stem_support
from backend.stem.formula_extractor import extract_formulas
from backend.stem.formula_library import normalize_formula_key, get_formula_library_explanation
from backend.stem.formula_assistant import explain_formula

print("=" * 80)
print("FINAL COMPREHENSIVE TEST - Formula Detection Pipeline")
print("=" * 80)

# Test Data
test_cases = [
    # (description, text, expected_formulas)
    ("ASCII operators only", "F = ma\nV = IR", ["F = ma", "V = IR"]),
    ("Unicode multiplication", "V = I × R", ["V = I × R"]),
    ("Unicode division", "a ÷ b = c", ["a ÷ b = c"]),
    ("Unicode minus", "x − y = z", ["x − y = z"]),
    ("Formula with colon prefix", "Formula: V = I × R", ["V = I × R"]),
    ("Mixed operators", "V = I × R\na = b - c\nx ÷ y = z", ["V = I × R", "a = b - c", "x ÷ y = z"]),
]

print("\n1. EXTRACTION TESTS")
print("-" * 80)

all_pass = True
for desc, text, expected in test_cases:
    result = extract_formulas(text)
    passed = result == expected
    all_pass = all_pass and passed
    status = "✓" if passed else "✗"
    print(f"{status} {desc}")
    if not passed:
        print(f"    Expected: {expected}")
        print(f"    Got: {result}")

print("\n2. NORMALIZATION TESTS")
print("-" * 80)

norm_tests = [
    ("V = I × R", "v=ir"),
    ("V = I * R", "v=ir"),
    ("a − b", "a-b"),
    ("a - b", "a-b"),
    ("x ÷ y", "x/y"),
    ("x / y", "x/y"),
]

norm_pass = True
for formula, expected_key in norm_tests:
    result_key = normalize_formula_key(formula)
    passed = result_key == expected_key
    norm_pass = norm_pass and passed
    status = "✓" if passed else "✗"
    print(f"{status} '{formula}' → '{result_key}'")
    if not passed:
        print(f"    Expected: '{expected_key}'")

print("\n3. LIBRARY LOOKUP TESTS")
print("-" * 80)

library_tests = [
    ("V = I × R", "V = IR"),  # Should find library entry
    ("F = ma", "F = ma"),
    ("a ÷ b", None),  # Not in library
]

lib_pass = True
for formula, expected_display in library_tests:
    result = get_formula_library_explanation(formula)
    passed = (result is not None) == (expected_display is not None)
    lib_pass = lib_pass and passed
    status = "✓" if passed else "✗"
    has_lib = "FOUND" if result is not None else "NOT FOUND"
    print(f"{status} '{formula}' → {has_lib}")

print("\n4. EXPLANATION TESTS")
print("-" * 80)

explain_tests = ["V = I × R", "F = ma", "x − y = z"]

explain_pass = True
for formula in explain_tests:
    try:
        result = explain_formula(formula)
        has_meaning = bool(result.get('meaning'))
        has_example = bool(result.get('example'))
        passed = has_meaning and has_example
        explain_pass = explain_pass and passed
        status = "✓" if passed else "✗"
        print(f"{status} '{formula}' → meaning and example generated")
        if not passed:
            print(f"    Has meaning: {has_meaning}, Has example: {has_example}")
    except Exception as e:
        explain_pass = False
        print(f"✗ '{formula}' → Error: {e}")

print("\n5. CONTROLLER INTEGRATION TEST")
print("-" * 80)

controller_text = """Ohm's Law
Formula: V = I × R
Pythagorean theorem: a² + b² = c²"""

result = process_stem_support(controller_text)
controller_pass = (
    len(result['formulas']) > 0 and
    'formulas' in result and
    'symbols' in result and
    'features' in result
)
status = "✓" if controller_pass else "✗"
print(f"{status} Controller returns formulas: {result['formulas']}")

print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)

all_tests_pass = all_pass and norm_pass and lib_pass and explain_pass and controller_pass
print(f"\nExtraction Tests:  {'✓ PASS' if all_pass else '✗ FAIL'}")
print(f"Normalization Tests: {'✓ PASS' if norm_pass else '✗ FAIL'}")
print(f"Library Lookup Tests: {'✓ PASS' if lib_pass else '✗ FAIL'}")
print(f"Explanation Tests: {'✓ PASS' if explain_pass else '✗ FAIL'}")
print(f"Controller Integration: {'✓ PASS' if controller_pass else '✗ FAIL'}")

print(f"\n{'=' * 80}")
if all_tests_pass:
    print("✓ ALL TESTS PASSED - Formula Detection Pipeline is fixed!")
else:
    print("✗ SOME TESTS FAILED - Review the results above")
print("=" * 80)
