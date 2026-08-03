import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.educational_understanding_engine import EducationalUnderstanding
from services.knowledge_organization_engine import organize_knowledge

SAMPLES = {
    "Photosynthesis": "Photosynthesis is the process by which green plants use sunlight, water, and carbon dioxide to produce glucose and oxygen. Chlorophyll in the chloroplasts captures light energy. Roots absorb water. Stomata allow carbon dioxide to enter leaves.",
    "Ohm's Law": "Ohm's Law relates voltage, current, and resistance in an electrical circuit. Voltage drives current through a conductor. Resistance opposes current. The formula is V = I * R.",
    "Water Cycle": "The water cycle includes evaporation, condensation, precipitation, and collection. Sunlight evaporates water from surfaces. Clouds form by condensation. Precipitation returns water to the ground.",
    "Cell Division": "Cell division includes mitosis and meiosis. Mitosis produces two identical daughter cells. DNA is replicated before division. The process is essential for growth and repair.",
    "Computer Networks": "Computer networks connect devices so they can share data and resources. The topic covers network types, transmission media, protocols, and common services such as the internet and local area networks.",
    "Operating Systems": "Operating systems manage computer hardware and software. They provide process scheduling, memory management, file systems, and user interfaces for efficient system operation.",
    "Database Normalization": "Database normalization organizes data to reduce redundancy and improve consistency. The chapter explains normal forms, keys, anomalies, and design principles for relational databases.",
}


def run_sample(title, text):
    understanding = EducationalUnderstanding(
        chapter_title=title,
        subject="General Studies",
        domain="General Studies",
        topic_complexity="Medium",
        learning_objective="Understand the main ideas in this chapter.",
        major_sections=["Introduction", "Core Concepts", "Applications", "Summary"],
    )
    structure = organize_knowledge(understanding, text)
    print("-------------------------------------")
    print(json.dumps(structure.to_dict(), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    for title, text in SAMPLES.items():
        run_sample(title, text)
