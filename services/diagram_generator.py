"""Educational diagram generator for visual learning."""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path

from graphviz import Digraph


class DiagramGenerationError(RuntimeError):
    """Raised when diagram generation fails."""


DIAGRAM_FOLDER = "generated_diagrams"

# Create diagram folder if it doesn't exist
Path(DIAGRAM_FOLDER).mkdir(parents=True, exist_ok=True)


def generate_flowchart_diagram(
    title: str,
    nodes: list[str],
    edges: list[tuple[str, str]],
) -> str:
    """Generate a flowchart diagram using Graphviz and save as PNG.
    
    Args:
        title: Flowchart title
        nodes: List of node labels
        edges: List of (source, target) tuples representing connections
        
    Returns:
        Path to generated PNG file
        
    Raises:
        DiagramGenerationError: If diagram generation fails
    """
    if not title or not nodes:
        raise DiagramGenerationError("Title and nodes are required.")
    
    try:
        # Create a new Graphviz digraph
        graph = Digraph(
            name=f"flowchart_{uuid.uuid4().hex[:8]}",
            format="png",
            engine="dot",
        )
        
        graph.attr(
            rankdir="TB",  # Top to Bottom
            margin="0.5",
            pad="0.5",
            nodesep="0.5",
            ranksep="1.0",
        )
        
        # Style settings
        graph.attr("node", shape="box", style="rounded,filled", fillcolor="#e8f4f8", fontname="Arial")
        graph.attr("edge", arrowsize="1.5", color="#2e7d32", fontname="Arial")
        
        # Add nodes with styling
        for node in nodes[:15]:  # Limit to 15 nodes
            # Wrap long text
            wrapped = wrap_text(str(node), 20)
            graph.node(node, label=wrapped, fontsize="11", color="#1976d2")
        
        # Add edges (connections)
        for source, target in edges[:20]:  # Limit to 20 edges
            if source in nodes and target in nodes:
                graph.edge(str(source), str(target), label="", color="#388e3c")
        
        # Save diagram
        filename = f"flowchart_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(DIAGRAM_FOLDER, filename)
        
        # Render and save
        graph.render(filepath.replace(".png", ""), view=False, quiet=True, cleanup=True)
        
        if not os.path.exists(filepath):
            raise DiagramGenerationError(f"Flowchart PNG not created: {filepath}")
        
        return filepath
    
    except DiagramGenerationError:
        raise
    except Exception as exc:
        raise DiagramGenerationError(f"Flowchart generation failed: {exc}") from exc


def generate_concept_map(
    title: str,
    central_concept: str,
    concepts: list[str],
    edges: list[tuple[str, str, str]],
) -> str:
    """Generate a structured educational concept map using Graphviz.
    
    Args:
        title: Map title
        central_concept: Central concept (root node)
        concepts: List of related concepts
        edges: List of (source, target, label) tuples
        
    Returns:
        Path to generated PNG file
        
    Raises:
        DiagramGenerationError: If generation fails
    """
    if not title or not central_concept:
        raise DiagramGenerationError("Title and central concept are required.")
    
    try:
        graph = Digraph(
            name=f"conceptmap_{uuid.uuid4().hex[:8]}",
            format="png",
            engine="dot",
        )

        graph.attr(
            rankdir="TB",
            margin="0.5",
            pad="0.5",
            nodesep="0.6",
            ranksep="0.9",
            label=title,
            labelloc="t",
            fontsize="18",
            fontname="Arial",
        )
        graph.attr("edge", color="#546e7a", arrowsize="0.9", fontname="Arial", fontsize="10")

        graph.node(
            "center",
            label=wrap_text(central_concept, 22),
            shape="box",
            style="rounded,filled",
            fillcolor="#0f766e",
            fontcolor="white",
            color="#0f766e",
            fontsize="14",
            fontname="Arial",
        )

        node_ids: dict[str, str] = {central_concept: "center"}
        for index, concept in enumerate(concepts[:10]):
            node_id = f"concept{index}"
            node_ids[str(concept)] = node_id
            graph.node(
                node_id,
                label=wrap_text(str(concept), 18),
                shape="note",
                style="filled",
                fillcolor="#ecfeff",
                color="#0891b2",
                fontcolor="#111827",
                fontsize="11",
                fontname="Arial",
            )
            graph.edge("center", node_id, label="connects to")

        for source, target, label in edges[:15]:
            source_id = node_ids.get(str(source))
            target_id = node_ids.get(str(target))
            if source_id and target_id and source_id != target_id:
                graph.edge(source_id, target_id, label=wrap_text(str(label), 12) if label else "")

        filename = f"conceptmap_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(DIAGRAM_FOLDER, filename)
        graph.render(filepath.replace(".png", ""), view=False, quiet=True, cleanup=True)
        
        if not os.path.exists(filepath):
            raise DiagramGenerationError(f"Concept map PNG not created: {filepath}")
        
        return filepath
    
    except DiagramGenerationError:
        raise
    except Exception as exc:
        raise DiagramGenerationError(f"Concept map generation failed: {exc}") from exc


def generate_process_diagram(
    title: str,
    steps: list[str],
    connections: list[tuple[str, str]],
) -> str:
    """Generate a process/workflow diagram using Graphviz.
    
    Args:
        title: Process title
        steps: List of process steps in order
        connections: List of (source, target) tuples
        
    Returns:
        Path to generated PNG file
        
    Raises:
        DiagramGenerationError: If generation fails
    """
    if not title or not steps:
        raise DiagramGenerationError("Title and steps are required.")
    
    try:
        graph = Digraph(
            name=f"process_{uuid.uuid4().hex[:8]}",
            format="png",
            engine="dot",
        )
        
        graph.attr(
            rankdir="LR",  # Left to Right
            margin="0.5",
            pad="0.5",
            nodesep="0.5",
            ranksep="1.5",
        )
        
        # Style for process steps
        graph.attr(
            "node",
            shape="box",
            style="filled",
            fillcolor="#fff8e1",
            fontname="Arial",
            fontsize="11",
        )
        graph.attr("edge", arrowsize="1.5", color="#f57c00", fontname="Arial")
        
        # Add nodes
        for i, step in enumerate(steps[:10]):  # Limit to 10 steps
            wrapped = wrap_text(str(step), 15)
            graph.node(f"step{i}", label=wrapped, color="#ff6f00")
        
        # Add edges - if connections not provided, create sequential
        if connections:
            for source, target in connections[:15]:
                source_index = steps.index(source) if source in steps else None
                target_index = steps.index(target) if target in steps else None
                if source_index is not None and target_index is not None:
                    graph.edge(f"step{source_index}", f"step{target_index}")
        else:
            # Sequential connections
            for i in range(len(steps) - 1):
                graph.edge(f"step{i}", f"step{i+1}")
        
        # Save
        filename = f"process_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(DIAGRAM_FOLDER, filename)
        
        graph.render(filepath.replace(".png", ""), view=False, quiet=True, cleanup=True)
        
        if not os.path.exists(filepath):
            raise DiagramGenerationError(f"Process diagram PNG not created: {filepath}")
        
        return filepath
    
    except DiagramGenerationError:
        raise
    except Exception as exc:
        raise DiagramGenerationError(f"Process diagram generation failed: {exc}") from exc


def generate_mind_map(
    title: str,
    central_idea: str,
    branches: dict[str, list[str]],
) -> str:
    """Generate a mind map diagram using Graphviz.
    
    Args:
        title: Mind map title
        central_idea: Central concept
        branches: Dict mapping main branches to sub-concepts
        
    Returns:
        Path to generated PNG file
        
    Raises:
        DiagramGenerationError: If generation fails
    """
    if not title or not central_idea:
        raise DiagramGenerationError("Title and central idea are required.")
    
    try:
        graph = Digraph(
            name=f"mindmap_{uuid.uuid4().hex[:8]}",
            format="png",
            engine="dot",
        )
        
        graph.attr(
            rankdir="LR",
            margin="1",
            pad="1",
            nodesep="1",
            ranksep="2",
        )
        
        # Central node
        graph.node(
            "center",
            label=wrap_text(central_idea, 20),
            shape="ellipse",
            style="filled",
            fillcolor="#1976d2",
            fontcolor="white",
            fontsize="13",
            fontname="Arial",
            fontweight="bold",
        )
        
        # Add branches
        for branch_idx, (branch_name, sub_items) in enumerate(list(branches.items())[:5]):
            branch_id = f"branch{branch_idx}"
            
            # Branch node
            graph.node(
                branch_id,
                label=wrap_text(branch_name, 15),
                shape="box",
                style="filled",
                fillcolor="#4caf50",
                fontcolor="white",
                fontsize="11",
                fontname="Arial",
            )
            
            graph.edge("center", branch_id, color="#1976d2", penwidth="2")
            
            # Sub-items
            for item_idx, item in enumerate(sub_items[:4]):
                item_id = f"branch{branch_idx}_item{item_idx}"
                graph.node(
                    item_id,
                    label=wrap_text(item, 12),
                    shape="ellipse",
                    style="filled",
                    fillcolor="#ffc107",
                    fontsize="10",
                    fontname="Arial",
                )
                graph.edge(branch_id, item_id, color="#4caf50")
        
        # Save
        filename = f"mindmap_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(DIAGRAM_FOLDER, filename)
        
        graph.render(filepath.replace(".png", ""), view=False, quiet=True, cleanup=True)
        
        if not os.path.exists(filepath):
            raise DiagramGenerationError(f"Mind map PNG not created: {filepath}")
        
        return filepath
    
    except DiagramGenerationError:
        raise
    except Exception as exc:
        raise DiagramGenerationError(f"Mind map generation failed: {exc}") from exc


def wrap_text(text: str, max_width: int = 20) -> str:
    """Wrap text to specified width for diagram labels.
    
    Args:
        text: Text to wrap
        max_width: Maximum characters per line
        
    Returns:
        Wrapped text with newlines
    """
    if len(text) <= max_width:
        return text
    
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        if len(" ".join(current_line + [word])) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(" ".join(current_line))
    
    return "\n".join(lines)


def cleanup_old_diagrams(keep_count: int = 30) -> None:
    """Clean up old diagram files, keeping only the most recent.
    
    Args:
        keep_count: Number of recent files to keep
    """
    try:
        diagram_folder = Path(DIAGRAM_FOLDER)
        if not diagram_folder.exists():
            return
        
        png_files = sorted(
            diagram_folder.glob("*.png"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if len(png_files) > keep_count:
            for old_file in png_files[keep_count:]:
                try:
                    old_file.unlink()
                except Exception as exc:
                    print(f"Warning: Could not delete {old_file}: {exc}")
    except Exception as exc:
        print(f"Warning: Diagram cleanup failed: {exc}")
