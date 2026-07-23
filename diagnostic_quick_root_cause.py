#!/usr/bin/env python3
"""
QUICK ROOT CAUSE ANALYSIS
Check the flowchart prompt directly
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS: Flowchart Content Generation")
print("="*80)

# Read the visual_service.py to inspect the prompts
with open(project_root / "services" / "visual_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the FLOWCHART_PROMPT
start_idx = content.find('_FLOWCHART_PROMPT = """')
end_idx = content.find('"""', start_idx + 30)

if start_idx != -1 and end_idx != -1:
    prompt_section = content[start_idx:end_idx + 3]
    
    print("\n" + "="*80)
    print("THE FLOWCHART PROMPT")
    print("="*80)
    # Show just the key parts
    lines = prompt_section.split('\n')
    for i, line in enumerate(lines[:60]):  # First 60 lines
        if i < 40:  # Show the critical section
            print(line)
    
    print("\n" + "="*80)
    print("ROOT CAUSE IDENTIFIED")
    print("="*80)
    
    print("""
The _FLOWCHART_PROMPT has these problematic instructions:

1. "Read the document below and extract the main sequential PROCESS as a flowchart."
   ↳ PROBLEM: It says "process" not "concept explanation"

2. "Each step MUST be EXACTLY ONE ACTION: imperative verb + direct object."
   ↳ PROBLEM: Imperative verbs (Connect, Measure, Record) are for PROCEDURES

3. Allowed verbs: "Connect, Measure, Apply, Calculate, Observe, Record, Compare..."
   ↳ PROBLEM: These are LAB EXPERIMENT verbs, not CONCEPTUAL verbs

4. EXAMPLE USED: "Connect Battery", "Measure Voltage", "Turn Switch On"
   ↳ PROBLEM: These are instruction steps, not concept explanation steps

WHAT THIS CAUSES:
When LLM reads a Photosynthesis document with this prompt, it thinks:
"I need to describe HOW TO PERFORM PHOTOSYNTHESIS" (lab procedure)
NOT "I need to EXPLAIN PHOTOSYNTHESIS" (conceptual explanation)

So it generates:
- "Connect Roots" (connect roots to water?)
- "Identify Leaves" (identify where photosynthesis happens?)
- "Calculate Plant Sugar" (measure the output?)
- "Record Fresh Air" (record oxygen production?)

These are PROCEDURAL STEPS (experiment), not EXPLANATORY STEPS (concept).

COMPARISON:
Flowchart SHOULD explain: 
✓ Sunlight is Absorbed
✓ Water Splits
✓ Glucose is Produced
✓ Oxygen is Released

Flowchart ACTUALLY explains:
✗ Connect Roots
✗ Identify Leaves  
✗ Calculate Sugar
✗ Record Air
    """)

print("\n" + "="*80)
print("WHERE TO FIX")
print("="*80)

print("""
File: services/visual_service.py

Function: _extract_flowchart_structure()
         (called by _extract_visual_structure())

Prompt Variable: _FLOWCHART_PROMPT (line ~410-455)

FIX REQUIRED:
Change the prompt from asking for PROCEDURAL steps
TO asking for CONCEPTUAL explanation steps

The prompt should NOT say "extract the main sequential process"
It should say "extract the main conceptual stages" or "extract the key steps that explain"
""")
