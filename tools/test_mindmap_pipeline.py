from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.visual_service import _stage1_extract_concepts, _stage2_rank_and_deduplicate, _stage3_build_mindmap_json

SAMPLES = {
    "Photosynthesis": "Photosynthesis is the process by which green plants use sunlight, water, and carbon dioxide to produce glucose and oxygen. Chlorophyll in the chloroplasts captures light energy. Roots absorb water. Stomata allow carbon dioxide to enter leaves.",
    "Ohm's Law": "Ohm's Law relates voltage, current, and resistance in an electrical circuit. Voltage drives current through a conductor. Resistance opposes current. The formula is V = I * R.",
    "Water Cycle": "The water cycle includes evaporation, condensation, precipitation, and collection. Sunlight evaporates water from surfaces. Clouds form by condensation. Precipitation returns water to the ground.",
    "Cell Division": "Cell division includes mitosis and meiosis. Mitosis produces two identical daughter cells. DNA is replicated before division. The process is essential for growth and repair.",
}


def run_sample(title, text):
    print('\n' + '='*40)
    print('Sample:', title)
    concepts = _stage1_extract_concepts(text)
    print('Stage1 concepts:', concepts)
    validated = _stage2_rank_and_deduplicate(concepts, text)
    print('Stage2 validated:', validated)
    structure = _stage3_build_mindmap_json(title, validated, text)
    print('Stage3 structure:', structure)


if __name__ == '__main__':
    for t, txt in SAMPLES.items():
        run_sample(t, txt)
