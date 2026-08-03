"""Visual learning generator focused on Flowcharts and Mind Maps.

Produces emoji-first visuals designed for quick visual learning
and dyslexia-friendly readability: short labels, large spacing,
diagram structure, and extensive emoji use.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any

from services.educational_understanding_engine import understand_chapter
from services.educational_validation_engine import validate_educational_knowledge
from services.educational_visuals import (
    create_process_flowchart,
    create_mind_map,
    detect_topic,
)
from services.knowledge_organization_engine import organize_knowledge
from services.educational_concept_labeling_engine import label_educational_knowledge
from services.llm_router import generate_content, LLMRouterError
from services.ollama_service import clean_ollama_response
from services.visualization_planning_engine import VisualizationPlanningEngine

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
    logger.info("======== ENTERED VISUAL SERVICE ========")
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
            if _use_mindmap_v2() and structure.get("mindmap_layout_model"):
                mindmap_nodes = _layout_model_to_renderer_nodes(structure.get("mindmap_layout_model"))
                mindmap_path = _generate_mindmap(
                    structure.get("title", "Concept"),
                    mindmap_nodes,
                    theme,
                )
            else:
                branches = structure.get("branches", [])
                # Build hierarchy-aware node list: branch labels + their children
                # Each node carries a "level" key: 1 = primary concept, 2 = child detail
                mindmap_nodes: list[dict] = []
                if branches and isinstance(branches[0], dict):
                    for branch in branches:
                        label = branch.get("label", {})
                        label_node = (
                            label if isinstance(label, dict)
                            else {"text": str(label), "emoji": "📌"}
                        )
                        label_node = dict(label_node)
                        label_node["level"] = 1
                        mindmap_nodes.append(label_node)
                        children = branch.get("children", [])
                        if isinstance(children, list):
                            for child in children:
                                child_node = (
                                    child if isinstance(child, dict)
                                    else {"text": str(child), "emoji": "📍"}
                                )
                                child_node = dict(child_node)
                                child_node["level"] = 2
                                mindmap_nodes.append(child_node)
                else:
                    for item in (
                        structure.get("inputs", []) +
                        structure.get("outputs", []) +
                        structure.get("steps", [])
                    ):
                        node = (
                            item if isinstance(item, dict)
                            else {"text": str(item), "emoji": "📍"}
                        )
                        node = dict(node)
                        node.setdefault("level", 1)
                        mindmap_nodes.append(node)
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
            "mindmap_layout_model": structure.get("mindmap_layout_model"),
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
You are an experienced teacher creating an educational mind map for dyslexic learners.
Read the document carefully and identify the important study concepts a student
should remember after studying this chapter.

Do NOT perform keyword extraction.
Do NOT perform entity extraction.
Do NOT return isolated nouns, physical objects, materials, devices, examples,
locations, or random words that only appear in the text.

Think: "What are the important ideas, processes, relationships, functions,
principles, or mechanisms that belong on a textbook revision mind map?"

Output requirements:
- Return ONLY valid JSON with a top-level `title` and a `concepts` array.
- `title` should be the exact chapter or subject title inferred from the document.
- Each concept should be a short textbook-style heading suitable for a mind map branch.
- Concepts should be meaningful educational study ideas, not raw nouns.
- Use approximately 2–6 words per concept.
- Concepts may be paraphrased for clarity if they remain fully supported by the document.
- Do NOT write full sentences, explanations, definitions, examples, or lists of materials.
- Do NOT invent unsupported concepts.
- Do NOT force a fixed number of concepts; choose the number dynamically based on topic size.
- If the topic is small, return fewer concepts; if the topic is larger, return more.

Good examples:
- Purpose of Photosynthesis
- Requirements for Photosynthesis
- Role of Chlorophyll
- Light Energy Absorption
- Glucose Formation
- Oxygen Release
- Importance of Photosynthesis

Bad examples:
- Water
- Leaves
- Roots
- Stomata
- Carbon Dioxide
- Wire
- Battery
- Device

JSON format:
{
    "title": "Exact chapter or subject title",
    "concepts": [
        {"text": "Light Energy Absorption", "importance": 0.98},
        {"text": "Chlorophyll Function", "importance": 0.95}
    ]
}

Document:
"""


def _stage1_extract_concepts(text: str) -> list[dict]:
    """LLM call: extract topic title and a list of concepts (text + importance).

    Returns a list of dicts with keys: 'concept' and 'importance'.
    The LLM is only allowed to identify concepts; no sentences or explanations.
    """
    logger.info("[Stage1] Extracting concepts from document")
    prompt = _STAGE1_PROMPT + text.strip()[:3000]
    logger.info("[Stage1][PROMPT] %s", prompt[:2000])
    response = generate_content(prompt, max_tokens=800)
    cleaned = clean_ollama_response(response or "")
    logger.info("[Stage1][OUTPUT] Raw LLM response (trimmed): %s", (cleaned or "")[:2000])
    cleaned = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.warning("[Stage1] No JSON object found in response")
        return []
    try:
        parsed = json.loads(cleaned[start:end + 1])
        concepts = parsed.get("concepts", []) or []
        title = parsed.get("title", "").strip()
        logger.info("[Stage1] Title: %s | Concepts: %d", title, len(concepts))
        result: list[dict] = []
        for c in concepts:
            if not isinstance(c, dict):
                continue
            text_val = (c.get("text") or c.get("concept") or "").strip()
            try:
                importance = float(c.get("importance", 0.0))
            except Exception:
                importance = 0.0
            if not text_val:
                continue
            result.append({
                "concept": text_val,
                "importance": float(max(0.0, min(1.0, importance))),
            })
        return result
    except json.JSONDecodeError:
        logger.warning("[Stage1] JSON parse failed")
        return []


def _tokenize_text(text: str, min_length: int = 3) -> list[str]:
    """Return normalized tokens from text for support and duplicate detection."""
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9'’]+", text or "")
        if len(token) >= min_length
    ]


def _word_set(text: str) -> set[str]:
    return set(_tokenize_text(text, min_length=3))


def _is_generic_concept(candidate: dict) -> bool:
    title = str(candidate.get("concept", "")).strip()
    if not title:
        return True
    words = title.split()
    if len(words) < 3:
        return True

    lower_title = title.lower()
    generic_signals = (
        "overview", "definition", "key component", "main concept", "process", "topic",
        "description", "important", "summary", "general", "basic", "used for", "helps", "because",
        "characteristic", "function", "role", "part of", "related to"
    )
    if any(signal in lower_title for signal in generic_signals):
        return True

    return False


def _support_score(candidate: dict, source_tokens: set[str]) -> int:
    title_tokens = _word_set(candidate.get("concept", ""))
    explanation_tokens = _word_set(candidate.get("fact", ""))

    title_support = len(title_tokens & source_tokens)
    explanation_support = len(explanation_tokens & source_tokens)

    return title_support * 3 + explanation_support


def _has_document_support(candidate: dict, source_tokens: set[str]) -> bool:
    if not source_tokens:
        return True
    title_tokens = _word_set(candidate.get("concept", ""))
    if title_tokens and title_tokens & source_tokens:
        return True

    explanation_tokens = _word_set(candidate.get("fact", ""))
    if explanation_tokens and explanation_tokens & source_tokens:
        return True

    return False


def _concept_is_duplicate(candidate: dict, accepted: dict) -> bool:
    candidate_words = _word_set(candidate.get("concept", ""))
    accepted_words = _word_set(accepted.get("concept", ""))
    if not candidate_words or not accepted_words:
        return False

    overlap_ratio = len(candidate_words & accepted_words) / min(len(candidate_words), len(accepted_words))
    if overlap_ratio >= 0.65:
        return True

    candidate_explanation = _word_set(candidate.get("fact", ""))
    accepted_explanation = _word_set(accepted.get("fact", ""))
    if candidate_explanation and accepted_explanation:
        explanation_overlap = len(candidate_explanation & accepted_explanation) / max(len(candidate_explanation), len(accepted_explanation), 1)
        if explanation_overlap >= 0.75:
            return True

    return False


def _adaptive_mindmap_node_limit(text: str) -> int:
    # Deprecated: node count must not be hardcoded. Keep for compatibility but not used.
    return 9999


# ---------------------------------------------------------------------------
# Stage 2 — Rank and deduplicate (pure Python, no LLM)
# ---------------------------------------------------------------------------

def _stage2_rank_and_deduplicate(concepts: list[dict], source_text: str) -> list[dict]:
    """Validate, deduplicate, and rank concepts using pure Python.

    Validation rules:
    - 1–4 words
    - not a verb phrase or sentence fragment
    - not generic or meaningless
    - not duplicate
    - must have support in the source text (matching tokens)

    Returns a list of validated concepts (dicts with 'concept' and 'importance').
    """
    source_tokens = _word_set(source_text)
    logger.info("[Stage2][INPUT] Candidate concepts: %s", [c.get("concept") for c in concepts])

    def is_valid_text(text: str) -> bool:
        if not text or not text.strip():
            return False
        words = text.strip().split()
        if len(words) > 4:
            return False
        # Reject if it looks like a verb phrase or ends with banned verbs
        banned_endings = ("is", "means", "because", "allows", "uses", "produces", "explains", "shows", "enables")
        lower = text.strip().lower()
        for be in banned_endings:
            if lower.endswith(" " + be) or lower.endswith(" " + be + "s"):
                return False
        # Reject generic short labels (single words that are too vague)
        if len(words) == 1:
            # Allow if word appears in source tokens and is not in generic signals
            if words[0].lower() in ("overview", "definition", "process", "topic", "concept"):
                return False
        # Basic check: must share at least one token with source
        token_set = _word_set(text)
        if token_set and not (token_set & source_tokens):
            return False
        return True

    # Rank by importance (float) then lexical length
    ranked = sorted(
        concepts,
        key=lambda c: (
            float(c.get("importance", 0.0)),
            -len(_word_set(str(c.get("concept", ""))))
        ),
        reverse=True,
    )

    kept: list[dict] = []
    for candidate in ranked:
        cand_text = str(candidate.get("concept", "")).strip()
        if not is_valid_text(cand_text):
            logger.info("[Stage2] Rejected invalid or generic concept '%s'", cand_text)
            continue

        is_duplicate = False
        for accepted in kept:
            if _concept_is_duplicate(candidate, accepted):
                is_duplicate = True
                logger.info("[Stage2] Dropped duplicate '%s' (matches '%s')", cand_text, accepted.get("concept"))
                break
        if is_duplicate:
            continue

        # Keep candidate
        kept.append({"concept": cand_text, "importance": float(candidate.get("importance", 0.0))})

    logger.info("[Stage2] %d concepts after validation and deduplication", len(kept))
    logger.info("[Stage2][INPUT] %d candidate concepts", len(concepts))
    logger.info("[Stage2][OUTPUT] %d validated concepts", len(kept))
    return kept


# ---------------------------------------------------------------------------
# Stage 2.5 — Concept Refinement Engine
# ---------------------------------------------------------------------------

_CONCEPT_CATEGORY_KEYWORDS = {
    "requirements": {"requirement", "requirements", "need", "needs", "required", "input", "source", "water", "sunlight", "light", "carbon", "nutrient"},
    "products": {"product", "products", "output", "result", "formation", "production", "release", "glucose", "oxygen"},
    "process": {"process", "overview", "mechanism", "stage", "phase", "sequence", "steps"},
    "role": {"role", "function", "functions", "purpose", "importance", "effect", "relationship", "relationships"},
    "types": {"type", "types", "category", "categories", "kind", "kinds", "variation"},
}

_CATEGORY_INDICATORS = {
    "requirements": {"absorption", "entry", "requirement", "required", "need", "needs", "water", "carbon", "sunlight", "light", "nutrient", "nutrients", "gas"},
    "products": {"formation", "production", "produced", "result", "release", "output", "glucose", "oxygen", "product"},
    "process": {"process", "mechanism", "stage", "phase", "sequence", "step", "steps"},
    "role": {"role", "function", "purpose", "importance", "effect", "relationship"},
    "types": {"mitosis", "meiosis", "type", "category", "kind", "variation"},
}

_CHILD_LABEL_FILTERS = {
    "mechanism", "entry", "formation", "production", "process", "function", "role", "requirement",
    "required", "need", "needs", "purpose", "stage", "phases", "phase", "step", "steps", "type", "types",
    "category", "categories", "product", "output", "result", "release", "absorption", "generated", "produced",
    "stored", "stored", "cells", "cell", "processes", "mechanisms"
}

_WEAK_CONCEPT_INDICATORS = {
    "overview", "definition", "basic", "simple", "general", "summary", "introduction", "key", "main"
}


def _concept_category(concept: str) -> str | None:
    lower = concept.lower()
    for category, keywords in _CONCEPT_CATEGORY_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return category
    return None


def _concept_similarity(a: str, b: str) -> float:
    a_words = _word_set(a)
    b_words = _word_set(b)
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / min(len(a_words), len(b_words))


def _extract_child_label(text: str, parent_category: str | None = None) -> str:
    tokens = [t for t in _tokenize_text(text) if t not in _CONCEPT_CATEGORY_KEYWORDS.get(parent_category, set())]
    filtered = [t for t in tokens if t not in _CHILD_LABEL_FILTERS]
    if not filtered:
        filtered = tokens
    if not filtered:
        return text
    return " ".join(filtered[:3]).title()


def _is_weak_refined_concept(candidate: dict, parents: list[dict]) -> bool:
    text = str(candidate.get("concept", "")).strip().lower()
    if not text:
        return True
    if any(signal in text for signal in _WEAK_CONCEPT_INDICATORS):
        return True
    candidate_tokens = _word_set(text)
    for parent in parents:
        if _concept_similarity(text, parent.get("concept", "")) >= 0.8:
            return True
    return False


def _refine_concepts(concepts: list[dict], source_text: str) -> list[dict]:
    logger.info("[Stage2.5][RAW] Stage2 concepts: %s", [c.get("concept") for c in concepts])
    if not concepts:
        return []

    # Deduplicate again in case similar variants remain
    deduped: list[dict] = []
    for candidate in sorted(concepts, key=lambda c: float(c.get("importance", 0.0)), reverse=True):
        if any(_concept_is_duplicate(candidate, kept) for kept in deduped):
            logger.info("[Stage2.5] Removed near-duplicate '%s'", candidate.get("concept"))
            continue
        deduped.append(candidate)
    logger.info("[Stage2.5][DEDUP] Concepts: %s", [c.get("concept") for c in deduped])

    parents: list[dict] = []
    orphans: list[dict] = []
    for concept in deduped:
        if _concept_category(concept.get("concept", "")) is not None:
            parents.append(concept)
        else:
            orphans.append(concept)

    parent_children: dict[int, list[dict]] = {id(parent): [] for parent in parents}
    assigned: set[int] = set()

    for candidate in orphans:
        candidate_tokens = _word_set(candidate.get("concept", ""))
        best_parent = None
        best_score = 0.0
        for parent in parents:
            parent_category = _concept_category(parent.get("concept", ""))
            if not parent_category:
                continue
            score = _concept_similarity(parent.get("concept", ""), candidate.get("concept", ""))
            if _CATEGORY_INDICATORS.get(parent_category, set()) & candidate_tokens:
                score += 0.35
            if score <= 0.0:
                continue
            if parent.get("importance", 0.0) < candidate.get("importance", 0.0):
                score *= 0.85
            if score > best_score:
                best_score = score
                best_parent = parent

        if best_parent and best_score >= 0.25:
            parent_children[id(best_parent)].append(candidate)
            assigned.add(id(candidate))
            logger.info("[Stage2.5] Merged '%s' under '%s' (score=%.2f)", candidate.get("concept"), best_parent.get("concept"), best_score)

    refined: list[dict] = []
    for parent in parents:
        children = parent_children.get(id(parent), [])
        child_labels: list[str] = []
        for child in children:
            child_text = str(child.get("concept", "")).strip()
            if not child_text:
                continue
            child_labels.append(_compress_node_label(child_text, max_words=4))
        if child_labels:
            logger.info("[Stage2.5] Parent '%s' children: %s", parent.get("concept"), child_labels)
        refined.append({
            "concept": parent.get("concept", ""),
            "importance": float(parent.get("importance", 0.0)),
            "children": child_labels,
        })

    for candidate in deduped:
        if id(candidate) in assigned:
            continue
        if _is_weak_refined_concept(candidate, refined):
            logger.info("[Stage2.5] Removed weak concept '%s'", candidate.get("concept"))
            continue
        refined.append({
            "concept": candidate.get("concept", ""),
            "importance": float(candidate.get("importance", 0.0)),
            "children": [],
        })

    refined.sort(key=lambda c: (float(c.get("importance", 0.0)), len(c.get("children", []))), reverse=True)
    logger.info("[Stage2.5][OUTPUT] Refined concepts: %s", [c.get("concept") for c in refined])
    return refined


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


def _stage3_build_mindmap_json(title: str, concepts: list[dict], source_text: str) -> dict:
    """Build renderer-friendly mind map JSON from validated concepts.

    Each concept becomes a branch; the first child is the best supporting
    sentence extracted from the source text. Emojis are assigned heuristically.
    """
    logger.info("[Stage3] Building mind map JSON from %d concepts", len(concepts))
    logger.info("[Stage3][INPUT] Concepts: %s", [c.get("concept") for c in concepts])
    branches = []
    used_emojis: set[str] = set()

    def choose_emoji(text: str) -> str:
        mapping = [
            (("sun", "light", "solar"), "☀️"),
            (("water", "hydro", "aqueous"), "💧"),
            (("oxygen",), "💨"),
            (("glucose", "sugar", "starch"), "🍬"),
            (("voltage", "current", "resistance", "electric", "electron"), "⚡"),
            (("cell", "division", "mitosis", "meiosis"), "🧬"),
            (("atom", "molecule", "chemical"), "⚛️"),
            (("cpu", "process", "scheduling"), "⏱️"),
            (("plant", "leaf", "chlorophyll"), "🌿"),
        ]
        lower = text.lower()
        for keys, emoji in mapping:
            for k in keys:
                if k in lower:
                    if emoji not in used_emojis:
                        used_emojis.add(emoji)
                        return emoji
        pool = ["📌", "📍", "🔣", "🔬", "🧠", "🔋", "🧭", "🗂️"]
        for e in pool:
            if e not in used_emojis:
                used_emojis.add(e)
                return e
        return "📌"

    def best_supporting_sentence(concept: str) -> str:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", source_text) if s.strip()]
        if not sentences:
            return ""
        c_tokens = _word_set(concept)
        best = ""
        best_score = 0
        for s in sentences:
            s_tokens = _word_set(s)
            if not s_tokens:
                continue
            score = len(c_tokens & s_tokens)
            if score > best_score:
                best = s
                best_score = score
        return (best or sentences[0]).strip()

    for c in concepts:
        concept_text = str(c.get("concept", "")).strip()
        if not concept_text:
            continue
        emoji = choose_emoji(concept_text)
        support = best_supporting_sentence(concept_text)
        branch_children = []
        if support:
            branch_children.append({"text": support, "emoji": emoji})
        for child in c.get("children", []):
            child_text = str(child).strip()
            if child_text:
                branch_children.append({"text": child_text, "emoji": emoji})
        branch = {"label": {"text": concept_text, "emoji": emoji}, "children": branch_children}
        branches.append(branch)

    result = {"title": title, "description": "", "branches": branches}
    logger.info("[Stage3][OUTPUT] Mind map JSON (trimmed): %s", json.dumps(result, ensure_ascii=False)[:1000])
    logger.info("[Stage3] Mind map JSON built with %d branches", len(branches))
    return result


# ---------------------------------------------------------------------------
# Flowchart structure extraction (unchanged single-prompt path)
# ---------------------------------------------------------------------------

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
    """Build a visual structure from the new educational pipeline when enabled."""
    logger.info("ENTER: _extract_visual_structure at %s", datetime.utcnow().isoformat(timespec="milliseconds"))
    logger.info("[MindMap] Step 0.1 - _extract_visual_structure started")

    if _use_mindmap_v2():
        try:
            understanding = understand_chapter(text)
            knowledge_structure = organize_knowledge(understanding, text)
            labeled_structure = label_educational_knowledge(knowledge_structure)
            validated_structure = validate_educational_knowledge(labeled_structure)
            layout_model = VisualizationPlanningEngine().plan(validated_structure)
            flowchart_structure = _extract_flowchart_structure(text)
            structure: dict[str, Any] = {
                "title": layout_model.center_node.label or understanding.chapter_title,
                "description": validated_structure.learning_objective,
                "branches": [],
                "steps": flowchart_structure.get("steps") or _fallback_steps_from_text(text),
                "inputs": flowchart_structure.get("inputs", [{"text": "Input", "emoji": "📥"}]),
                "outputs": flowchart_structure.get("outputs", [{"text": "Output", "emoji": "📤"}]),
                "educational_understanding": understanding.to_dict(),
                "educational_structure": knowledge_structure.to_dict(),
                "validated_structure": validated_structure.to_dict(),
                "mindmap_layout_model": layout_model.to_dict(),
            }
            logger.info("[MindMap] Step 0.1 complete - new educational pipeline used")
            logger.info("EXIT: _extract_visual_structure at %s", datetime.utcnow().isoformat(timespec="milliseconds"))
            return structure
        except Exception as exc:
            logger.warning("New pipeline failed, using fallback structure: %s", exc)

    try:
        topic = detect_topic(text)
        educational_understanding = understand_chapter(text)

        raw_concepts = _stage1_extract_concepts(text)
        if not raw_concepts:
            logger.warning("[Stage1] No concepts extracted, using fallback")
            return _fallback_visual_structure(text)

        clean_concepts = _stage2_rank_and_deduplicate(raw_concepts, text)
        refined_concepts = _refine_concepts(clean_concepts, text)
        topic_title = topic or (refined_concepts[0]["concept"] if refined_concepts else "Learning Concept")
        mindmap_structure = _stage3_build_mindmap_json(topic_title, refined_concepts, text)
        flowchart_structure = _extract_flowchart_structure(text)

        structure = {
            "title": mindmap_structure.get("title") or flowchart_structure.get("title") or "Learning Concept",
            "description": mindmap_structure.get("description") or flowchart_structure.get("description") or "",
            "branches": mindmap_structure.get("branches", []),
            "steps": flowchart_structure.get("steps") or _fallback_steps_from_text(text),
            "inputs": flowchart_structure.get("inputs", [{"text": "Input", "emoji": "📥"}]),
            "outputs": flowchart_structure.get("outputs", [{"text": "Output", "emoji": "📤"}]),
            "educational_understanding": educational_understanding.to_dict(),
        }

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
        return create_process_flowchart(title, steps, theme)
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


# ---------------------------------------------------------------------------
# Phase 1 — Node label compression (preprocessing before rendering)
# ---------------------------------------------------------------------------

_COMPRESS_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "this", "that", "these", "those", "of", "in", "on", "at",
    "to", "for", "with", "by", "from", "as", "into", "through", "during",
    "and", "or", "but", "so", "yet", "both", "either", "neither",
    "which", "who", "whom", "whose", "where", "when", "how",
    "can", "could", "will", "would", "shall", "should", "may", "might",
    "do", "does", "did", "have", "has", "had",
    "also", "very", "just", "only", "even", "still", "already",
    "used", "called", "known", "made", "found", "given", "taken",
}


def _compress_node_label(text: str, max_words: int = 5) -> str:
    """Compress a long explanation into a short educational keyword phrase.

    Strategy:
    1. If already short enough, return as-is (title-cased).
    2. Extract nouns and important verbs; drop stop words.
    3. Preserve terminology (capitalized words, acronyms, domain terms).
    4. Result: 3–5 keyword words suitable for diagram nodes.
    
    Examples:
      "Chlorophyll is the green pigment that captures sunlight" → "Chlorophyll Captures Sunlight"
      "Current is the flow of electrical charge" → "Current Flow"
      "Resistance limits or slows electric current" → "Resistance Limits Current"
    """
    text = text.strip()
    if not text:
        return text

    words = text.split()
    if len(words) <= max_words:
        return text

    # Phase 1: categorize words by importance
    # Priority 1: Capitalized, acronyms (likely key domain terms)
    # Priority 2: Content verbs (is, has, provides, creates, flows, etc. with semantic value)
    # Priority 3: Remaining content words
    priority1: list[str] = []  # Capitalized, acronyms
    priority2: list[str] = []  # Semantically rich verbs/nouns
    priority3: list[str] = []  # Other content

    semantic_verbs = {
        "is", "are", "provides", "creates", "produces", "flows", "moves", "drives",
        "absorbs", "releases", "contains", "forms", "converts", "stores", "limits",
        "opposes", "affects", "controls", "causes", "results", "generates", "transfers"
    }

    for w in words:
        clean = w.strip(".,;:!?()[]\"'").strip()
        if not clean:
            continue
        lower = clean.lower()
        
        # Skip stop words
        if lower in _COMPRESS_STOP_WORDS:
            continue
        
        # Priority 1: Capitalized (proper nouns, domain terms)
        if clean[0].isupper() or clean.isupper():
            priority1.append(clean)
        # Priority 2: Semantic verbs + short nouns
        elif lower in semantic_verbs or (len(clean) <= 8 and clean[0].isalpha()):
            priority2.append(clean)
        # Priority 3: Other content
        else:
            priority3.append(clean)

    # Phase 2: Assemble the result
    combined = priority1 + priority2 + priority3
    if not combined:
        return " ".join(words[:max_words])

    result = " ".join(combined[:max_words])
    
    # Phase 3: Ensure at least one capital letter for readability
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    
    return result


def _compress_nodes(nodes: list[dict]) -> list[dict]:
    """Apply label compression only to level-1 branch labels (not explanation children)."""
    result = []
    for node in nodes:
        if not isinstance(node, dict):
            result.append(node)
            continue
        compressed = dict(node)
        # Level-2 nodes are full explanation sentences — never compress them.
        # Level-1 nodes are short educational titles — compress only if > max_words.
        if node.get("level", 1) == 1:
            raw_text = node.get("text", "")
            compressed["text"] = _compress_node_label(raw_text, max_words=5)
        result.append(compressed)
    return result


def _generate_mindmap(title: str, nodes: list[dict] | dict[str, Any], theme: str) -> str:
    """Generate a mind map using the educational visuals module."""
    try:
        # The renderer contract now accepts the full hierarchical layout model
        # (adapter output) or the legacy flattened node list. Pass the
        # appropriate object to `create_mind_map` and let the renderer handle
        # compatibility internally.
        if isinstance(nodes, dict):
            adapter_output = nodes
            logger.info("======== CALLING RENDERER (hierarchical model) ========")
            logger.info("[Renderer INPUT] title=%s, theme=%s, adapter_output=present", title, theme)
            path = create_mind_map(title, adapter_output, theme)
        else:
            compressed = _compress_nodes(nodes)
            logger.info("======== CALLING RENDERER (legacy nodes list) ========")
            logger.info(
                "[Renderer INPUT] title=%s, theme=%s, node_count=%d, adapter_output=none",
                title,
                theme,
                len(compressed),
            )
            path = create_mind_map(title, compressed, theme)
        logger.info("======== PNG GENERATED ======== path=%s", path)
        return path
    except Exception as exc:
        logger.error("Mind map generation failed: %s", exc)
        raise VisualError(f"Could not create mind map: {exc}") from exc


def _layout_model_to_renderer_nodes(layout_model: dict[str, Any] | None) -> dict[str, Any]:
    """Adapt the layout model into the renderer's expected node contract.

    The renderer currently consumes a list of nodes, but this adapter preserves
    the full hierarchical graph model for future renderer improvements.
    """
    if not layout_model:
        return {
            "center_node": {},
            "branch_nodes": [],
            "child_nodes": [],
            "edges": [],
            "nodes": [],
        }

    nodes: list[dict] = []
    edges: list[dict] = []

    center_node = layout_model.get("center_node", {}) or {}
    if center_node:
        nodes.append(
            {
                "text": center_node.get("label", "Concept"),
                "emoji": "🧠",
                "level": 0,
                "priority": center_node.get("priority", "highest"),
                "visual_style": center_node.get("visual_style", {}),
                "node_type": center_node.get("node_type", "center"),
                "display_label": center_node.get("display_label", center_node.get("label", "Concept")),
                "branch_order": center_node.get("branch_order"),
                "parent_id": center_node.get("parent_id"),
            }
        )

    for branch in layout_model.get("branch_nodes", []) or []:
        branch_id = branch.get("id")
        if branch_id:
            edges.append({"source": center_node.get("id", "center"), "target": branch_id, "edge_type": "branch"})

        nodes.append(
            {
                "text": branch.get("label", "Branch"),
                "emoji": "📌",
                "level": 1,
                "priority": branch.get("priority", "high"),
                "visual_style": branch.get("visual_style", {}),
                "node_type": branch.get("node_type", "branch"),
                "display_label": branch.get("display_label", branch.get("label", "Branch")),
                "branch_order": branch.get("branch_order"),
                "parent_id": branch.get("parent_id"),
            }
        )

    for child in layout_model.get("child_nodes", []) or []:
        parent_id = child.get("parent_id")
        child_id = child.get("id")
        if parent_id and child_id:
            edges.append({"source": parent_id, "target": child_id, "edge_type": "child"})

        nodes.append(
            {
                "text": child.get("label", "Child"),
                "emoji": "📍",
                "level": 2,
                "priority": child.get("priority", "medium"),
                "visual_style": child.get("visual_style", {}),
                "node_type": child.get("node_type", "child"),
                "display_label": child.get("display_label", child.get("label", "Child")),
                "branch_order": child.get("branch_order"),
                "parent_id": parent_id,
            }
        )

    return {
        "center_node": center_node,
        "branch_nodes": layout_model.get("branch_nodes", []) or [],
        "child_nodes": layout_model.get("child_nodes", []) or [],
        "edges": edges,
        "nodes": nodes,
    }


def _use_mindmap_v2() -> bool:
    return os.getenv("USE_MINDMAP_V2", "1").lower() in {"1", "true", "yes", "on"}


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
