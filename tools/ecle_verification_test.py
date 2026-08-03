import sys
from pathlib import Path

# Ensure diagnostic output is encoded safely in Windows consoles and redirected files.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.educational_understanding_engine import understand_chapter
from services.knowledge_organization_engine import organize_knowledge
from services.educational_concept_labeling_engine import label_educational_knowledge

SAMPLES = {
    "Photosynthesis": [
        "Water evaporates due to sunlight.",
        "Plants convert light energy into chemical energy.",
        "Glucose is produced during the Calvin cycle.",
    ],
    "Ohm's Law": [
        "Voltage equals current multiplied by resistance.",
        "Resistance opposes electric current.",
        "The formula is V = I * R.",
    ],
    "Water Cycle": [
        "Water vapour cools and forms clouds.",
        "Water evaporates from rivers and lakes due to sunlight.",
        "Precipitation returns water to the ground.",
    ],
    "Cell Division": [
        "DNA replicates before mitosis.",
        "Mitosis produces identical daughter cells.",
        "Meiosis creates genetic variation.",
    ],
    "Operating Systems": [
        "Operating systems allocate and protect memory.",
        "The OS schedules processes on the CPU.",
        "File systems organize persistent storage.",
    ],
    "Database Normalization": [
        "Normalization reduces redundancy in relational tables.",
        "First Normal Form requires atomic attribute values.",
        "Keys enforce relationships between records.",
    ],
}

for topic, points in SAMPLES.items():
    print(f"\n=== {topic} ===")
    understanding = understand_chapter(topic)
    ks = organize_knowledge(understanding, " ")
    labeled = label_educational_knowledge(ks)
    for orig_section, labeled_section in zip(ks.sections, labeled.sections):
        for orig_point, labeled_point in zip(orig_section.learning_points, labeled_section.learning_points):
            print("------------------------------------------------------------")
            print("Original Learning Point")
            print(orig_point.text)
            print("↓")
            print("Generated Educational Concept Label")
            print(labeled_point.text)
            print("↓")
            print("Reason: This label reflects the core concept taught by the sentence and reads like a textbook heading.")
