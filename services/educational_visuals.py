"""Educational visual generator using Pillow for accessible learning diagrams.

Creates three types of educational visuals:
1. Educational Illustration - emoji-based flowchart-style learning diagrams
2. Process Flowchart - styled flowchart for step-by-step processes
3. Concept Summary - visual card summarizing key concepts
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = None

VISUALS_FOLDER = "generated_diagrams"
Path(VISUALS_FOLDER).mkdir(parents=True, exist_ok=True)

# Educational color schemes (high contrast, dyslexia-friendly)
COLOR_SCHEMES = {
    "light": {
        "background": "#FFFFFF",
        "text": "#111827",
        "title": "#1D4ED8",
        "box_bg": "#DBEAFE",
        "box_border": "#0C63E4",
        "accent": "#059669",
        "line": "#6366F1",
    },
    "dark": {
        "background": "#111827",
        "text": "#F3F4F6",
        "title": "#93C5FD",
        "box_bg": "#1E3A8A",
        "box_border": "#93C5FD",
        "accent": "#10B981",
        "line": "#A5F3FC",
    },
    "dyslexia_cream": {
        "background": "#FFF8F0",
        "text": "#2C1810",
        "title": "#C65911",
        "box_bg": "#FFE4CC",
        "box_border": "#E88B3F",
        "accent": "#2D5016",
        "line": "#B8860B",
    },
    "dyslexia_yellow": {
        "background": "#FFFACD",
        "text": "#1A1A00",
        "title": "#003366",
        "box_bg": "#FFFACD",
        "box_border": "#003366",
        "accent": "#006600",
        "line": "#0066CC",
    },
}

# Topic-specific emoji mappings
TOPIC_EMOJIS = {
    "photosynthesis": {"sun": "☀️", "plant": "🌿", "water": "💧", "glucose": "🍃", "oxygen": "🌬️"},
    "water_cycle": {"sun": "☀️", "evaporation": "🌊", "clouds": "☁️", "rain": "🌧️", "collection": "🌊"},
    "digestive": {"food": "🍎", "mouth": "👄", "stomach": "🫃", "nutrients": "🧠", "energy": "⚡"},
    "respiration": {"oxygen": "🫁", "glucose": "🍃", "cells": "🧬", "energy": "⚡", "co2": "💨"},
    "heart": {"heart": "❤️", "blood": "🩸", "veins": "🔴", "arteries": "🔵", "brain": "🧠"},
    "plants": {"leaf": "🍂", "roots": "🌱", "stem": "🌾", "flower": "🌸", "seeds": "🌰"},
    "ecosystem": {"sun": "☀️", "plants": "🌿", "herbivore": "🦌", "carnivore": "🦁", "decomposer": "🍄"},
    "cell": {"nucleus": "⭕", "mitochondria": "⚡", "membrane": "🔵", "cytoplasm": "💧", "ribosome": "◾"},
    "default": {"input": "⬅️", "process": "⚙️", "output": "➡️", "step": "📍", "connect": "🔗"},
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def get_topic_emojis(topic: str) -> dict[str, str]:
    """Get topic-specific emoji mappings."""
    topic_lower = topic.lower()
    for key, emojis in TOPIC_EMOJIS.items():
        if key in topic_lower or any(word in topic_lower for word in key.split("_")):
            return emojis
    return TOPIC_EMOJIS["default"]


def create_educational_illustration(
    topic: str,
    steps: list[str],
    theme: str = "light",
) -> str:
    """Create an educational illustration with emoji-based flowchart.

    Args:
        topic: Topic/title of the illustration
        steps: List of steps/concepts to visualize
        theme: Color theme (light, dark, dyslexia_cream, dyslexia_yellow)

    Returns:
        Path to generated PNG file
    """
    if theme not in COLOR_SCHEMES:
        theme = "light"

    colors = COLOR_SCHEMES[theme]
    emojis = get_topic_emojis(topic)

    # Image dimensions
    img_width = 800
    step_height = 100
    padding = 40
    img_height = len(steps) * step_height + padding * 2

    # Create image
    image = Image.new("RGB", (img_width, img_height), hex_to_rgb(colors["background"]))
    draw = ImageDraw.Draw(image)

    # Try to use better fonts, fall back to default
    try:
        title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 28)
        text_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 18)
        emoji_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 32)
    except (IOError, OSError):
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        emoji_font = ImageFont.load_default()

    # Draw title
    title_y = padding // 2
    draw.text(
        (img_width // 2, title_y),
        f"📚 {topic}",
        fill=hex_to_rgb(colors["title"]),
        font=title_font,
        anchor="mm",
    )

    # Draw steps
    y_pos = padding + 60
    for i, step in enumerate(steps[:8]):  # Limit to 8 steps
        # Get emoji for this step (cycle through available emojis)
        emoji_keys = list(emojis.keys())
        emoji_key = emoji_keys[i % len(emoji_keys)]
        emoji = emojis.get(emoji_key, "📍")

        # Draw box background
        box_padding = 15
        box_y_top = y_pos - step_height // 2
        box_y_bottom = y_pos + step_height // 2
        draw.rectangle(
            [(padding, box_y_top), (img_width - padding, box_y_bottom)],
            fill=hex_to_rgb(colors["box_bg"]),
            outline=hex_to_rgb(colors["box_border"]),
            width=3,
        )

        # Draw emoji
        draw.text(
            (padding + box_padding + 20, y_pos),
            emoji,
            fill=hex_to_rgb(colors["text"]),
            font=emoji_font,
            anchor="lm",
        )

        # Draw text
        draw.text(
            (padding + box_padding + 70, y_pos),
            step,
            fill=hex_to_rgb(colors["text"]),
            font=text_font,
            anchor="lm",
        )

        # Draw arrow between steps
        if i < len(steps) - 1:
            arrow_y = y_pos + step_height // 2 + 10
            draw.line(
                [(img_width // 2, arrow_y), (img_width // 2, arrow_y + 20)],
                fill=hex_to_rgb(colors["line"]),
                width=3,
            )
            draw.polygon(
                [
                    (img_width // 2, arrow_y + 25),
                    (img_width // 2 - 8, arrow_y + 15),
                    (img_width // 2 + 8, arrow_y + 15),
                ],
                fill=hex_to_rgb(colors["line"]),
            )

        y_pos += step_height

    # Save image
    filename = f"edu_illustration_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(VISUALS_FOLDER, filename)
    image.save(filepath)

    return filepath


def create_process_flowchart(
    title: str,
    steps: list[str],
    theme: str = "light",
) -> str:
    """Create a styled process flowchart visualization.

    Args:
        title: Flowchart title
        steps: List of process steps
        theme: Color theme

    Returns:
        Path to generated PNG file
    """
    if theme not in COLOR_SCHEMES:
        theme = "light"

    colors = COLOR_SCHEMES[theme]

    # Use graphviz if available, otherwise fallback to Pillow
    try:
        from graphviz import Digraph
        return _create_flowchart_graphviz(title, steps, colors)
    except ImportError:
        return _create_flowchart_pillow(title, steps, colors)


def _create_flowchart_graphviz(title: str, steps: list[str], colors: dict) -> str:
    """Create flowchart using Graphviz."""
    from graphviz import Digraph

    graph = Digraph(
        name=f"flowchart_{uuid.uuid4().hex[:8]}",
        format="png",
        engine="dot",
    )

    graph.attr(
        rankdir="TB",
        margin="0.5",
        pad="0.5",
        nodesep="0.8",
        ranksep="1.2",
        label=title,
        labelloc="t",
        fontsize="20",
    )

    # Node styling - educational colors
    graph.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fillcolor=colors["box_bg"],
        fontcolor=colors["text"],
        fontname="Arial",
        fontsize="14",
        penwidth="2",
        color=colors["box_border"],
    )

    # Edge styling
    graph.attr("edge", arrowsize="1.8", color=colors["line"], penwidth="2.5", fontname="Arial")

    # Add nodes
    for i, step in enumerate(steps[:12]):
        step_text = step[:50] + ("..." if len(step) > 50 else "")
        graph.node(f"step{i}", label=step_text)

    # Add sequential edges
    for i in range(len(steps) - 1):
        graph.edge(f"step{i}", f"step{i + 1}")

    # Save
    filename = f"flowchart_edu_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(VISUALS_FOLDER, filename)

    try:
        graph.render(filepath.replace(".png", ""), view=False, quiet=True, cleanup=True)
        return filepath
    except Exception as exc:
        raise RuntimeError(f"Graphviz flowchart generation failed: {exc}") from exc


def _create_flowchart_pillow(title: str, steps: list[str], colors: dict) -> str:
    """Fallback flowchart creation using Pillow."""
    img_width = 900
    box_height = 80
    padding = 50
    box_width = 250
    img_height = len(steps) * (box_height + 60) + padding * 2

    image = Image.new("RGB", (img_width, img_height), hex_to_rgb(colors["background"]))
    draw = ImageDraw.Draw(image)

    try:
        title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 26)
        text_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 16)
    except (IOError, OSError):
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Draw title
    draw.text(
        (img_width // 2, padding),
        title,
        fill=hex_to_rgb(colors["title"]),
        font=title_font,
        anchor="mm",
    )

    # Draw flowchart
    x_pos = img_width // 2 - box_width // 2
    y_pos = padding + 60

    for i, step in enumerate(steps[:10]):
        # Draw box
        draw.rectangle(
            [(x_pos, y_pos), (x_pos + box_width, y_pos + box_height)],
            fill=hex_to_rgb(colors["box_bg"]),
            outline=hex_to_rgb(colors["box_border"]),
            width=3,
        )

        # Draw text
        step_text = step[:40] + ("..." if len(step) > 40 else "")
        draw.text(
            (x_pos + box_width // 2, y_pos + box_height // 2),
            step_text,
            fill=hex_to_rgb(colors["text"]),
            font=text_font,
            anchor="mm",
        )

        # Draw arrow
        if i < len(steps) - 1:
            arrow_y = y_pos + box_height + 10
            draw.line(
                [(img_width // 2, arrow_y), (img_width // 2, arrow_y + 30)],
                fill=hex_to_rgb(colors["line"]),
                width=3,
            )
            draw.polygon(
                [
                    (img_width // 2, arrow_y + 40),
                    (img_width // 2 - 10, arrow_y + 25),
                    (img_width // 2 + 10, arrow_y + 25),
                ],
                fill=hex_to_rgb(colors["line"]),
            )

        y_pos += box_height + 60

    filename = f"flowchart_edu_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(VISUALS_FOLDER, filename)
    image.save(filepath)

    return filepath


def create_concept_summary(
    title: str,
    inputs: list[str],
    outputs: list[str],
    key_component: str = "",
    theme: str = "light",
) -> str:
    """Create a visual concept summary card.

    Args:
        title: Concept title
        inputs: List of inputs
        outputs: List of outputs
        key_component: Key component/process
        theme: Color theme

    Returns:
        Path to generated PNG file
    """
    if theme not in COLOR_SCHEMES:
        theme = "light"

    colors = COLOR_SCHEMES[theme]

    # Image dimensions
    img_width = 700
    img_height = 600
    padding = 40
    section_height = 120

    image = Image.new("RGB", (img_width, img_height), hex_to_rgb(colors["background"]))
    draw = ImageDraw.Draw(image)

    try:
        title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 24)
        section_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 16)
        item_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 14)
    except (IOError, OSError):
        title_font = ImageFont.load_default()
        section_font = ImageFont.load_default()
        item_font = ImageFont.load_default()

    y_pos = padding

    # Draw title
    draw.text(
        (img_width // 2, y_pos),
        f"🎯 {title}",
        fill=hex_to_rgb(colors["title"]),
        font=title_font,
        anchor="mm",
    )
    y_pos += 60

    # Draw Inputs section
    draw.text(
        (padding + 20, y_pos),
        "📥 INPUTS:",
        fill=hex_to_rgb(colors["accent"]),
        font=section_font,
        anchor="lm",
    )
    y_pos += 30

    for input_item in inputs[:3]:
        draw.rectangle(
            [(padding, y_pos - 12), (img_width - padding, y_pos + 12)],
            fill=hex_to_rgb(colors["box_bg"]),
            outline=hex_to_rgb(colors["box_border"]),
            width=2,
        )
        draw.text(
            (padding + 15, y_pos),
            f"• {input_item}",
            fill=hex_to_rgb(colors["text"]),
            font=item_font,
            anchor="lm",
        )
        y_pos += 28

    y_pos += 20

    # Draw Key Component
    if key_component:
        draw.text(
            (padding + 20, y_pos),
            "⚙️ KEY COMPONENT:",
            fill=hex_to_rgb(colors["accent"]),
            font=section_font,
            anchor="lm",
        )
        y_pos += 30

        # Large highlighted box for key component
        draw.rectangle(
            [(padding, y_pos - 15), (img_width - padding, y_pos + 30)],
            fill=hex_to_rgb(colors["box_bg"]),
            outline=hex_to_rgb(colors["box_border"]),
            width=3,
        )
        draw.text(
            (img_width // 2, y_pos + 7),
            key_component,
            fill=hex_to_rgb(colors["title"]),
            font=section_font,
            anchor="mm",
        )
        y_pos += 55

    y_pos += 10

    # Draw Outputs section
    draw.text(
        (padding + 20, y_pos),
        "📤 OUTPUTS:",
        fill=hex_to_rgb(colors["accent"]),
        font=section_font,
        anchor="lm",
    )
    y_pos += 30

    for output_item in outputs[:3]:
        draw.rectangle(
            [(padding, y_pos - 12), (img_width - padding, y_pos + 12)],
            fill=hex_to_rgb(colors["box_bg"]),
            outline=hex_to_rgb(colors["box_border"]),
            width=2,
        )
        draw.text(
            (padding + 15, y_pos),
            f"• {output_item}",
            fill=hex_to_rgb(colors["text"]),
            font=item_font,
            anchor="lm",
        )
        y_pos += 28

    # Save image
    filename = f"concept_summary_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(VISUALS_FOLDER, filename)
    image.save(filepath)

    return filepath


def detect_topic(text: str) -> str:
    """Detect the main topic from content text.

    Args:
        text: Content text

    Returns:
        Detected topic name
    """
    text_lower = text.lower()

    topic_keywords = {
        "photosynthesis": ["photosynthesis", "chlorophyll", "sunlight", "glucose"],
        "water_cycle": ["water cycle", "evaporation", "precipitation", "condensation"],
        "digestive": ["digestive", "stomach", "digestion", "nutrient", "enzyme"],
        "respiration": ["respiration", "cellular respiration", "glucose", "atp", "mitochondria"],
        "heart": ["heart", "cardiovascular", "blood", "circulation", "heartbeat"],
        "plants": ["plant", "leaf", "root", "photosynthesis", "stem"],
        "cell": ["cell", "nucleus", "mitochondria", "membrane", "organelle"],
        "ecosystem": ["ecosystem", "food chain", "biotic", "habitat", "organism"],
    }

    for topic, keywords in topic_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic

    return "general"
