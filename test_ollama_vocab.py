# test_ollama_vocab.py

from services.ollama_service import generate_answer

response = generate_answer(
    question="Extract 5 difficult words and meanings. Return ONLY JSON.",
    context="Photosynthesis occurs in chloroplasts. Mitochondria produce energy."
)

print(response)