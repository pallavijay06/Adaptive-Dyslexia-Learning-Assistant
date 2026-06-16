from services.ollama_service import generate_answer

result = generate_answer(
    question="What is photosynthesis?",
    context="Photosynthesis is how plants make food."
)

print(result)