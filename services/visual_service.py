"""Educational visual learning generator - redesigned for true learning visuals.

Generates three types of educational visuals:
1. Educational Illustration (emoji-based learning flowchart)
2. Process Flowchart (step-by-step process diagram)
3. Concept Summary (visual summary of inputs/outputs/key concepts)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from services.educational_visuals import (
    create_educational_illustration,
    create_process_flowchart,
    create_concept_summary,
    detect_topic,
)
from services.llm_router import generate_content, LLMRouterError
from services.ollama_service import clean_ollama_response

logger = logging.getLogger(__name__)


class VisualError(RuntimeError):
    """Raised when visual content generation fails."""


def generate_visual_content(text: str, theme: str = "light") -> dict[str, Any]:
    """Generate three types of educational visual learning content.
    
    Creates:
    1. Educational Illustration - emoji-based learning flowchart
    2. Process Flowchart - styled step-by-step diagram
    3. Concept Summary - visual card with inputs/outputs/key concepts
    
    Args:
        text: Content to visualize
        theme: Color theme (light, dark, dyslexia_cream, dyslexia_yellow)
        
    Returns:
        Dict with:
        - topic: Detected topic
        - illustration_path: Path to illustration PNG
        - flowchart_path: Path to flowchart PNG
        - summary_path: Path to concept summary PNG
        - structure: Extracted concepts, steps, inputs, outputs
        - description: Generated summary
        
    Raises:
        VisualError: If generation fails
    """
    if not text or not text.strip():
        raise VisualError("Text cannot be empty.")
    
    try:
        # Step 1: Detect topic
        topic = detect_topic(text)
        
        # Step 2: Extract structure from AI
        structure = _extract_visual_structure(text)
        
        # Step 3: Generate three educational visuals
        illustration_path = _generate_illustration(
            topic, 
            structure.get("steps", []), 
            theme
        )
        
        flowchart_path = _generate_flowchart(
            structure.get("title", "Process"), 
            structure.get("steps", []), 
            theme
        )
        
        summary_path = _generate_summary(
            structure.get("title", "Concept"),
            structure.get("inputs", []),
            structure.get("outputs", []),
            structure.get("key_component", ""),
            theme
        )
        
        return {
            "topic": topic,
            "title": structure.get("title", "Visual Learning"),
            "description": structure.get("description", ""),
            "illustration_path": illustration_path,
            "flowchart_path": flowchart_path,
            "summary_path": summary_path,
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
        "Analyze this educational content and extract a visual learning structure.\n\n"
        "Return ONLY valid JSON (no markdown, no code blocks).\n\n"
        "Format:\n"
        "{\n"
        '  "title": "Topic Title",\n'
        '  "description": "One sentence summary",\n'
        '  "steps": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],\n'
        '  "inputs": ["Input 1", "Input 2", "Input 3"],\n'
        '  "outputs": ["Output 1", "Output 2", "Output 3"],\n'
        '  "key_component": "Most important component or process"\n'
        "}\n\n"
        "Rules:\n"
        "- title: Clear, engaging topic (4-8 words)\n"
        "- description: Single sentence explaining the concept\n"
        "- steps: 4-6 sequential steps in the process (clear, educational)\n"
        "- inputs: 2-4 main inputs/resources/raw materials\n"
        "- outputs: 2-4 main outputs/products/results\n"
        "- key_component: The central process or most important component\n"
        "- Use simple, student-friendly language\n"
        "- Return ONLY JSON, no extra text\n\n"
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
    try:
        return create_educational_illustration(topic, steps[:8], theme)
    except Exception as exc:
        logger.error("Educational illustration generation failed: %s", exc)
        raise VisualError(f"Could not create illustration: {exc}") from exc


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
    try:
        return create_concept_summary(title, inputs[:3], outputs[:3], key_component, theme)
    except Exception as exc:
        logger.error("Concept summary generation failed: %s", exc)
        raise VisualError(f"Could not create summary: {exc}") from exc


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
