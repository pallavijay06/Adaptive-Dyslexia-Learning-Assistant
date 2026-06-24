"""Test both old and new regex patterns on the detector test text."""

import re

text = "Area = length * width. Use sqrt(16) / 2 and x^2."

# Original pattern
OLD_PATTERN = re.compile(
    r"(?m)^\s*(?:[-*]\s*)?"
    r"([A-Za-z0-9_\u0370-\u03ff\u221a\u00d7\u22c5][A-Za-z0-9_\u0370-\u03ff \t().,\u221a\u00d7\u22c5+\-*/^=]{0,120}"
    r"(?:=|\+|-|\*|/|\^|\u221a|\u00d7|\u22c5)"
    r"[A-Za-z0-9_\u0370-\u03ff \t().,\u221a\u00d7\u22c5+\-*/^=]{0,120})\s*$"
)

# New pattern (with Unicode operators and colon support)
NEW_PATTERN = re.compile(
    r"(?m)(?:^|:\s*)(?:[-*]\s*)?"
    r"([A-Za-z0-9_\u0370-\u03ff\u221a\u00d7\u22c5\u00f7\u2212][A-Za-z0-9_\u0370-\u03ff \t().,\u221a\u00d7\u22c5\u00f7\u2212+\-*/^=]{0,120}"
    r"(?:=|\+|-|\*|/|\^|\u221a|\u00d7|\u22c5\u00f7|\u2212)"
    r"[A-Za-z0-9_\u0370-\u03ff \t().,\u221a\u00d7\u22c5\u00f7\u2212+\-*/^=]{0,120})\s*$"
)

print("=" * 80)
print(f"Test text: {text}")
print("=" * 80)

old_matches = OLD_PATTERN.findall(text)
new_matches = NEW_PATTERN.findall(text)

print(f"\nOld pattern matches: {len(old_matches)}")
for m in old_matches:
    print(f"  - {m}")

print(f"\nNew pattern matches: {len(new_matches)}")
for m in new_matches:
    print(f"  - {m}")

print("\n" + "=" * 80)
print("CONCLUSION:")
if len(old_matches) == 0 and len(new_matches) == 0:
    print("✓ Both patterns return 0 matches - test was already failing")
elif len(old_matches) == 0 and len(new_matches) > 0:
    print("✗ New pattern is breaking the detector by extracting new formulas")
elif len(old_matches) > 0 and len(new_matches) == 0:
    print("✗ New pattern broke something - old pattern worked")
else:
    print(f"? Both patterns return matches: old={len(old_matches)}, new={len(new_matches)}")
print("=" * 80)
