import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from services.educational_understanding_engine import understand_chapter
from services.knowledge_organization_engine import organize_knowledge
from services.educational_validation_engine import validate_educational_knowledge
from services.visualization_planning_engine import VisualizationPlanningEngine
import services.visualization_planning_stages as spsmod

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

captured = {}
original_generate_content = spsmod.generate_content

def capturing_generate_content(prompt, max_tokens=None):
    captured['prompt'] = prompt
    try:
        result = original_generate_content(prompt, max_tokens=max_tokens)
        captured['response'] = result
        return result
    except Exception as exc:
        captured['response'] = f'ERROR: {exc}'
        raise

spsmod.generate_content = capturing_generate_content

lines = []
lines.append('PIPELINE AUDIT START')
for title, text in SAMPLES.items():
    lines.append('\n' + '#' * 80)
    lines.append(f'TOPIC: {title}')
    lines.append('#' * 80)
    understanding = understand_chapter(text)
    structure = organize_knowledge(understanding, text)
    validated = validate_educational_knowledge(structure)
    lines.append('\nCHAPTER')
    lines.append(validated.chapter_title)
    lines.append('\nLearning Objective')
    lines.append(validated.learning_objective)
    lines.append('\nOriginal Educational Structure')
    for sec in validated.sections:
        lines.append(f'- Title: {sec.title}')
        lines.append(f'  Type: {sec.type}')
        lines.append(f'  Pedagogical role: {sec.pedagogical_role}')
        lines.append(f'  Importance: {sec.importance}')
        lines.append(f'  Learning points: {[pt.text for pt in sec.learning_points]}')

    lines.append('\nSTAGE 1: Educational Branch Selection Engine')
    selected = selection_engine.plan(validated)
    selected_titles = [branch.title for branch in selected.branches]
    lines.append('Selected Branches: ' + str(selected_titles))
    lines.append('Rejected Branches: ' + str([sec.title for sec in validated.sections if sec.title not in selected_titles]))

    lines.append('\nSTAGE 2: Educational Branch Renaming Engine')
    for branch in selected.branches:
        lines.append('Original Title: ' + branch.title)
    captured.clear()
    try:
        renamed = rename_engine.plan(selected)
    except Exception as exc:
        renamed = selected
        lines.append('Stage 2 ERROR: ' + repr(exc))
    lines.append('LLM Prompt: ' + captured.get('prompt', '<none>'))
    lines.append('LLM Raw Response: ' + captured.get('response', '<none>'))
    lines.append('Renamed Titles: ' + str([branch.title for branch in renamed.branches]))

    lines.append('\nSTAGE 3: Hierarchy Optimization Engine')
    optimized = hierarchy_engine.plan(renamed)
    lines.append('Hierarchy changes: ' + str(hierarchy_engine.changes))
    lines.append('Optimized Branches: ' + str([branch.title for branch in optimized.branches]))

    lines.append('\nSTAGE 4: Semantic Child Assignment Engine')
    reassigned = child_assignment_engine.plan(optimized)
    lines.append('Reassignments: ' + str(child_assignment_engine.reassignments))
    lines.append('Final Branches after child assignment: ' + str([branch.title for branch in reassigned.branches]))

    lines.append('\nSTAGE 5: Educational Sequencing Engine')
    sequenced = sequence_engine.plan(reassigned)
    lines.append('Ordered Branches: ' + str([branch.title for branch in sequenced.branches]))

    lines.append('\nSTAGE 6: Layout Planning Engine')
    final_layout = layout_engine.plan(sequenced)
    lines.append('Layout branch ids: ' + str([branch.id for branch in final_layout]))
    lines.append('Layout branch titles: ' + str([branch.title for branch in final_layout]))

lines.append('\nPIPELINE AUDIT COMPLETE')
output_path = ROOT / 'verify_viz_pipeline_log.txt'
output_path.write_text('\n'.join(lines), encoding='utf-8')
print('WROTE', output_path)
