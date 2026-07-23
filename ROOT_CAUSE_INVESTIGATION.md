# ROOT CAUSE INVESTIGATION REPORT
## Visual Learning Pipeline - Incorrect Educational Content

---

## EXECUTIVE SUMMARY

The generated flowcharts produce **procedural laboratory steps** instead of **conceptual explanation steps**.

**Example Problem:**
- Input: Photosynthesis educational document
- Expected Flowchart: "Absorb Sunlight" → "Split Water" → "Produce Glucose" → "Release Oxygen"
- Actual Flowchart: "Connect Roots" → "Identify Leaves" → "Calculate Plant Sugar" → "Record Fresh Air"

**Root Cause:** The `_FLOWCHART_PROMPT` is designed for procedural processes (like lab experiments), not conceptual explanations (like educational diagrams).

---

## PIPELINE ARCHITECTURE

```
Document Input
    ↓
    ├─→ [STAGE 1] _stage1_extract_concepts() (LLM)
    │   ├─→ Extracts educational concepts
    │   └─→ Returns: topic, description, nodes with importance
    │
    ├─→ [STAGE 2] _stage2_rank_and_deduplicate() (Pure Python)
    │   └─→ Returns: ranked, deduplicated concepts
    │
    ├─→ [STAGE 3] _stage3_build_mindmap_json() (LLM)
    │   └─→ Returns: mind map JSON with branches and emoji
    │
    └─→ [SEPARATE] _extract_flowchart_structure() (LLM)
        └─→ Returns: flowchart steps  ⚠️ PROBLEM HERE
            
    ↓
    Merge into visual structure
    ↓
    Render mind map and flowchart
```

---

## PHASE 1: PIPELINE TRACE & INTERMEDIATE OUTPUTS

### Stage 1: Educational Concept Extraction ✓ WORKING CORRECTLY

**File:** `services/visual_service.py`, lines 148-190  
**Function:** `_stage1_extract_concepts(text)`

**Prompt:** `_STAGE1_PROMPT` (lines ~132-240)

**What It Asks For:**
```
"You are an expert educational content designer creating revision notes.
...Extract:
1. TOPIC TITLE (e.g., "Photosynthesis")
2. TOPIC DESCRIPTION (e.g., "Process by which plants make food using sunlight, water, CO2")
3. EDUCATIONAL NODES with:
   - title: Short 4-8 word educational statement (e.g., "Sunlight Provides Energy")
   - explanation: Complete sentence teaching the concept
   - importance: 1-10 rating"
```

**Example Output (CORRECT):**
```json
{
  "nodes": [
    {
      "title": "Sunlight Provides Energy",
      "explanation": "Sunlight provides the energy required to convert carbon dioxide and water into glucose.",
      "importance": 9
    },
    {
      "title": "Chlorophyll Absorbs Light",
      "explanation": "Chlorophyll is the green pigment that captures sunlight inside chloroplasts.",
      "importance": 9
    },
    {
      "title": "Glucose Is Produced",
      "explanation": "Plants convert light energy into chemical energy stored as glucose.",
      "importance": 8
    }
  ]
}
```

**Result:** ✓ Stage 1 produces CORRECT educational concepts

---

### Stage 2: Rank & Deduplicate ✓ WORKING CORRECTLY

**File:** `services/visual_service.py`, lines 292-316  
**Function:** `_stage2_rank_and_deduplicate(concepts)`

**What It Does:**
1. Sorts concepts by importance (descending)
2. Removes near-duplicates using word overlap ratio >= 0.6

**Result:** ✓ Pure Python, no LLM, works correctly

---

### Stage 3: Mind Map JSON Building ✓ WORKING CORRECTLY

**File:** `services/visual_service.py`, lines 349-398  
**Function:** `_stage3_build_mindmap_json(title, concepts)`

**Prompt:** `_STAGE3_PROMPT` (lines ~319-370)

**What It Asks For:**
```
"Format the curated list into mind map JSON.
For each concept:
- Use the title exactly as provided
- Assign one relevant emoji
- Add explanation as first child
- Add second child ONLY if genuinely new fact exists"
```

**Example Output (CORRECT):**
```json
{
  "title": "Photosynthesis",
  "branches": [
    {
      "label": {"text": "Sunlight Provides Energy", "emoji": "☀️"},
      "children": [
        {"text": "Sunlight provides the energy required to convert CO2 and water into glucose.", "emoji": "⚡"}
      ]
    }
  ]
}
```

**Result:** ✓ Stage 3 produces CORRECT mind map structure

---

### ⚠️ FLOWCHART EXTRACTION - PROBLEM IDENTIFIED

**File:** `services/visual_service.py`, lines 407-463  
**Function:** `_extract_flowchart_structure(text)`

**Prompt:** `_FLOWCHART_PROMPT` (lines ~407-463)

**CURRENT PROBLEMATIC PROMPT:**

```python
_FLOWCHART_PROMPT = """
Read the document below and extract the main sequential PROCESS as a flowchart.

...

CRITICAL STEP RULES (strictly enforced):
- Each step MUST be EXACTLY ONE ACTION: imperative verb + direct object.
- Maximum 5–8 words per step.
- Start with a strong action verb from: Connect, Measure, Apply, Calculate, 
  Observe, Record, Compare, Insert, Remove, Turn, Check, Find, Identify, Mark, Count.
- CORRECT EXAMPLES:
  ✓ "Connect Battery"
  ✓ "Measure Voltage"
  ✓ "Turn Switch On"
  ✓ "Observe Current"
  ✓ "Calculate Resistance"
  ✓ "Record Data"
  ✓ "Compare Results"
"""
```

**ANALYSIS OF THE PROBLEM:**

| Aspect | Current Prompt | Problem | Result |
|--------|-----------------|---------|--------|
| Process Type | "main sequential PROCESS" | Asks for procedures | Procedural steps |
| Verb Requirement | Imperative verbs (Connect, Measure, Record) | Lab/experiment verbs | Laboratory instructions |
| Example Usage | Connect Battery, Measure Voltage, Record Data | Equipment manipulation | Experiment procedures |
| Intended Purpose | Suitable for physics experiments, circuit building | Not suitable for concept explanation | Photosynthesis → "Connect Roots, Measure Sugar, Record Air" |

**WHY THIS FAILS FOR PHOTOSYNTHESIS:**

When the LLM receives a Photosynthesis document with the instruction:
- "Extract the main sequential PROCESS"
- "Use imperative verbs like Connect, Measure, Record, Calculate, Identify"

The LLM interprets this as: **"Describe how to perform photosynthesis as an experiment"**

Instead of: **"Explain the stages of photosynthesis as a concept"**

**Generated Flowchart (INCORRECT):**
```
1. "Connect Roots Water"     (connect roots to water source)
2. "Identify Leaves Air"     (identify where air enters)
3. "Calculate Plant Sugar"   (measure sugar production)
4. "Record Fresh Air"        (record oxygen output)
```

These look like laboratory procedure instructions, not conceptual explanations.

---

## PHASE 2: PROMPT INSPECTION

### Stage 1 Prompt: ✓ CORRECT

Asks for: **Educational concepts** with titles and explanations  
Purpose: Extract facts for mind map nodes  
Result: Produces educational content  

### Stage 3 Prompt: ✓ CORRECT

Asks for: **Mind map structure** from curated concepts  
Purpose: Format concepts with emoji  
Result: Produces educational content  

### Flowchart Prompt: ❌ INCORRECT

Asks for: **Procedural PROCESS steps** with imperative verbs  
Purpose: Extract lab procedure/workflow  
Result: Produces procedural/experimental content instead of conceptual content  

---

## PHASE 3: JSON COMPARISON

### What Gemini Produces

When given the Photosynthesis document with `_FLOWCHART_PROMPT`, Gemini outputs:

```json
{
  "title": "Photosynthesis",
  "steps": [
    "Connect Roots Water",
    "Identify Leaves Air",
    "Calculate Plant Sugar",
    "Record Fresh Air"
  ]
}
```

**Problem:** These are EXPERIMENTAL procedure steps, not conceptual explanation steps.

### What We Need

```json
{
  "title": "Photosynthesis",
  "steps": [
    "Absorb Sunlight",
    "Water Splits",
    "Glucose Produced",
    "Oxygen Released"
  ]
}
```

**Solution:** Change the prompt to ask for conceptual stages, not procedural steps.

---

## PHASE 4: ROOT CAUSE DETERMINATION

**✓ ROOT CAUSE CONFIRMED:**

| Component | Status | Issue |
|-----------|--------|-------|
| Stage 1 (Concepts) | ✓ Works | Produces correct educational concepts |
| Stage 2 (Deduplicate) | ✓ Works | Pure Python logic is sound |
| Stage 3 (Mind Map) | ✓ Works | Produces correct mind map structure |
| **Flowchart Prompt** | **❌ BROKEN** | **Asks for procedural steps, not conceptual steps** |
| Rendering Engine | ✓ Works | PIL rendering is correct (Phase 6 fixes) |

**First Point Where Content Becomes Incorrect:**
1. `_FLOWCHART_PROMPT` sends instruction to LLM to extract "main sequential PROCESS"
2. LLM interprets as: "describe procedure for performing photosynthesis"
3. LLM generates procedural steps: "Connect Roots", "Measure Sugar", "Record Air"
4. These steps are rendered as-is into the flowchart

---

## PHASE 5: FIX STRATEGY

### Problem to Solve

The `_FLOWCHART_PROMPT` needs to ask for:
- **Conceptual stages** (not procedural steps)
- **Explanation verbs** (not imperative/experimental verbs)
- **Educational outcomes** (not laboratory instructions)

### Solution Design

**Change From:**
```
"extract the main sequential PROCESS as a flowchart"
"Using imperative verbs: Connect, Measure, Apply, Calculate, Observe, Record..."
```

**Change To:**
```
"extract the main conceptual STAGES that explain this process"
"Using explanation verbs: Absorb, Split, Produce, Release, Convert, Transfer..."
```

**New Allowed Verbs (Educational, Not Procedural):**
- Absorb, Release, Produce, Convert, Transfer, Create, Break, Split, Combine
- Capture, Store, Transport, Transform, Generate, Conduct, Form

**New Prompt Design:**
Instead of: "Connect Battery ⚡"  
Use: "Absorb Sunlight ☀️"

Instead of: "Measure Voltage 📊"  
Use: "Split Water 💧"

Instead of: "Record Data 📝"  
Use: "Produce Glucose 🍬"

---

## FILES RESPONSIBLE

### File 1: `services/visual_service.py`

**Location:** Lines ~407-463  
**Variable:** `_FLOWCHART_PROMPT`  
**Function:** `_extract_flowchart_structure(text)`  

**Issue:** Prompt is designed for procedural processes (experiments), not conceptual processes (explanations)

**Fix Required:** Rewrite prompt to request conceptual explanation steps instead of procedural steps

---

## SUMMARY TABLE

| Phase | Component | Status | Root Cause | Fix Required |
|-------|-----------|--------|------------|--------------|
| 1 | Topic Detection | ✓ | N/A | None |
| 2 | Concept Extraction (Stage 1) | ✓ | N/A | None |
| 3 | Ranking & Dedup (Stage 2) | ✓ | N/A | None |
| 4 | Mind Map Building (Stage 3) | ✓ | N/A | None |
| **5** | **Flowchart Extraction** | **❌** | **Procedural prompt** | **Rewrite prompt** |
| 6 | Rendering (PIL/Graphviz) | ✓ | N/A | None (Phase 6 done) |

---

## RECOMMENDED FIX

**File:** `services/visual_service.py`  
**Lines:** 407-463  
**Variable:** `_FLOWCHART_PROMPT`

**Change:** Completely rewrite to request conceptual explanation steps instead of procedural/experimental steps

**Scope:** ~60 lines of prompt text  
**Impact:** Flowcharts will now explain concepts (e.g., Photosynthesis) instead of describing procedures

---

## NEXT STEPS

1. ✓ **Root cause identified:** `_FLOWCHART_PROMPT` is procedural, not educational
2. **Rewrite prompt** to request conceptual stages with educational verbs
3. **Test with Photosynthesis** to verify flowchart is now educational
4. **Verify no API changes** needed (prompt change is internal only)
5. **Update documentation** to explain the new flowchart approach
