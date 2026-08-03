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

print('PIPELINE AUDIT START')
for title, text in SAMPLES.items():
    print('\n' + '#' * 80)
    print(f'TOPIC: {title}')
    print('#' * 80)
    understanding = understand_chapter(text)
    structure = organize_knowledge(understanding, text)
    validated = validate_educational_knowledge(structure)
    print('\nCHAPTER')
    print(validated.chapter_title)
    print('\nLearning Objective')
    print(validated.learning_objective)
    print('\nOriginal Educational Structure')
    for sec in validated.sections:
        print(f'- Title: {sec.title}')
        print(f'  Type: {sec.type}')
        print(f'  Pedagogical role: {sec.pedagogical_role}')
        print(f'  Importance: {sec.importance}')
        print(f'  Learning points: {[pt.text for pt in sec.learning_points]}')

    print('\nSTAGE 1: Educational Branch Selection Engine')
    selected = selection_engine.plan(validated)
    print('Selected Branches:', selected.selected_titles)
    print('Rejected Branches:', [sec.title for sec in validated.sections if sec.title not in selected.selected_titles])

    print('\nSTAGE 2: Educational Branch Renaming Engine')
    for branch in selected.branches:
        print('Original Title:', branch.title)
    captured.clear()
    try:
        renamed = rename_engine.plan(selected)
    except Exception as exc:
        renamed = selected
        print('Stage 2 ERROR:', exc)
    print('LLM Prompt:', captured.get('prompt', '<none>'))
    print('LLM Raw Response:', captured.get('response', '<none>'))
    print('Renamed Titles:', [branch.title for branch in renamed.branches])

    print('\nSTAGE 3: Hierarchy Optimization Engine')
    optimized = hierarchy_engine.plan(renamed)
    print('Hierarchy changes:', hierarchy_engine.changes)
    print('Optimized Branches:', [branch.title for branch in optimized.branches])

    print('\nSTAGE 4: Semantic Child Assignment Engine')
    reassigned = child_assignment_engine.plan(optimized)
    print('Reassignments:', child_assignment_engine.reassignments)
    print('Final Branches after child assignment:', [branch.title for branch in reassigned.branches])

    print('\nSTAGE 5: Educational Sequencing Engine')
    sequenced = sequence_engine.plan(reassigned)
    print('Ordered Branches:', [branch.title for branch in sequenced.branches])

    print('\nSTAGE 6: Layout Planning Engine')
    final_layout = layout_engine.plan(sequenced)
    print('Layout branch ids:', [branch.id for branch in final_layout])
    print('Layout branch titles:', [branch.title for branch in final_layout])

print('\nPIPELINE AUDIT COMPLETE')
