from services.educational_understanding_engine import understand_chapter


SAMPLES = {
    "Photosynthesis": "Photosynthesis is the process by which green plants use sunlight, water, and carbon dioxide to produce glucose and oxygen. Chlorophyll in the chloroplasts captures light energy. Roots absorb water. Stomata allow carbon dioxide to enter leaves.",
    "Ohm's Law": "Ohm's Law relates voltage, current, and resistance in an electrical circuit. Voltage drives current through a conductor. Resistance opposes current. The formula is V = I * R.",
    "Water Cycle": "The water cycle includes evaporation, condensation, precipitation, and collection. Sunlight evaporates water from surfaces. Clouds form by condensation. Precipitation returns water to the ground.",
    "Cell Division": "Cell division includes mitosis and meiosis. Mitosis produces two identical daughter cells. DNA is replicated before division. The process is essential for growth and repair.",
    "Computer Networks": "Computer networks connect devices so they can share data and resources. The topic covers network types, transmission media, protocols, and common services such as the internet and local area networks.",
    "Operating Systems": "Operating systems manage computer hardware and software. They provide process scheduling, memory management, file systems, and user interfaces for efficient system operation.",
    "Database Normalization": "Database normalization organizes data to reduce redundancy and improve consistency. The chapter explains normal forms, keys, anomalies, and design principles for relational databases.",
}


def test_understand_chapter_returns_educational_structure_for_core_topics():
    for topic, text in SAMPLES.items():
        understanding = understand_chapter(text)

        assert understanding.chapter_title
        assert understanding.learning_objective
        assert understanding.major_sections
        assert understanding.subject
        assert understanding.domain

        print("-------------------------------------")
        print("Chapter Title")
        print(understanding.chapter_title)
        print("Learning Objective")
        print(understanding.learning_objective)
        print("Major Sections")
        print("\n".join(understanding.major_sections))

    print("-------------------------------------")
