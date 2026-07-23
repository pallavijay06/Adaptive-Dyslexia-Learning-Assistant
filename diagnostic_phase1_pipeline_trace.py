#!/usr/bin/env python3
"""
PHASE 1: Complete Pipeline Tracing
Trace every intermediate output to find where "Photosynthesis" becomes "Connect Roots Water"
"""

import sys
import json
import logging
from pathlib import Path

# Setup path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging to see intermediate steps
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)

from services.visual_service import (
    _stage1_extract_concepts,
    _stage2_rank_and_deduplicate,
    _stage3_build_mindmap_json,
    _extract_flowchart_structure,
    _extract_visual_structure,
)
from services.educational_visuals import detect_topic

# Photosynthesis test document
PHOTOSYNTHESIS_DOC = """
Photosynthesis

Photosynthesis is the process by which green plants make their own food using sunlight, water, and carbon dioxide. This process happens mainly in the leaves of plants.

How does photosynthesis work?

Plants need three things for photosynthesis:
1. Sunlight - provides energy
2. Water - absorbed by roots from the soil
3. Carbon dioxide - taken in through small holes in leaves called stomata

Inside the leaves, there is a green substance called chlorophyll. This green pigment captures the energy from sunlight. The energy is used to break water molecules apart and to combine carbon dioxide with hydrogen to make glucose (plant food).

The process takes place in two main stages:
1. Light reactions - happen in the thylakoids, where light energy is captured
2. Dark reactions (Calvin cycle) - happen in the stroma, where glucose is made

During photosynthesis, plants produce oxygen as a waste product. This oxygen is released into the air through the stomata. Humans and animals breathe this oxygen.

The glucose made by photosynthesis is used by the plant in two ways:
1. As food - for energy to grow and survive
2. Storage - stored as starch for later use

Why is photosynthesis important?

Photosynthesis is very important because:
- Plants use it to make their own food
- It produces oxygen that all living things need
- It forms the base of most food chains
- It removes carbon dioxide from the atmosphere
"""


def print_section(title: str, char: str = "="):
    """Print a formatted section header."""
    print(f"\n{char * 80}")
    print(f"  {title}")
    print(f"{char * 80}\n")


def print_json(data: dict, label: str = ""):
    """Pretty print JSON data."""
    if label:
        print(f"\n{label}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def phase1_trace_pipeline():
    """PHASE 1: Trace complete pipeline with intermediate outputs."""
    
    print_section("PHASE 1: COMPLETE PIPELINE TRACING", "=")
    print("Tracing: DOCUMENT → CONCEPTS → JSON → RENDERER")
    print(f"Document length: {len(PHOTOSYNTHESIS_DOC)} chars")
    print(f"Topic: Photosynthesis")
    
    # ===== STEP 0: Topic Detection =====
    print_section("STEP 0: Topic Detection", "-")
    detected_topic = detect_topic(PHOTOSYNTHESIS_DOC)
    print(f"Detected topic: {detected_topic}")
    
    # ===== STEP 1: Extract Concepts (Stage 1) =====
    print_section("STEP 1: Extract Concepts (Stage 1 LLM)", "-")
    print("Prompt asks for: Educational concepts with titles and explanations")
    print("Input: First 3000 chars of document")
    
    concepts = _stage1_extract_concepts(PHOTOSYNTHESIS_DOC)
    print(f"\n✓ Stage 1 returned {len(concepts)} concepts")
    
    if concepts:
        print("\nConcepts extracted:")
        for i, c in enumerate(concepts[:5], 1):  # Show first 5
            print(f"\n  Concept {i}:")
            print(f"    Topic: {c.get('topic')}")
            print(f"    Concept: {c.get('concept')}")
            print(f"    Fact: {c.get('fact')[:80]}...")
            print(f"    Importance: {c.get('importance')}")
    else:
        print("\n✗ NO CONCEPTS EXTRACTED - Stage 1 failed")
        return
    
    # ===== STEP 2: Rank and Deduplicate (Stage 2) =====
    print_section("STEP 2: Rank and Deduplicate (Stage 2 - Pure Python)", "-")
    clean_concepts = _stage2_rank_and_deduplicate(concepts)
    print(f"✓ After deduplication: {len(clean_concepts)} concepts")
    
    if clean_concepts:
        print("\nCleaned concepts (top 3):")
        for i, c in enumerate(clean_concepts[:3], 1):
            print(f"\n  {i}. {c.get('concept')}")
            print(f"     Importance: {c.get('importance')}")
    
    # ===== STEP 3: Build Mind Map JSON (Stage 3) =====
    print_section("STEP 3: Build Mind Map JSON (Stage 3 LLM)", "-")
    print("Prompt asks for: Mind map structure with branches and emoji")
    
    topic_title = next(
        (c["topic"] for c in clean_concepts if c.get("topic", "").strip()),
        clean_concepts[0]["concept"] if clean_concepts else "Learning Concept",
    )
    
    mindmap_json = _stage3_build_mindmap_json(topic_title, clean_concepts)
    print(f"\n✓ Mind map JSON created")
    
    if mindmap_json:
        print(f"  Title: {mindmap_json.get('title')}")
        print(f"  Description: {mindmap_json.get('description')[:60]}...")
        print(f"  Branches: {len(mindmap_json.get('branches', []))}")
        
        if mindmap_json.get('branches'):
            print("\n  Branch labels (first 3):")
            for i, branch in enumerate(mindmap_json.get('branches', [])[:3], 1):
                label = branch.get('label', {})
                if isinstance(label, dict):
                    print(f"    {i}. {label.get('text')} {label.get('emoji', '')}")
                else:
                    print(f"    {i}. {label}")
    else:
        print("  ✗ No mind map JSON returned")
    
    # ===== STEP 4: Extract Flowchart Structure =====
    print_section("STEP 4: Extract Flowchart Structure (Separate Prompt)", "-")
    print("Prompt asks for: 'main sequential process as a flowchart'")
    print("         with 'Action Verb + Object' steps")
    print("         like: 'Connect Battery', 'Measure Voltage', 'Record Data'")
    
    flowchart_json = _extract_flowchart_structure(PHOTOSYNTHESIS_DOC)
    print(f"\n✓ Flowchart JSON created")
    
    if flowchart_json:
        print(f"  Title: {flowchart_json.get('title')}")
        print(f"  Description: {flowchart_json.get('description')}")
        print(f"  Steps: {len(flowchart_json.get('steps', []))}")
        
        if flowchart_json.get('steps'):
            print("\n  ❌ FLOWCHART STEPS (THIS IS THE PROBLEM):")
            for i, step in enumerate(flowchart_json.get('steps', [])[:10], 1):
                print(f"    {i}. {step}")
            
            print("\n  ⚠️ ANALYSIS:")
            print("     These are PROCEDURAL steps (like lab instructions)")
            print("     Instead of CONCEPTUAL steps (explaining photosynthesis)")
            print("     Expected: 'Absorb Sunlight', 'Split Water', 'Produce Glucose'")
            print("     Got: 'Connect...', 'Measure...', 'Record...'")
    else:
        print("  ✗ No flowchart JSON returned")
    
    # ===== STEP 5: Complete Visual Structure =====
    print_section("STEP 5: Complete Visual Structure", "-")
    print("Merging mind map and flowchart outputs...")
    
    structure = _extract_visual_structure(PHOTOSYNTHESIS_DOC)
    print(f"\n✓ Complete structure created")
    print(f"  Title: {structure.get('title')}")
    print(f"  Branches: {len(structure.get('branches', []))}")
    print(f"  Steps: {len(structure.get('steps', []))}")
    
    print_section("ROOT CAUSE ANALYSIS", "=")
    print("""
    PROBLEM IDENTIFIED: The _FLOWCHART_PROMPT is asking for PROCEDURAL STEPS
    
    Location: services/visual_service.py, line ~425
    
    Current Prompt Says:
    "Read the document below and extract the main sequential process as a flowchart."
    
    With Rules:
    "Each step MUST be EXACTLY ONE ACTION: imperative verb + direct object."
    "Start with a strong action verb from: Connect, Measure, Apply, Calculate,
     Observe, Record, Compare, Insert, Remove, Turn, Check, Find, Identify,
     Mark, Count."
    
    IMPACT:
    For Photosynthesis, LLM interprets this as a LAB EXPERIMENT procedure:
    - "Connect Roots" (connecting to water?)
    - "Measure Plant Sugar" (measuring output?)
    - "Record Fresh Air" (measuring oxygen?)
    
    Instead of CONCEPTUAL EXPLANATION:
    - "Absorb Sunlight"
    - "Split Water"
    - "Produce Glucose"
    
    ROOT CAUSE:
    The flowchart prompt is designed for PROCEDURAL flowcharts (experiments)
    NOT for CONCEPTUAL flowcharts (explanations)
    """)


if __name__ == "__main__":
    try:
        phase1_trace_pipeline()
    except Exception as e:
        print(f"\n✗ Pipeline tracing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
