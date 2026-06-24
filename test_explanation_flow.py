"""Test formula explanation with the detected formulas."""

from backend.stem.stem_controller import process_stem_support
from backend.stem.formula_assistant import explain_formula

# Test with Ohm's Law content
text = """Ohm's Law
Formula: V = I × R
Where V = Voltage, I = Current, and R = Resistance."""

print("=" * 80)
print("TEST: Formula Explanation Flow")
print("=" * 80)

result = process_stem_support(text)
formulas = result['formulas']

print(f"\nDetected formulas: {formulas}")

for formula in formulas:
    print(f"\n{'-' * 80}")
    print(f"Formula: {formula}")
    print(f"{'-' * 80}")
    
    try:
        explanation = explain_formula(formula)
        print(f"✓ Explanation generated:")
        print(f"  Meaning: {explanation.get('meaning', 'N/A')}")
        print(f"  Terms: {explanation.get('terms', {})}")
        print(f"  Example: {explanation.get('example', 'N/A')}")
    except Exception as e:
        print(f"✗ Error explaining formula: {e}")

print("\n" + "=" * 80)
print("Flow test complete!")
print("=" * 80)
