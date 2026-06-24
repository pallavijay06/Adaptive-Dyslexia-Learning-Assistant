"""Investigation script to trace formula detection issues."""

from backend.stem.formula_extractor import extract_formulas

# Test case 1: Formula on its own line
text1 = """V = I × R
This is Ohm's Law."""

print("=" * 80)
print("Test 1: Formula on its own line")
print(f"Input text:\n{repr(text1)}")
result1 = extract_formulas(text1)
print(f"Extracted formulas: {result1}")
print()

# Test case 2: Formula with prefix (like in actual PDF)
text2 = """Formula: V = I × R
This is Ohm's Law."""

print("=" * 80)
print("Test 2: Formula with 'Formula:' prefix (like in PDF)")
print(f"Input text:\n{repr(text2)}")
result2 = extract_formulas(text2)
print(f"Extracted formulas: {result2}")
print()

# Test case 3: Full Ohm's Law text
text3 = """Ohm's Law
Ohm's Law is one of the fundamental principles of electrical engineering and physics. It describes
the relationship between voltage, current, and resistance in an electrical circuit. The law states that
the electric current flowing through a conductor is directly proportional to the voltage applied across
it and inversely proportional to the resistance offered by the conductor, provided that temperature
and other physical conditions remain constant.
Formula: V = I × R
Where V = Voltage (Volts), I = Current (Amperes), and R = Resistance (Ohms).
The experimental setup shown above is commonly used to verify Ohm's Law. A resistor is
connected in series with a power supply, key, and ammeter, while a voltmeter is connected in
parallel across the resistor. The ammeter measures the current flowing through the circuit, whereas
the voltmeter measures the potential difference across the resistor. By varying the applied voltage
and recording the corresponding current values, it can be observed that the ratio of voltage to
current remains constant. This constant ratio is the resistance of the conductor."""

print("=" * 80)
print("Test 3: Full Ohm's Law text from PDF")
print(f"Input text length: {len(text3)} characters")
result3 = extract_formulas(text3)
print(f"Extracted formulas: {result3}")
print()

# Test case 4: Unicode minus and division
text4 = """a − b
x ÷ y"""

print("=" * 80)
print("Test 4: Unicode minus (−) and division (÷)")
print(f"Input text:\n{repr(text4)}")
result4 = extract_formulas(text4)
print(f"Extracted formulas: {result4}")
print()

# Test case 5: Mixed operators
text5 = """V = I × R
a = b - c
x ÷ y = z"""

print("=" * 80)
print("Test 5: Mixed operators")
print(f"Input text:\n{repr(text5)}")
result5 = extract_formulas(text5)
print(f"Extracted formulas: {result5}")
print()

# Test case 6: Verify Unicode character codes
print("=" * 80)
print("Unicode character verification:")
print(f"× (multiplication): U+00D7 = \\u00d7 = {repr('×')}")
print(f"÷ (division): U+00F7 = \\u00f7 = {repr('÷')}")
print(f"− (minus): U+2212 = \\u2212 = {repr('−')}")
print()
