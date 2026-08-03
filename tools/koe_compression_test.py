import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.educational_understanding_engine import understand_chapter
from services.knowledge_organization_engine import organize_knowledge
from services.knowledge_compression_engine import compress_educational_knowledge

SAMPLES = {
    "Photosynthesis": (
        "Photosynthesis converts sunlight into chemical energy stored as glucose. Chlorophyll absorbs sunlight. Glucose is synthesized in chloroplasts. Oxygen is released as a byproduct.") ,
    "Ohm's Law": (
        "Ohm's Law states that voltage equals current multiplied by resistance. Voltage drives current through a circuit. Resistance opposes current and reduces flow.") ,
    "Water Cycle": (
        "Water evaporates from bodies of water due to solar heating. Water vapour condenses into clouds. Precipitation returns water to the surface. Collection gathers water in rivers and oceans.") ,
    "Cell Division": (
        "Mitosis produces identical daughter cells for growth and repair. DNA duplicates before division. Meiosis produces gametes and increases genetic variation.") ,
    "Operating Systems": (
        "An operating system manages hardware resources and schedules processes. Memory management provides allocation and protection. File systems organize persistent storage and access.") ,
    "Database Normalization": (
        "Normalization reduces redundancy and avoids update anomalies. First Normal Form requires atomic attributes. Second and Third Normal Forms remove partial and transitive dependencies. Keys enforce relationships between tables.") ,
}

for title, text in SAMPLES.items():
    print("\n===", title, "===")
    understanding = understand_chapter(text)
    ks = organize_knowledge(understanding, text)
    compressed = compress_educational_knowledge(ks)
    for sec, sec_c in zip(ks.sections, compressed.sections):
        print(f"\nSection: {sec.title}")
        for orig, comp in zip(sec.learning_points, sec_c.learning_points):
            print(f"- {orig.text}\n  ↓\n  {comp.text}")
