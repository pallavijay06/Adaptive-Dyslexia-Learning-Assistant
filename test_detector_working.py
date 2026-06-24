"""Test the detector with properly formatted formulas."""

from backend.stem.detector import detect_formulas

# Original test text (all on one line, with sentence structure)
text1 = "Area = length * width. Use sqrt(16) / 2 and x^2."
result1 = detect_formulas(text1)

print("=" * 80)
print("Detector Test")
print("=" * 80)

print(f"\nTest 1 (single line with sentence):")
print(f"  Text: {text1}")
print(f"  Detected: {result1} formulas")
print(f"  Expected: 5 formulas")
print(f"  Status: {'✓ PASS' if result1 == 5 else '✗ FAIL'}")

# Modified text (each formula on its own line)
text2 = """Area = length * width
sqrt(16) / 2
x^2
V = I * R
F = ma"""

result2 = detect_formulas(text2)

print(f"\nTest 2 (formulas on separate lines):")
print(f"  Text: (multiline)")
for line in text2.split('\n'):
    print(f"    {line}")
print(f"  Detected: {result2} formulas")

# Another version with colons
text3 = """Formula: Area = length * width
Equation: sqrt(16) / 2 = 4
Power: x^2"""

result3 = detect_formulas(text3)

print(f"\nTest 3 (formulas with labels):")
print(f"  Text: (multiline)")
for line in text3.split('\n'):
    print(f"    {line}")
print(f"  Detected: {result3} formulas")

print("\n" + "=" * 80)
