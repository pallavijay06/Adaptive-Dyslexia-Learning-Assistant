"""Visual learning generator focused on Flowcharts and Mind Maps.

Produces emoji-first visuals designed for quick visual learning
and dyslexia-friendly readability: short labels, large spacing,
diagram structure, and extensive emoji use.
"""

from __future__ import annotations

import json
import logging
import re
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
            mindmap_path = _generate_mindmap(
                structure.get("title", "Concept"),
                structure.get("inputs", []) + structure.get("outputs", []) + structure.get("steps", []),
                theme,
            )

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


def _extract_visual_structure(text: str) -> dict[str, Any]:
    """Extract visual structure (concepts, steps, inputs, outputs) from text.
    
    Args:
        text: Content to analyze
        
    Returns:
        Dict with title, description, steps, inputs, outputs, key_component
    """
    prompt = (
        "Analyze this educational content and extract a compact visual structure for two outputs:"
        " a Flowchart (sequential steps) and a Mind Map (central concept + related nodes).\n\n"
        "Return ONLY valid JSON (no markdown, no code blocks).\n\n"
        "Format:\n"
        "{\n"
        '  "title": "Topic Title",\n'
        '  "description": "One short sentence (<=12 words)",\n'
        '  "steps": ["short step label 1", "step 2", ...],\n'
        '  "inputs": ["short label"],\n'
        '  "outputs": ["short label"],\n'
        '  "related": ["node1", "node2", "node3"]\n'
        "}\n\n"
        "Rules:\n"
        "- Use emojis for key concepts when possible (emoji + short label).\n"
        "- Keep labels very short (1-4 words).\n"
        "- Prefer visual structure: steps (flow), related nodes (mind map).\n"
        "- Minimize text; use hierarchy and short labels.\n"
        "- Make outputs dyslexia-friendly: short labels, wide spacing.\n"
        "- Return ONLY JSON.\n\n"
        f"Content:\n{text.strip()[:2000]}"
    )
    
    try:
        response = generate_content(prompt)
        structure = _parse_json_response(response)
        
        # Validate structure
        if not structure.get("steps"):
            structure["steps"] = _fallback_steps_from_text(text)
        if not structure.get("inputs"):
            structure["inputs"] = ["Input/Resource 1", "Input/Resource 2"]
        if not structure.get("outputs"):
            structure["outputs"] = ["Output/Result 1", "Output/Result 2"]
        if not structure.get("title"):
            structure["title"] = "Learning Concept"
            
        return structure
        
    except Exception as exc:
        logger.warning("Structure extraction failed, using fallback: %s", exc)
        return _fallback_visual_structure(text)


def _parse_json_response(response: str) -> dict[str, Any]:
    """Safely parse JSON from AI response."""
    if not response or not response.strip():
        return {}
    
    # Clean response
    cleaned = clean_ollama_response(response)
    cleaned = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', cleaned).strip()
    
    # Extract JSON
    if "{" not in cleaned:
        return {}
    
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    
    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        return {}
    
    json_str = cleaned[start_idx:end_idx + 1]
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning("JSON parsing failed")
        return {}


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


def _generate_mindmap(title: str, nodes: list[str], theme: str) -> str:
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
