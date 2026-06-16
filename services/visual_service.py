"""Visual learning generator for flowcharts, concept maps, and diagrams."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from services.diagram_generator import (
    generate_flowchart_diagram,
    generate_concept_map,
    generate_process_diagram,
    generate_mind_map,
    DiagramGenerationError,
    cleanup_old_diagrams,
)
from services.llm_router import generate_content, LLMRouterError
from services.ollama_service import clean_ollama_response

logger = logging.getLogger(__name__)


class VisualError(RuntimeError):
    """Raised when visual content generation fails."""


def generate_visual_content(text: str) -> dict[str, Any]:
    """Generate visual learning structure with PNG diagrams.
    
    Creates structured educational content with:
    - Diagram type (flowchart, concept_map, process, mind_map)
    - PNG image file path
    - Node and edge structure
    - Educational summary
    
    Args:
        text: Content to visualize
        
    Returns:
        Dict with diagram_image_path, nodes, edges, and description
        
    Raises:
        VisualError: If generation fails
    """
    if not text or not text.strip():
        raise VisualError("Text cannot be empty.")
    
    # First, get structured content from AI
    prompt = (
        "Convert this content into a visual learning structure.\n\n"
        "Return ONLY valid JSON (no markdown, no code blocks).\n\n"
        "Format:\n"
        "{\n"
        '  "title": "Topic Name",\n'
        '  "type": "flowchart or concept_map or process or mind_map",\n'
        '  "central_concept": "Main concept (for concept maps)",\n'
        '  "nodes": ["Node 1", "Node 2", "Node 3", ...],\n'
        '  "edges": [["source1", "target1"], ["source2", "target2"], ...],\n'
        '  "branches": {"Main Branch 1": ["Sub 1", "Sub 2"], ...},\n'
        '  "description": "Brief description of the concept"\n'
        "}\n\n"
        "Rules:\n"
        "- title: Clear, engaging title\n"
        "- type: One of: flowchart, concept_map, process, mind_map\n"
        "- Use educational diagrams only: flowcharts, concept maps, or process diagrams\n"
        "- Do not create network graphs or abstract graph diagrams\n"
        "- central_concept: Main topic (required for concept_map, mind_map)\n"
        "- nodes: 4-12 key concepts or steps\n"
        "- edges: List of connections [[source, target], ...]\n"
        "- branches: For mind maps - main topics with subtopics\n"
        "- description: One sentence summary\n"
        "- Return ONLY JSON, no extra text\n\n"
        f"Content:\n{text.strip()}"
    )
    
    try:
        try:
            response = generate_content(prompt)
            structured_data = _parse_visual_json(response)
        except Exception as exc:
            logger.exception("Visual JSON generation failed. Using local fallback.")
            structured_data = _fallback_visual_structure(text, exc)
        
        # Generate PNG diagram
        diagram_path = _generate_png_diagram(structured_data)
        
        # Add image path to response
        structured_data["diagram_image_path"] = diagram_path
        
        # Clean up old diagrams periodically
        cleanup_old_diagrams(keep_count=30)
        
        return structured_data
        
    except VisualError:
        raise
    except Exception as exc:
        raise VisualError(f"Visual content generation failed: {exc}") from exc


def _parse_visual_json(response: str) -> dict[str, Any]:
    """Safely parse visual content JSON from AI response.
    
    Handles:
    - JSON in markdown code blocks
    - Extra whitespace
    - Malformed JSON
    - Missing fields (provides defaults)
    
    Args:
        response: Raw response from AI
        
    Returns:
        Validated visual content dict
        
    Raises:
        VisualError: If JSON cannot be parsed
    """
    if not response or not response.strip():
        raise VisualError("Empty response from visual generator.")
    
    cleaned = clean_ollama_response(response)
    cleaned = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', cleaned).strip()
    
    # Try to find JSON object
    if "{" not in cleaned:
        raise VisualError("Response does not contain a JSON object.")
    
    # Extract JSON from response (in case there's extra text)
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    
    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        raise VisualError("Could not find valid JSON object in response.")
    
    json_str = cleaned[start_idx:end_idx + 1]
    
    json_str = _sanitize_json(json_str)
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        try:
            data = json.loads(_repair_json(json_str))
        except json.JSONDecodeError as exc:
            logger.warning("Visual JSON repair failed: %s", exc)
            raise VisualError("The visual generator returned an unclear structure.") from exc
    
    if not isinstance(data, dict):
        raise VisualError(f"Expected JSON object, got {type(data).__name__}")
    
    # Validate and normalize structure
    title = (data.get("title") or "Visual Summary").strip()
    visual_type = (data.get("type") or "flowchart").strip().lower()
    visual_type = visual_type.replace(" ", "_").replace("-", "_")
    if visual_type in {"network", "graph", "network_graph", "diagram"}:
        visual_type = "concept_map"
    if visual_type not in {"flowchart", "concept_map", "process", "mind_map"}:
        visual_type = "flowchart"
    description = (data.get("description") or "").strip()
    central_concept = (data.get("central_concept") or "").strip()
    
    # Parse nodes
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        nodes = []
    nodes = [str(n).strip() for n in nodes if n and str(n).strip()][:12]
    
    # Parse edges
    edges = data.get("edges", [])
    if not isinstance(edges, list):
        edges = []
    
    # Validate edges (should be [source, target] pairs)
    valid_edges = []
    for edge in edges:
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            source = str(edge[0]).strip()
            target = str(edge[1]).strip()
            if source and target:
                valid_edges.append([source, target])
    edges = valid_edges[:15]
    
    # Parse branches (for mind maps)
    branches = data.get("branches", {})
    if not isinstance(branches, dict):
        branches = {}
    branches = {
        str(branch).strip(): [str(item).strip() for item in items[:5] if str(item).strip()]
        for branch, items in branches.items()
        if isinstance(items, list) and str(branch).strip()
    }
    
    # Ensure nodes exist
    if not nodes:
        nodes = [description] if description else ["Main Topic"]
    
    return {
        "title": title,
        "type": visual_type,
        "central_concept": central_concept,
        "nodes": nodes,
        "edges": edges,
        "branches": branches,
        "description": description,
    }


def _sanitize_json(json_str: str) -> str:
    json_str = json_str.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    json_str = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", " ", json_str)
    return re.sub(r"\s+", " ", json_str).strip()


def _repair_json(json_str: str) -> str:
    repaired = json_str.replace("“", '"').replace("”", '"').replace("’", "'")
    repaired = re.sub(
        r'([{,]\s*)(title|type|central_concept|nodes|edges|branches|description)(\s*:)',
        r'\1"\2"\3',
        repaired,
    )
    repaired = re.sub(r",\s*}", "}", repaired)
    repaired = re.sub(r",\s*\]", "]", repaired)
    return repaired


def _fallback_visual_structure(text: str, exc: Exception) -> dict[str, Any]:
    sentences = [
        sentence.strip(" .")
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text.strip())
        if sentence.strip()
    ]
    nodes = [sentence[:70] for sentence in sentences[:8]]
    if not nodes:
        nodes = ["Read the topic", "Find key ideas", "Connect the ideas", "Review the learning"]
    edges = [[nodes[index], nodes[index + 1]] for index in range(len(nodes) - 1)]
    return {
        "title": "Visual Learning Summary",
        "type": "process",
        "central_concept": nodes[0],
        "nodes": nodes,
        "edges": edges,
        "branches": {},
        "description": "A simple step-by-step visual summary was created from the text.",
    }


def _generate_png_diagram(visual_data: dict[str, Any]) -> str:
    """Generate PNG diagram based on visual content structure.
    
    Args:
        visual_data: Structured visual content dict
        
    Returns:
        Path to generated PNG file
        
    Raises:
        VisualError: If diagram generation fails
    """
    try:
        title = visual_data.get("title", "Diagram")
        diagram_type = visual_data.get("type", "flowchart")
        nodes = visual_data.get("nodes", [])
        edges = visual_data.get("edges", [])
        branches = visual_data.get("branches", {})
        central_concept = visual_data.get("central_concept", title)
        
        # Generate appropriate diagram type
        if diagram_type == "concept_map":
            return generate_concept_map(
                title=title,
                central_concept=central_concept,
                concepts=nodes,
                edges=[(e[0], e[1], "") for e in edges[:15]],
            )
        
        elif diagram_type == "mind_map":
            return generate_mind_map(
                title=title,
                central_idea=central_concept,
                branches=branches or {title: nodes[:5]},
            )
        
        elif diagram_type == "process":
            return generate_process_diagram(
                title=title,
                steps=nodes,
                connections=[(e[0], e[1]) for e in edges[:15]],
            )
        
        else:  # Default to flowchart
            return generate_flowchart_diagram(
                title=title,
                nodes=nodes,
                edges=[(e[0], e[1]) for e in edges[:15]],
            )
    
    except DiagramGenerationError as exc:
        raise VisualError(f"PNG diagram generation failed: {str(exc)}") from exc
    except Exception as exc:
        raise VisualError(f"PNG diagram generation failed: {str(exc)}") from exc
