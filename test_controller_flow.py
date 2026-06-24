"""Test the complete formula detection flow through the STEM controller."""

from backend.stem.stem_controller import process_stem_support

# Test with Ohm's Law content
text = """Ohm's Law
Ohm's Law is one of the fundamental principles of electrical engineering and physics.
Formula: V = I × R
Where V = Voltage (Volts), I = Current (Amperes), and R = Resistance (Ohms)."""

print("=" * 80)
print("TEST: Complete STEM Controller Formula Flow")
print("=" * 80)
print(f"\nInput text:\n{text}")
print("\n" + "=" * 80)

result = process_stem_support(text)

print(f"\nController result keys: {result.keys()}")
print(f"\nFormulas extracted: {result['formulas']}")
print(f"Number of formulas: {len(result['formulas'])}")
print(f"\nSymbols extracted: {result['symbols']}")
print(f"Features available: {result['features']}")
print("\n" + "=" * 80)

# Verify formula is in the result
if "V = I × R" in result['formulas']:
    print("✓ PASS: Formula 'V = I × R' successfully extracted and returned")
else:
    print("✗ FAIL: Formula not found in results")
    print(f"   Got: {result['formulas']}")

# Test with multiple formulas
print("\n" + "=" * 80)
print("TEST: Multiple Formulas")
print("=" * 80)

text2 = """Physics Concepts
Force equation: F = ma
Voltage: V = I × R
Energy equation: E = mc²
Division: a ÷ b = c
Subtraction: x − y = z"""

result2 = process_stem_support(text2)
print(f"\nFormulas detected: {result2['formulas']}")
print(f"\nExpected formulas found:")
for expected_formula in ["F = ma", "V = I × R", "E = mc²", "a ÷ b = c", "x − y = z"]:
    if expected_formula in result2['formulas']:
        print(f"  ✓ {expected_formula}")
    else:
        print(f"  ✗ {expected_formula} NOT FOUND")
