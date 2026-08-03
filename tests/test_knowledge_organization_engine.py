import json

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


def build_understanding(topic: str, text: str) -> EducationalUnderstanding:
    return EducationalUnderstanding(
        chapter_title=topic,
        subject="General Studies",
        domain="General Studies",
        topic_complexity="Medium",
        learning_objective="Understand the main ideas in this chapter.",
        major_sections=["Introduction", "Core Concepts", "Applications", "Summary"],
    )


def test_organize_knowledge_returns_textbook_like_sections():
    for topic, text in SAMPLES.items():
        understanding = build_understanding(topic, text)
        structure = organize_knowledge(understanding, text)

        assert structure.chapter_title
        assert structure.learning_objective
        assert structure.sections
        assert all(section.learning_points for section in structure.sections)

        print("-------------------------------------")
        print(json.dumps(structure.to_dict(), indent=2, ensure_ascii=False))

    print("-------------------------------------")
