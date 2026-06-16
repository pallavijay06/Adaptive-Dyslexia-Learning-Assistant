from services.tts_service import generate_audio

sample_text = """
Photosynthesis is how plants make food.
Plants use sunlight, water and carbon dioxide.
"""

audio_file = generate_audio(sample_text)

print("Generated:", audio_file)