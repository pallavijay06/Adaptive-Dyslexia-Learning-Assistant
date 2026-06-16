from services.vocabulary_service import generate_vocabulary

sample_text = """
Photosynthesis occurs in chloroplasts.
Mitochondria are responsible for energy production.
"""

result = generate_vocabulary(sample_text)

print(result)