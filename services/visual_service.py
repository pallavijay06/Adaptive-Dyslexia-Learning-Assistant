"""Visual learning generator focused on Flowcharts and Mind Maps.

Produces emoji-first visuals designed for quick visual learning
and dyslexia-friendly readability: short labels, large spacing,
diagram structure, and extensive emoji use.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from typing import Any

from services.educational_visuals import (
    create_process_flowchart,
    create_mind_map,
    detect_topic,
)
from services.llm_router import generate_content, LLMRouterError
from services.ollama_service import clean_ollama_response

logger = logging.getLogger(__name__)


class VisualError(RuntimeError):
    """Raised when visual content generation fails."""


def generate_visual_content(text: str, theme: str = "light", visual_type: str | None = None) -> dict[str, Any]:
    """Generate visual learning content for one or both supported visual types.

    Args:
        text: Source text to visualize.
        theme: Visual theme for color styling.
        visual_type: One of "flowchart", "mind_map", "mindmap", or None for both.

    Returns a dict with `flowchart_path`, `mindmap_path`, `structure`,
    `topic`, and short `description`.
    """
    logger.info("ENTER: generate_visual_content at %s", datetime.utcnow().isoformat(timespec="milliseconds"))

    if not text or not text.strip():
        raise VisualError("Text cannot be empty.")

    if isinstance(visual_type, str):
        normalized_visual_type = visual_type.strip().lower().replace("-", "_")
        if normalized_visual_type == "mindmap":
            normalized_visual_type = "mind_map"
    else:
        normalized_visual_type = None

    if normalized_visual_type not in {None, "flowchart", "mind_map"}:
        raise VisualError("Unsupported visual_type. Use 'flowchart' or 'mind_map'.")

    try:
        logger.info("[MindMap] Step 0 - generate_visual_content started")
        start_time = time.perf_counter()
        topic = detect_topic(text)
        structure = _extract_visual_structure(text)

        flowchart_path = None
        mindmap_path = None

        if normalized_visual_type in {None, "flowchart"}:
            flowchart_path = _generate_flowchart(
                structure.get("title", "Process"),
                structure.get("steps", []),
                theme,
            )

        if normalized_visual_type in {None, "mind_map"}:
            branches = structure.get("branches", [])
            mindmap_nodes: list[dict] = []
            if branches and isinstance(branches[0], dict):
                for branch in branches[:8]:
                    label = branch.get("label", {})
                    mindmap_nodes.append(
                        label if isinstance(label, dict)
                        else {"text": str(label), "emoji": "📌"}
                    )
                    for child in branch.get("children", [])[:4]:
                        mindmap_nodes.append(
                            child if isinstance(child, dict)
                            else {"text": str(child), "emoji": "📍"}
                        )
            else:
                for item in (
                    structure.get("inputs", []) +
                    structure.get("outputs", []) +
                    structure.get("steps", [])
                ):
                    mindmap_nodes.append(
                        item if isinstance(item, dict)
                        else {"text": str(item), "emoji": "📍"}
                    )
            mindmap_path = _generate_mindmap(
                structure.get("title", "Concept"),
                mindmap_nodes,
                theme,
            )

        elapsed = time.perf_counter() - start_time
        logger.info("[MindMap] Step 0 complete - generate_visual_content finished in %.4fs", elapsed)
        logger.info("EXIT: generate_visual_content at %s", datetime.utcnow().isoformat(timespec="milliseconds"))
        return {
            "topic": topic,
            "title": structure.get("title", "Visual Learning"),
            "description": structure.get("description", ""),
            "flowchart_path": flowchart_path,
            "mindmap_path": mindmap_path,
            "structure": structure,
        }

    except VisualError:
        raise
    except Exception as exc:
        logger.exception("Visual content generation failed")
        raise VisualError(f"Failed to generate educational visuals: {exc}") from exc


# ---------------------------------------------------------------------------
# Stage 1 — Educational concept extraction
# ---------------------------------------------------------------------------

_STAGE1_PROMPT = """\
You are an expert educational content designer creating revision notes for a student.
Your quality standard is Google NotebookLM concept maps.

Read the document carefully. Your output will become the nodes of a mind map.
A student must be able to understand the entire topic by reading only the mind map.

OUTPUT TWO THINGS:

1. TOPIC TITLE
   The exact chapter or subject name as it would appear in a textbook.
   Examples: "Photosynthesis", "Ohm's Law", "Binary Search", "Human Digestive System"
   NOT: "Photosynthesis Basics", "Plant Food Production", "Overview", "Main Topic"

2. TOPIC DESCRIPTION
   One or two complete sentences that explain what this topic is about.
   This will appear in the center node of the mind map.
   Example for Photosynthesis:
     "Photosynthesis is the process by which green plants make their own food
      using sunlight, water, and carbon dioxide."

3. EDUCATIONAL NODES
   Each node has two parts:
   a) "title" — a short educational statement, 4-8 words, that names the specific fact.
      It must read like a revision note heading, not a category label.
      CORRECT titles:
        ✓ "Sunlight Provides Energy"
        ✓ "Chlorophyll Absorbs Light"
        ✓ "Carbon Dioxide Is Absorbed"
        ✓ "Water Is Absorbed by Roots"
        ✓ "Glucose Is Produced"
        ✓ "Oxygen Is Released"
        ✓ "Glucose Stored as Starch"
      BANNED titles (these are labels, not facts):
        ✗ "Chlorophyll"           (single word)
        ✗ "Photosynthesis"        (topic name repeated as a node)
        ✗ "Plant Food"            (vague)
        ✗ "Definition"            (generic)
        ✗ "Process"               (generic)
        ✗ "Location"              (generic)
        ✗ "Key Component"         (generic)
        ✗ "Overview"              (generic)
        ✗ "Sunlight"              (single word)
        ✗ "Water"                 (single word)
        ✗ "Carbon Dioxide"        (single word / label)
   b) "explanation" — one or two complete sentences that teach the concept.
      Must be fully understandable without reading any other node.
      Must have an explicit subject.
      Must be factually correct and student-friendly.
      CORRECT explanations:
        ✓ "Sunlight provides the energy required to convert carbon dioxide and water into glucose."
        ✓ "Chlorophyll is the green pigment that captures sunlight inside chloroplasts."
        ✓ "Leaves absorb carbon dioxide through tiny openings called stomata."
        ✓ "Roots absorb water from the soil and transport it up to the leaves."
        ✓ "Plants convert light energy into chemical energy stored as glucose."
        ✓ "Oxygen is released into the atmosphere as a by-product of photosynthesis."
        ✓ "Glucose is stored as starch in the plant for later use as an energy source."
      BANNED explanations:
        ✗ "This process is essential for..."   (incomplete)
        ✗ "Photosynthesis is..."               (incomplete)
        ✗ "Used for..."                        (missing subject)
        ✗ "Occurs in..."                       (missing subject)
        ✗ "Responsible for..."                 (missing subject)
        ✗ "Provides..."                        (missing subject)
        ✗ "Essential for..."                   (missing subject)
        ✗ "Helps plants..."                    (vague)
        ✗ "Combines with..."                   (missing subject)
        ✗ "Produces..."                        (missing subject)
   c) "importance" — integer 1-10.
      10 = student cannot understand the topic without this node.
      Only include nodes with importance >= 6.

CONCEPT SELECTION RULES:
- Select only the most important educational concepts.
- Do NOT create filler nodes.
- Do NOT try to cover every sentence in the document.
- Do NOT repeat the same idea using different wording.
- The number of nodes depends entirely on the content.
  If six nodes explain the topic well, return six.
  If fifteen are genuinely needed, return fifteen.
  Never pad. Never truncate.

QUALITY CHECK before returning:
- Every title must be an educational statement, not a label or category.
- Every explanation must be a complete sentence with a subject.
- No duplicate ideas.
- No vague or generic nodes.
- No incomplete sentences.
- Every node must make sense when read completely alone.

Return ONLY a valid JSON object. No markdown, no explanation.
Format:
{
  "topic": "Exact chapter or subject title",
  "description": "One or two complete sentences explaining what this topic is.",
  "nodes": [
    {"title": "Short Educational Statement", "explanation": "Complete sentence teaching the concept.", "importance": 9},
    {"title": "Short Educational Statement", "explanation": "Complete sentence teaching the concept.", "importance": 8}
  ]
}

Document:
"""


def _stage1_extract_concepts(text: str) -> list[dict]:
    """LLM call 1: extract topic, description, and educational nodes from document."""
    logger.info("[Stage1] Extracting concepts from document")
    prompt = _STAGE1_PROMPT + text.strip()[:3000]
    response = generate_content(prompt, max_tokens=1400)
    cleaned = clean_ollama_response(response or "")
    cleaned = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.warning("[Stage1] No JSON object found in response")
        return []
    try:
        parsed = json.loads(cleaned[start:end + 1])
        nodes = parsed.get("nodes", [])
        topic = parsed.get("topic", "").strip()
        description = parsed.get("description", "").strip()
        logger.info("[Stage1] Topic: %s | Nodes: %d", topic, len(nodes))
        result = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            if not n.get("title") or not n.get("explanation"):
                continue
            result.append({
                "topic": topic,
                "description": description,
                "concept": n["title"],
                "fact": n["explanation"],
                "importance": int(n.get("importance", 5)),
            })
        return result
    except json.JSONDecodeError:
        logger.warning("[Stage1] JSON parse failed")
        return []


# ---------------------------------------------------------------------------
# Stage 2 — Rank and deduplicate (pure Python, no LLM)
# ---------------------------------------------------------------------------

def _stage2_rank_and_deduplicate(concepts: list[dict]) -> list[dict]:
    """Sort by importance descending, then remove near-duplicate concepts."""
    ranked = sorted(concepts, key=lambda c: int(c.get("importance", 0)), reverse=True)
    kept: list[dict] = []
    for candidate in ranked:
        name = candidate["concept"].lower()
        name_words = set(name.split())
        is_duplicate = False
        for accepted in kept:
            accepted_words = set(accepted["concept"].lower().split())
            # Overlap ratio: shared words / shorter name length
            overlap = len(name_words & accepted_words) / max(len(name_words), len(accepted_words), 1)
            if overlap >= 0.6:
                is_duplicate = True
                logger.info("[Stage2] Dropped duplicate '%s' (overlaps with '%s')", candidate["concept"], accepted["concept"])
                break
        if not is_duplicate:
            kept.append(candidate)
    logger.info("[Stage2] %d concepts after deduplication", len(kept))
    return kept


# ---------------------------------------------------------------------------
# Stage 3 — Convert curated concepts to renderer JSON
# ---------------------------------------------------------------------------

_STAGE3_PROMPT = """\
You are formatting a curated list of educational revision notes into a mind map JSON structure.
The content has already been written by a teacher. Do NOT change the meaning of any node.
Your ONLY jobs are: assign one emoji per node, and output the correct JSON.

RULES FOR "title" (center node):
- Must be the exact topic/chapter name provided.
- Examples: "Photosynthesis", "Ohm's Law", "Binary Search"
- NEVER use: "Photosynthesis Basics", "Plant Food Production", "Learning Topic", "Overview"

RULES FOR "description" (center node subtitle):
- Use the description provided verbatim.
- It must be a complete 1-2 sentence explanation of the topic.

RULES FOR branch labels:
- Use the node title exactly as provided. Do NOT shorten or rephrase.
- The label must be the educational statement title, e.g. "Chlorophyll Absorbs Light"
- NEVER reduce it to a single word like "Chlorophyll"

RULES FOR children:
- The first child must be the explanation sentence provided, verbatim or lightly cleaned.
- Add a second child ONLY if you can state a genuinely new fact not already in the explanation.
  If no new fact exists, use only one child. Do NOT invent or pad.

EMOJI RULES:
- Choose one emoji per node that visually matches the meaning.
- Do NOT reuse the same emoji for every node.
- Examples:
    "Sunlight Provides Energy"      -> ☀️
    "Chlorophyll Absorbs Light"     -> 🌿
    "Carbon Dioxide Is Absorbed"    -> 🌬️
    "Water Is Absorbed by Roots"    -> 💧
    "Glucose Is Produced"           -> 🍬
    "Oxygen Is Released"            -> 💨
    "Glucose Stored as Starch"      -> 🌾
    "Voltage Drives Current"        -> ⚡
    "Resistance Opposes Current"    -> 🔩
    "V Equals I Times R"            -> 🧮
    "Cell Division Occurs"          -> 🧬
    "CPU Scheduling"                -> ⏱️

Return ONLY valid JSON. No markdown, no explanation.
JSON format:
{
  "title": "Exact topic title",
  "description": "The provided topic description verbatim.",
  "branches": [
    {
      "label": {"text": "Node title exactly as provided", "emoji": "🔣"},
      "children": [
        {"text": "The explanation sentence verbatim", "emoji": "🔣"},
        {"text": "One genuinely new fact only if it exists", "emoji": "🔣"}
      ]
    }
  ]
}

Concepts:
"""


def _stage3_build_mindmap_json(title: str, concepts: list[dict]) -> dict:
    """LLM call 2: convert curated concept list into renderer branch JSON."""
    logger.info("[Stage3] Building mind map JSON from %d concepts", len(concepts))
    description = next((c["description"] for c in concepts if c.get("description", "").strip()), "")
    concept_lines = json.dumps(
        [
            {"title": c["concept"], "explanation": c["fact"]}
            for c in concepts
        ],
        ensure_ascii=False, indent=2
    )
    topic_block = f"Topic: {title}\nDescription: {description}\n\nNodes:\n"
    prompt = _STAGE3_PROMPT + topic_block + concept_lines
    response = generate_content(prompt, max_tokens=1400)
    cleaned = clean_ollama_response(response or "")
    cleaned = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.warning("[Stage3] No JSON object found")
        return {}
    try:
        result = json.loads(cleaned[start:end + 1])
        logger.info("[Stage3] Mind map JSON built with %d branches", len(result.get("branches", [])))
        return result
    except json.JSONDecodeError:
        logger.warning("[Stage3] JSON parse failed")
        return {}


# ---------------------------------------------------------------------------
# Flowchart structure extraction (unchanged single-prompt path)
# ---------------------------------------------------------------------------

_FLOWCHART_PROMPT = """\
Read the document below and extract the main sequential process as a flowchart.
Return ONLY valid JSON. No markdown, no explanation.
Format:
{
  "title": "Topic name (2-4 words)",
  "description": "One sentence, max 12 words",
  "steps": ["Complete step sentence.", "Complete step sentence."],
  "inputs": [{"text": "label", "emoji": "🔣"}],
  "outputs": [{"text": "label", "emoji": "🔣"}]
}
Steps: 4-8, complete sentences, plain English only.

Document:
"""


def _extract_flowchart_structure(text: str) -> dict:
    """Single-prompt extraction for flowchart steps only."""
    prompt = _FLOWCHART_PROMPT + text.strip()[:3000]
    response = generate_content(prompt, max_tokens=600)
    cleaned = clean_ollama_response(response or "")
    cleaned = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# Orchestrator — replaces the old monolithic _extract_visual_structure
# ---------------------------------------------------------------------------

def _extract_visual_structure(text: str) -> dict[str, Any]:
    """Three-stage mind map pipeline + single-stage flowchart extraction."""
    logger.info("ENTER: _extract_visual_structure at %s", datetime.utcnow().isoformat(timespec="milliseconds"))
    logger.info("[MindMap] Step 0.1 - _extract_visual_structure started")

    try:
        # ── Stage 1: extract concepts ────────────────────────────────────────
        raw_concepts = _stage1_extract_concepts(text)
        if not raw_concepts:
            logger.warning("[Stage1] No concepts extracted, using fallback")
            return _fallback_visual_structure(text)

        # ── Stage 2: rank and deduplicate ────────────────────────────────────
        clean_concepts = _stage2_rank_and_deduplicate(raw_concepts)

        # ── Stage 3: build mind map JSON ─────────────────────────────────────
        # Use the topic field from Stage 1 as the center node title.
        # Fall back to the first concept name only if topic is absent.
        topic_title = next(
            (c["topic"] for c in clean_concepts if c.get("topic", "").strip()),
            clean_concepts[0]["concept"] if clean_concepts else "Learning Concept",
        )
        mindmap_structure = _stage3_build_mindmap_json(topic_title, clean_concepts)

        # ── Flowchart: separate single-prompt extraction ──────────────────────
        flowchart_structure = _extract_flowchart_structure(text)

        # ── Merge into the shape generate_visual_content expects ─────────────
        structure: dict[str, Any] = {
            "title": mindmap_structure.get("title") or flowchart_structure.get("title") or "Learning Concept",
            "description": mindmap_structure.get("description") or flowchart_structure.get("description") or "",
            "branches": mindmap_structure.get("branches", []),
            "steps": flowchart_structure.get("steps") or _fallback_steps_from_text(text),
            "inputs": flowchart_structure.get("inputs", [{"text": "Input", "emoji": "📥"}]),
            "outputs": flowchart_structure.get("outputs", [{"text": "Output", "emoji": "📤"}]),
        }

        # ── DIAGNOSTIC ───────────────────────────────────────────────────────
        logger.info("[DIAG] RAW PARSED JSON: %s", json.dumps(structure, ensure_ascii=False))
        branches_diag = structure.get("branches", [])
        logger.info("[DIAG] NUMBER OF BRANCHES: %d", len(branches_diag))
        for _bi, _br in enumerate(branches_diag):
            _lbl = _br.get("label", {}) if isinstance(_br, dict) else _br
            _lbl_text = _lbl.get("text", str(_lbl)) if isinstance(_lbl, dict) else str(_lbl)
            logger.info("[DIAG] BRANCH %d LABEL: %s", _bi, _lbl_text)
            for _ci, _ch in enumerate(_br.get("children", []) if isinstance(_br, dict) else []):
                _ch_text = _ch.get("text", str(_ch)) if isinstance(_ch, dict) else str(_ch)
                logger.info("[DIAG] BRANCH %d CHILD %d: %s", _bi, _ci, _ch_text)
        # ── END DIAGNOSTIC ───────────────────────────────────────────────────

        logger.info("[MindMap] Step 0.1 complete - _extract_visual_structure succeeded")
        logger.info("EXIT: _extract_visual_structure at %s", datetime.utcnow().isoformat(timespec="milliseconds"))
        return structure

    except Exception as exc:
        logger.warning("Structure extraction failed, using fallback: %s", exc)
        logger.info("EXIT: _extract_visual_structure at %s", datetime.utcnow().isoformat(timespec="milliseconds"))
        return _fallback_visual_structure(text)



def _fallback_steps_from_text(text: str) -> list[str]:
    """Extract steps from text when AI extraction fails."""
    sentences = [
        s.strip(" .") 
        for s in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) 
        if s.strip()
    ]
    
    # Take first 5-6 sentences as steps
    return [s[:80] for s in sentences[:6] if s]


def _fallback_visual_structure(text: str) -> dict[str, Any]:
    """Fallback structure when everything else fails."""
    steps = _fallback_steps_from_text(text)
    
    return {
        "title": "Educational Content",
        "description": "Visual learning summary created from content",
        "steps": steps or ["Begin here", "Learn key concepts", "Understand connections", "Review summary"],
        "inputs": ["Information", "Context"],
        "outputs": ["Understanding", "Knowledge"],
        "key_component": "Learning",
    }


def _generate_illustration(topic: str, steps: list[str], theme: str) -> str:
    """Generate educational illustration.
    
    Args:
        topic: Topic name
        steps: Process steps
        theme: Color theme
        
    Returns:
        Path to generated PNG
    """
    raise VisualError("Educational illustration is removed in this build.")


def _generate_flowchart(title: str, steps: list[str], theme: str) -> str:
    """Generate process flowchart.
    
    Args:
        title: Flowchart title
        steps: Process steps
        theme: Color theme
        
    Returns:
        Path to generated PNG
    """
    try:
        return create_process_flowchart(title, steps[:10], theme)
    except Exception as exc:
        logger.error("Flowchart generation failed: %s", exc)
        raise VisualError(f"Could not create flowchart: {exc}") from exc


def _generate_summary(
    title: str,
    inputs: list[str],
    outputs: list[str],
    key_component: str,
    theme: str,
) -> str:
    """Generate concept summary card.
    
    Args:
        title: Concept title
        inputs: Input items
        outputs: Output items
        key_component: Key component/process
        theme: Color theme
        
    Returns:
        Path to generated PNG
    """
    raise VisualError("Concept Summary is removed in this build.")


def _generate_mindmap(title: str, nodes: list[dict], theme: str) -> str:
    """Generate a mind map using the educational visuals module."""
    try:
        return create_mind_map(title, nodes[:10], theme)
    except Exception as exc:
        logger.error("Mind map generation failed: %s", exc)
        raise VisualError(f"Could not create mind map: {exc}") from exc


def cleanup_old_visuals(keep_count: int = 50) -> None:
    """Clean up old visual files."""
    import os
    from pathlib import Path
    
    visuals_folder = Path("generated_diagrams")
    if not visuals_folder.exists():
        return
    
    # Get all visual files
    visual_files = sorted(
        visuals_folder.glob("*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    # Remove old ones
    for old_file in visual_files[keep_count:]:
        try:
            old_file.unlink()
        except Exception as exc:
            logger.warning("Could not delete old visual file %s: %s", old_file, exc)
