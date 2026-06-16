# test_simplify.py

from services.simplification_service import simplify_text

text = """
Photosynthesis is the biochemical process by which plants use sunlight,
water and carbon dioxide to produce glucose and oxygen.
"""

print(simplify_text(text))