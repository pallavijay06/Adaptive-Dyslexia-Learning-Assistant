from services.visual_service import generate_visual_content

sample_text = """
Plants absorb sunlight.
Plants absorb water.
Photosynthesis occurs.
Food is produced.
Oxygen is released.
"""

result = generate_visual_content(sample_text)

print(result)