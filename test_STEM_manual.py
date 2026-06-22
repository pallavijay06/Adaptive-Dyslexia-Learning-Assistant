# test_stem_manual.py

from backend.stem.stem_service import analyze_document_for_stem
from backend.stem.stem_service import get_available_stem_features

sample_text = """
∑
Δ
π
"""

result = analyze_document_for_stem(sample_text)

print(result)

print(get_available_stem_features(result))