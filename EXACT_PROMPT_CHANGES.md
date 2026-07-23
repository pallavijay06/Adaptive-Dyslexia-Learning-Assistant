# EXACT PROMPT CHANGES - Before and After

## Location
**File:** `services/visual_service.py`  
**Lines:** 407-463  
**Variable:** `_FLOWCHART_PROMPT`

---

## THE OLD PROMPT (BROKEN)

```python
_FLOWCHART_PROMPT = """\
Read the document below and extract the main sequential process as a flowchart.
Return ONLY valid JSON. No markdown, no explanation.
Format:
{
  "title": "Topic name (2-4 words)",
  "description": "One sentence, max 12 words",
  "steps": ["Action Verb + Object", "Action Verb + Object"],
  "inputs": [{"text": "label", "emoji": "🔣"}],
  "outputs": [{"text": "label", "emoji": "🔣"}]
}

CRITICAL STEP RULES (strictly enforced):
- Each step MUST be EXACTLY ONE ACTION: imperative verb + direct object.
- Maximum 5–8 words per step. NEVER write a full sentence or explanation.
- Start with a strong action verb from: Connect, Measure, Apply, Calculate, Observe, Record, Compare, Insert, Remove, Turn, Check, Find, Identify, Mark, Count.
- CORRECT EXAMPLES (textbook quality):
  ✓ "Connect Battery"
  ✓ "Measure Voltage"
  ✓ "Turn Switch On"
  ✓ "Observe Current"
  ✓ "Calculate Resistance"
  ✓ "Record Data"
  ✓ "Compare Results"
- BANNED PATTERNS (these are TOO LONG or explanatory):
  ✗ "Connect the battery to the resistor and observe..."  (full explanation)
  ✗ "Measure the voltage across the resistor using..."    (explanatory)
  ✗ "By applying Ohm's law, calculate the current..."     (explanatory)
  ✗ "Note how the current decreases as resistance..."     (narrative)
- Step count: 4–8 steps exactly. Never more, never fewer.
- EMOJI RULES:
  - Add one relevant emoji to each step (e.g., "Connect Battery ⚡", "Measure Voltage 📊")
  - Choose from: ⚡ ⚙️ 🔌 📊 📝 ✅ 🎯 🔍 🔧 📥 📤

Document:
"""
```

### Problems with This Prompt

| Problem | Impact |
|---------|--------|
| "main sequential PROCESS" | Suggests procedure, not concept explanation |
| Imperative verbs (Connect, Measure) | Lab instruction verbs, not concept verbs |
| "EXACTLY ONE ACTION" | Sounds like lab steps, not concept stages |
| Examples (Connect Battery, Measure Voltage) | Lab procedures, not educational content |
| Lab emoji (⚡ ⚙️ 🔌 📊) | Lab equipment, not educational concepts |
| No explicit prohibition | Allows LLM to generate lab procedures |

---

## THE NEW PROMPT (FIXED)

```python
_FLOWCHART_PROMPT = """\
Read the document below and extract the main conceptual STAGES that explain this topic.
Return ONLY valid JSON. No markdown, no explanation.

IMPORTANT: This is for EDUCATIONAL EXPLANATION, not procedural instructions.
Extract the key stages that help a student understand the topic,
NOT a procedure for doing an experiment.

Format:
{
  "title": "Topic name (2-4 words)",
  "description": "One sentence, max 12 words",
  "steps": ["Educational verb + object describing key stage", ...],
  "inputs": [{"text": "label", "emoji": "🔣"}],
  "outputs": [{"text": "label", "emoji": "🔣"}]
}

CRITICAL STAGE RULES (strictly enforced):
- Each step MUST describe a CONCEPTUAL STAGE or KEY PHASE.
- Maximum 5–8 words per step.
- Start with an educational verb describing what HAPPENS, not what you DO:
  Absorb, Release, Produce, Convert, Transfer, Create, Break, Split, Combine,
  Capture, Store, Transport, Transform, Generate, Conduct, Form, Dissolve,
  Enter, Exit, Flow, Move, Travel, Build, Decompose, React.
- CORRECT EXAMPLES (concept explanation):
  ✓ "Sunlight is Absorbed"
  ✓ "Water Molecules Split"
  ✓ "Glucose is Produced"
  ✓ "Oxygen is Released"
  ✓ "Electron Transport Occurs"
  ✓ "ATP is Created"
  ✓ "Carbon Dioxide Combines"
  ✓ "Light Energy Converts"
  ✓ "Hydrogen Ions Flow"
- BANNED PATTERNS (procedural, not educational):
  ✗ "Connect the battery..."         (lab procedure)
  ✗ "Measure the voltage..."        (measurement instruction)
  ✗ "Turn the switch on..."         (equipment manipulation)
  ✗ "Record the data..."            (data collection)
  ✗ "Observe the result..."         (observation instruction)
  ✗ "Set up the apparatus..."       (lab setup)
- Step count: 4–8 steps exactly. Never more, never fewer.
- EMOJI RULES:
  - Add one relevant emoji to each step
  - Choose from: ☀️ 💧 🌿 🍬 💨 ⚡ 🔄 🌊 ♻️ 🧪 ⚛️ 🔬

Document:
"""
```

### Improvements in This Prompt

| Improvement | Impact |
|-------------|--------|
| "conceptual STAGES that explain" | Crystal clear: we want concept explanation |
| "EDUCATIONAL EXPLANATION, not procedural" | Explicit intent stated upfront |
| "what HAPPENS, not what you DO" | Distinguishes description from instruction |
| Educational verbs listed | Gives LLM correct verb set to use |
| Concept explanation examples | Shows LLM what output should look like |
| "BANNED PATTERNS" section | Explicitly prohibits procedural steps |
| Educational emoji (☀️ 💧 🌿) | Uses educational concept symbols |

---

## LINE-BY-LINE COMPARISON

### Line 407-408
```
OLD: Read the document below and extract the main sequential process as a flowchart.
NEW: Read the document below and extract the main conceptual STAGES that explain this topic.
     
     IMPORTANT: This is for EDUCATIONAL EXPLANATION, not procedural instructions.
     Extract the key stages that help a student understand the topic,
     NOT a procedure for doing an experiment.

CHANGE: Added "conceptual" and "STAGES that explain" + added 4-line intent clarification
```

### Line 420
```
OLD: "steps": ["Action Verb + Object", "Action Verb + Object"],
NEW: "steps": ["Educational verb + object describing key stage", ...],

CHANGE: Clarified steps should be "Educational verb" not just "Action Verb"
```

### Line 425
```
OLD: CRITICAL STEP RULES (strictly enforced):
NEW: CRITICAL STAGE RULES (strictly enforced):

CHANGE: Changed "STEP" to "STAGE" - emphasizes we want concept stages, not action steps
```

### Line 426
```
OLD: - Each step MUST be EXACTLY ONE ACTION: imperative verb + direct object.
NEW: - Each step MUST describe a CONCEPTUAL STAGE or KEY PHASE.

CHANGE: Changed from "ACTION" to "CONCEPTUAL STAGE" - key change in intent
```

### Line 428
```
OLD: Start with a strong action verb from: Connect, Measure, Apply, Calculate, Observe, Record, Compare, Insert, Remove, Turn, Check, Find, Identify, Mark, Count.
NEW: Start with an educational verb describing what HAPPENS, not what you DO:
     Absorb, Release, Produce, Convert, Transfer, Create, Break, Split, Combine,
     Capture, Store, Transport, Transform, Generate, Conduct, Form, Dissolve,
     Enter, Exit, Flow, Move, Travel, Build, Decompose, React.

CHANGE: Complete replacement of verb set - from lab verbs to educational verbs
```

### Lines 431-442
```
OLD: - CORRECT EXAMPLES (textbook quality):
       ✓ "Connect Battery"
       ✓ "Measure Voltage"
       ✓ "Turn Switch On"
       ✓ "Observe Current"
       ✓ "Calculate Resistance"
       ✓ "Record Data"
       ✓ "Compare Results"

NEW: - CORRECT EXAMPLES (concept explanation):
       ✓ "Sunlight is Absorbed"
       ✓ "Water Molecules Split"
       ✓ "Glucose is Produced"
       ✓ "Oxygen is Released"
       ✓ "Electron Transport Occurs"
       ✓ "ATP is Created"
       ✓ "Carbon Dioxide Combines"
       ✓ "Light Energy Converts"
       ✓ "Hydrogen Ions Flow"

CHANGE: Complete example replacement - from lab procedures to concept explanations
```

### Lines 443-449 (NEW SECTION)
```
NEW: - BANNED PATTERNS (procedural, not educational):
       ✗ "Connect the battery..."         (lab procedure)
       ✗ "Measure the voltage..."        (measurement instruction)
       ✗ "Turn the switch on..."         (equipment manipulation)
       ✗ "Record the data..."            (data collection)
       ✗ "Observe the result..."         (observation instruction)
       ✗ "Set up the apparatus..."       (lab setup)

CHANGE: Added entirely new section - explicit prohibition of procedural patterns
```

### Lines 456-457
```
OLD: - EMOJI RULES:
       - Add one relevant emoji to each step (e.g., "Connect Battery ⚡", "Measure Voltage 📊")
       - Choose from: ⚡ ⚙️ 🔌 📊 📝 ✅ 🎯 🔍 🔧 📥 📤

NEW: - EMOJI RULES:
       - Add one relevant emoji to each step
       - Choose from: ☀️ 💧 🌿 🍬 💨 ⚡ 🔄 🌊 ♻️ 🧪 ⚛️ 🔬

CHANGE: Updated emoji set from lab equipment (⚙️ 🔌 📊) to educational concepts (☀️ 💧 🌿)
```

---

## Summary of All Changes

| Type | Removed | Added |
|------|---------|-------|
| **Intent** | "sequential process" | "conceptual STAGES that explain" |
| **Clarity** | None | "IMPORTANT: This is for EDUCATIONAL EXPLANATION" |
| **Verbs** | Connect, Measure, Apply, Calculate, Observe, Record, Compare, Insert, Remove, Turn, Check, Find, Identify, Mark, Count | Absorb, Release, Produce, Convert, Transfer, Create, Break, Split, Combine, Capture, Store, Transport, Transform, Generate, Conduct, Form, Dissolve, Enter, Exit, Flow, Move, Travel, Build, Decompose, React |
| **Examples** | "Connect Battery", "Measure Voltage", "Record Data" | "Sunlight is Absorbed", "Water Splits", "Glucose Produced" |
| **Prohibitions** | None | "BANNED PATTERNS" section with 6 explicit examples |
| **Emoji** | ⚡ ⚙️ 🔌 📊 📝 ✅ 🎯 🔍 🔧 📥 📤 | ☀️ 💧 🌿 🍬 💨 ⚡ 🔄 🌊 ♻️ 🧪 ⚛️ 🔬 |

---

## Expected Output Changes

### Before Fix
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

### After Fix
```json
{
  "title": "Photosynthesis",
  "steps": [
    "Sunlight is Absorbed ☀️",
    "Water Molecules Split 💧",
    "Glucose is Produced 🍬",
    "Oxygen is Released 💨"
  ]
}
```

---

## Key Insight

The fix works because it changes what the LLM will interpret the task as:

**OLD:** "Extract how to perform this process" → Lab procedures  
**NEW:** "Extract the stages that explain this topic" → Concept explanation

By providing:
- Clear intent statement
- Different verb set
- Different examples
- Explicit prohibitions

The LLM now understands: **"Generate educational explanation, not lab instructions"**

---

## Verification

To verify the fix is working:

1. Generate flowchart for Photosynthesis
2. Check that steps use educational verbs: Absorb, Split, Produce, Release
3. Confirm NO lab verbs: Connect, Measure, Record, Turn
4. Verify steps explain concept (e.g., "Glucose is Produced")
5. Confirm NOT procedures (e.g., NOT "Calculate Sugar")

**Result:** Flowchart is educational and explains the concept correctly.
