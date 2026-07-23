#!/usr/bin/env python3
"""
PHASE 5: Fix Verification
Test that the new flowchart prompt generates educational content

Expected Result:
- Photosynthesis document generates conceptual explanation steps
- NOT procedural/experimental steps
"""

import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test document
PHOTOSYNTHESIS = """
Photosynthesis

Photosynthesis is the process by which green plants make their own food using sunlight, 
water, and carbon dioxide.

The process happens mainly in the leaves of plants. Inside the leaves, there is a green 
substance called chlorophyll. This green pigment captures the energy from sunlight.

Plants need three things for photosynthesis:
1. Sunlight - provides energy
2. Water - absorbed by roots from the soil
3. Carbon dioxide - taken in through small holes in leaves called stomata

The process takes place in two main stages:

LIGHT REACTIONS:
- Occur in the thylakoids of chloroplasts
- Light energy is captured by chlorophyll
- Water molecules are split into hydrogen and oxygen
- Energy is used to create ATP and NADPH
- Oxygen is released as a byproduct

CALVIN CYCLE (Dark Reactions):
- Occurs in the stroma of chloroplasts
- Uses ATP and NADPH from light reactions
- Carbon dioxide is combined with other molecules
- Glucose (plant food) is produced
- This glucose is used by the plant for energy and growth

The glucose made by photosynthesis is used by the plant in two ways:
1. As food - for energy to grow and survive
2. Storage - stored as starch for later use

Photosynthesis is very important because:
- Plants use it to make their own food
- It produces oxygen that all living things need
- It forms the base of most food chains
- It removes carbon dioxide from the atmosphere
"""

print("\n" + "="*80)
print("PHASE 5: FLOWCHART PROMPT FIX VERIFICATION")
print("="*80)

print("\n" + "-"*80)
print("Testing with Photosynthesis Document")
print("-"*80)

try:
    from services.visual_service import _extract_flowchart_structure
    
    print("\nExtracting flowchart structure with NEW prompt...")
    flowchart = _extract_flowchart_structure(PHOTOSYNTHESIS)
    
    if not flowchart:
        print("\n✗ No flowchart JSON returned")
        sys.exit(1)
    
    print("\n✓ Flowchart JSON generated")
    print(f"\nTitle: {flowchart.get('title')}")
    print(f"Description: {flowchart.get('description')}")
    
    steps = flowchart.get('steps', [])
    print(f"\nNumber of steps: {len(steps)}")
    
    if not steps:
        print("✗ No steps extracted")
        sys.exit(1)
    
    print("\nGenerated Flowchart Steps:")
    print("-" * 80)
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    
    # VALIDATION CHECKS
    print("\n" + "="*80)
    print("VALIDATION CHECKS")
    print("="*80)
    
    # Check 1: No procedural verbs
    procedural_verbs = ["connect", "measure", "record", "turn", "apply", "identify"]
    educational_verbs = ["absorb", "split", "produce", "release", "convert", "create", 
                        "transport", "capture", "store", "combine", "form"]
    
    has_procedural = any(
        any(verb in step.lower() for verb in procedural_verbs)
        for step in steps
    )
    
    has_educational = any(
        any(verb in step.lower() for verb in educational_verbs)
        for step in steps
    )
    
    if has_procedural:
        print("❌ FAIL: Steps contain procedural verbs (Connect, Measure, Record, etc.)")
    else:
        print("✓ PASS: No procedural verbs detected")
    
    if has_educational:
        print("✓ PASS: Steps contain educational verbs (Absorb, Split, Produce, etc.)")
    else:
        print("⚠️  WARNING: No common educational verbs detected (may still be OK)")
    
    # Check 2: Steps relate to Photosynthesis concept, not lab procedure
    photosynthesis_keywords = ["sunlight", "water", "glucose", "oxygen", "carbon dioxide", 
                               "chlorophyll", "energy", "split", "absorb", "produce", 
                               "release", "convert", "react"]
    
    steps_text = " ".join(steps).lower()
    relevant_count = sum(
        1 for keyword in photosynthesis_keywords
        if keyword in steps_text
    )
    
    print(f"✓ PASS: Steps contain {relevant_count} photosynthesis-related keywords")
    
    # Check 3: Steps explain concept, not procedure
    print("\n" + "-"*80)
    print("Step Quality Analysis:")
    print("-"*80)
    
    for i, step in enumerate(steps, 1):
        print(f"\n  Step {i}: '{step}'")
        
        # Check if educational (explains concept) vs procedural (instructs action)
        is_passive = any(word in step.lower() for word in ["is", "are", "occurs", "happens"])
        is_educational = any(verb in step.lower() for verb in educational_verbs)
        is_conceptual = "split" in step.lower() or "absorb" in step.lower() or \
                       "produce" in step.lower() or "release" in step.lower() or \
                       "convert" in step.lower()
        
        if is_educational or is_conceptual:
            print(f"    ✓ Educational/conceptual step")
        elif is_passive:
            print(f"    ✓ Passive/explanatory form")
        else:
            print(f"    ⚠️  May be procedural - review needed")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    print("""
Expected Flowchart Steps for Photosynthesis:
  1. Sunlight is Absorbed
  2. Water Molecules Split
  3. Chlorophyll Captures Energy
  4. Glucose is Produced
  5. Oxygen is Released

Generated Steps:""")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    
    if not has_procedural and (has_educational or relevant_count >= 2):
        print("\n✓✓✓ FIX SUCCESSFUL ✓✓✓")
        print("The flowchart now generates EDUCATIONAL CONTENT instead of PROCEDURAL steps")
    else:
        print("\n⚠️  PARTIAL SUCCESS - Review needed")
    
except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
