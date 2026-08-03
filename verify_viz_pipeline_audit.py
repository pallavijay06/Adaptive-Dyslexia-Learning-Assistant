from __future__ import annotations

from pathlib import Path
from services.educational_understanding_engine import understand_chapter
from services.knowledge_organization_engine import organize_knowledge
from services.educational_validation_engine import validate_educational_knowledge
from services.visualization_planning_engine import VisualizationPlanningEngine

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "verify_viz_pipeline_audit_log.txt"

SAMPLES = {
    'Photosynthesis': 'Photosynthesis is the process by which green plants use sunlight, water, and carbon dioxide to produce glucose and oxygen. Chlorophyll in the chloroplasts captures light energy. Roots absorb water. Stomata allow carbon dioxide to enter leaves.',
    "Ohm's Law": "Ohm's Law relates voltage, current, and resistance in an electrical circuit. Voltage drives current through a conductor. Resistance opposes current. The formula is V = I * R.",
    'Water Cycle': 'The water cycle includes evaporation, condensation, precipitation, and collection. Sunlight evaporates water from surfaces. Clouds form by condensation. Precipitation returns water to the ground.',
    'Cell Division': 'Cell division includes mitosis and meiosis. Mitosis produces two identical daughter cells. DNA is replicated before division. The process is essential for growth and repair.',
    'Operating Systems': 'Operating systems manage computer hardware and software. They provide process scheduling, memory management, file systems, and user interfaces for efficient system operation.',
    'Database Normalization': 'Database normalization organizes data to reduce redundancy and improve consistency. The chapter explains normal forms, keys, anomalies, and design principles for relational databases.',
}

engine = VisualizationPlanningEngine()
selection_engine = engine.selection_engine
rename_engine = engine.rename_engine
hierarchy_engine = engine.hierarchy_engine
child_assignment_engine = engine.child_assignment_engine
sequence_engine = engine.sequence_engine
layout_engine = engine.layout_engine

lines: list[str] = []
lines.append('PIPELINE VERIFICATION AUDIT START')
for title, text in SAMPLES.items():
    lines.append('\n' + '=' * 80)
    lines.append(f'TOPIC: {title}')
    lines.append('=' * 80)
    try:
        understanding = understand_chapter(text)
        structure = organize_knowledge(understanding, text)
        validated = validate_educational_knowledge(structure)
    except Exception as exc:
        lines.append('ERROR during educational validation: ' + repr(exc))
        continue

    lines.append('CHAPTER: ' + validated.chapter_title)
    lines.append('LEARNING OBJECTIVE: ' + validated.learning_objective)
    lines.append('ORIGINAL SECTIONS:')
    for sec in validated.sections:
        lines.append(f'  - {sec.title} | type={sec.type} | role={sec.pedagogical_role} | importance={sec.importance}')

    try:
        selected = selection_engine.plan(validated)
        selected_titles = [branch.title for branch in selected.branches]
        lines.append('STAGE 1: Selected Branch Titles: ' + str(selected_titles))
    except Exception as exc:
        lines.append('STAGE 1 ERROR: ' + repr(exc))
        continue

    try:
        renamed = rename_engine.plan(selected)
        lines.append('STAGE 2: Renamed Branch Titles: ' + str([branch.title for branch in renamed.branches]))
    except Exception as exc:
        lines.append('STAGE 2 ERROR: ' + repr(exc))
        renamed = selected

    try:
        optimized = hierarchy_engine.plan(renamed)
        lines.append('STAGE 3: Optimized Branch Titles: ' + str([branch.title for branch in optimized.branches]))
        lines.append('STAGE 3: Hierarchy changes: ' + str(hierarchy_engine.changes))
    except Exception as exc:
        lines.append('STAGE 3 ERROR: ' + repr(exc))
        continue

    try:
        reassigned = child_assignment_engine.plan(optimized)
        lines.append('STAGE 4: Reassignments: ' + str(child_assignment_engine.reassignments))
        lines.append('STAGE 4: Branch titles after reassignment: ' + str([branch.title for branch in reassigned.branches]))
    except Exception as exc:
        lines.append('STAGE 4 ERROR: ' + repr(exc))
        continue

    try:
        sequenced = sequence_engine.plan(reassigned)
        lines.append('STAGE 5: Sequenced Branch Titles: ' + str([branch.title for branch in sequenced.branches]))
    except Exception as exc:
        lines.append('STAGE 5 ERROR: ' + repr(exc))
        continue

    try:
        final_layout = layout_engine.plan(sequenced)
        lines.append('STAGE 6: Final layout branch ids: ' + str([branch.id for branch in final_layout]))
        lines.append('STAGE 6: Final layout branch titles: ' + str([branch.title for branch in final_layout]))
    except Exception as exc:
        lines.append('STAGE 6 ERROR: ' + repr(exc))
        continue

lines.append('\nPIPELINE VERIFICATION AUDIT COMPLETE')
LOG_PATH.write_text('\n'.join(lines), encoding='utf-8')
print('WROTE', LOG_PATH)
