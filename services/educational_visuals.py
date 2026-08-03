"""Educational visual generator using Pillow for accessible learning diagrams.

Now focused on two visual types:
- Process Flowchart (step-by-step diagram)
- Mind Map (central concept + related nodes, emoji-first)
"""

from __future__ import annotations

import logging
import math
import os
import textwrap
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

VISUALS_FOLDER = "generated_diagrams"
Path(VISUALS_FOLDER).mkdir(parents=True, exist_ok=True)

# Educational color schemes (high contrast, dyslexia-friendly)
COLOR_SCHEMES = {
    "light": {
        "background": "#F8FAFF",
        "text": "#1A1A2E",
        "title": "#1D4ED8",
        "box_bg": "#EEF2FF",
        "box_border": "#4F46E5",
        "accent": "#059669",
        "line": "#6366F1",
    },
    "dark": {
        "background": "#0F172A",
        "text": "#F1F5F9",
        "title": "#93C5FD",
        "box_bg": "#1E3A5F",
        "box_border": "#60A5FA",
        "accent": "#34D399",
        "line": "#67E8F9",
    },
    "dyslexia_cream": {
        "background": "#FFFBF0",
        "text": "#2C1810",
        "title": "#B45309",
        "box_bg": "#FEF3C7",
        "box_border": "#D97706",
        "accent": "#2D5016",
        "line": "#92400E",
    },
    "dyslexia_yellow": {
        "background": "#FEFCE8",
        "text": "#1A1A00",
        "title": "#1D4ED8",
        "box_bg": "#FEF9C3",
        "box_border": "#1D4ED8",
        "accent": "#15803D",
        "line": "#2563EB",
    },
}

# Pastel branch palette for mind map nodes (cycles through branches)
BRANCH_PALETTE = [
    {"bg": "#FDE8E8", "border": "#E53E3E"},  # soft red
    {"bg": "#FEF3C7", "border": "#D97706"},  # amber
    {"bg": "#D1FAE5", "border": "#059669"},  # green
    {"bg": "#DBEAFE", "border": "#2563EB"},  # blue
    {"bg": "#EDE9FE", "border": "#7C3AED"},  # violet
    {"bg": "#FCE7F3", "border": "#DB2777"},  # pink
    {"bg": "#CCFBF1", "border": "#0D9488"},  # teal
    {"bg": "#FFF7ED", "border": "#EA580C"},  # orange
]

# Topic-specific emoji mappings
TOPIC_EMOJIS = {
    "photosynthesis": {"main": "🌱", "sun": "☀️", "plant": "🌿", "water": "💧", "glucose": "🍃", "oxygen": "🌬️"},
    "water_cycle": {"main": "🌊", "sun": "☀️", "evaporation": "🔥", "clouds": "☁️", "rain": "🌧️", "collection": "🌊"},
    "sea_breeze": {"main": "🌬️", "sea": "🌊", "wind": "💨", "clouds": "☁️", "cool": "❄️", "air": "🌫️"},
    "land_breeze": {"main": "🌬️", "land": "🌾", "wind": "💨", "night": "🌙", "air": "🌫️"},
    "digestive": {"main": "🍎", "food": "🍎", "mouth": "👄", "stomach": "🫃", "nutrients": "🧠", "energy": "⚡"},
    "respiration": {"main": "🫁", "oxygen": "🫁", "glucose": "🍃", "cells": "🧬", "energy": "⚡", "co2": "💨"},
    "heart": {"main": "❤️", "heart": "❤️", "blood": "🩸", "veins": "🔴", "arteries": "🔵", "brain": "🧠"},
    "plants": {"main": "🌱", "leaf": "🍂", "roots": "🌱", "stem": "🌾", "flower": "🌸", "seeds": "🌰"},
    "ecosystem": {"main": "🌿", "sun": "☀️", "plants": "🌿", "herbivore": "🦌", "carnivore": "🦁", "decomposer": "🍄"},
    "cell": {"main": "🧬", "nucleus": "⭕", "mitochondria": "⚡", "membrane": "🔵", "cytoplasm": "💧", "ribosome": "◾"},
    "default": {"main": "⚙️", "input": "⬅️", "process": "⚙️", "output": "➡️", "step": "📍", "connect": "🔗"},
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


def _intelligent_shorten(text: str, max_width: int, draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont, max_words: int = 5) -> str:
    """Shorten text to fit max_width by trimming at word boundaries only.

    Does NOT remove stop words or strip grammar — that corrupts explanation sentences.
    Simply drops trailing words until the text fits.
    """
    if draw.textlength(text, font=font) <= max_width:
        return text

    words = text.split()
    while len(words) > 1 and draw.textlength(" ".join(words), font=font) > max_width:
        words = words[:-1]

    result = " ".join(words[:max_words])
    return result


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 2) -> list[str]:
    """Wrap text to fit within max_width and limit lines.
    
    No ellipsis. Uses intelligent shortening if needed.
    """
    if max_width <= 0:
        return [text]

    words = [word for word in text.strip().split() if word]
    if not words:
        return [text]

    lines: list[str] = []
    current_line = words[0]

    for word in words[1:]:
        candidate = f"{current_line} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current_line = candidate
        else:
            lines.append(current_line)
            current_line = word
            if len(lines) == max_lines - 1:
                break

    lines.append(current_line)

    # Trim to max_lines
    if len(lines) > max_lines:
        lines = lines[:max_lines]

    # If last line is too long, shorten it intelligently
    if len(lines) > 0:
        last_line = lines[-1]
        if draw.textlength(last_line, font=font) > max_width:
            shortened = _intelligent_shorten(last_line, max_width, draw, font, max_words=5)
            lines[-1] = shortened

    return lines


def _emoji_to_asset_filename(emoji: str) -> str:
    """Convert an emoji character to a Twemoji asset filename."""
    filtered = [ch for ch in emoji if ch not in {"\uFE0F", "\u200D", "\uFE0E", "\uFE0F"}]
    codes = [f"{ord(ch):x}" for ch in filtered if not ch.isspace()]
    return "-".join(codes) + ".png"


def _load_emoji_png(emoji: str) -> Image.Image | None:
    """Load a local PNG emoji by character if available."""
    asset_name = _emoji_to_asset_filename(emoji)
    asset_path = os.path.join("assets", "emojis", asset_name)
    if os.path.exists(asset_path):
        try:
            return Image.open(asset_path).convert("RGBA")
        except Exception:
            return None
    return None


def _draw_emoji_png(image: Image.Image, emoji_img: Image.Image, center_x: int, center_y: int, size: int) -> None:
    """Draw an emoji PNG centered at the given location."""
    icon = emoji_img.resize((size, size), Image.LANCZOS)
    px = int(center_x - size / 2)
    py = int(center_y - size / 2)
    image.paste(icon, (px, py), icon)


def _measure_text_block(draw: ImageDraw.ImageDraw, lines: list[str], font: ImageFont.ImageFont, spacing: int = 6) -> tuple[int, int]:
    """Measure text block dimensions with proper line spacing.
    
    Returns:
        (width, height) tuple of text block in pixels
    """
    if not lines:
        return 0, 0
    
    widths = [draw.textbbox((0, 0), line, font=font)[2] for line in lines]
    line_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
    
    width = max(widths) if widths else 0
    height = sum(line_heights) + spacing * max(0, len(lines) - 1)
    
    return width, height


def _measure_single_char(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    """Measure a single character (emoji or text) dimensions."""
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height


def _calculate_node_dimensions(
    draw: ImageDraw.ImageDraw,
    text_lines: list[str],
    text_font: ImageFont.ImageFont,
    emoji: str,
    emoji_font: ImageFont.ImageFont,
    padding: int = 30,
    level: int = 1,
) -> tuple[int, int]:
    """Calculate optimal node dimensions based on content.
    
    Args:
        draw: ImageDraw instance
        text_lines: Wrapped text lines
        text_font: Font for text
        emoji: Emoji character
        emoji_font: Font for emoji
        padding: Internal padding
        level: Node hierarchy level (1=primary, 2=supporting)
        
    Returns:
        (width, height) tuple for the node
    """
    # Measure text content
    text_width, text_height = _measure_text_block(draw, text_lines, text_font, spacing=8)
    
    # Measure emoji
    emoji_w, emoji_h = _measure_single_char(draw, emoji, emoji_font)
    
    # Calculate node dimensions with proper spacing
    # Total height = emoji + spacing + text
    min_node_width = 220 if level == 1 else 180
    max_node_width = 360 if level == 1 else 300
    
    # Width: accommodate text and emoji with padding
    node_width = max(
        min_node_width,
        text_width + padding * 2,
        emoji_w + padding * 2
    )
    node_width = min(node_width, max_node_width)
    
    # Height: emoji + spacing + text + padding
    node_height = emoji_h + 12 + text_height + padding * 2
    
    return int(node_width), int(node_height)


def _rectangles_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int], padding: int = 20) -> bool:
    return not (
        a[2] + padding < b[0]
        or a[0] - padding > b[2]
        or a[3] + padding < b[1]
        or a[1] - padding > b[3]
    )


def _rect_to_center(rect: tuple[int, int, int, int]) -> tuple[int, int]:
    return ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)


def _point_on_rect_edge(center_x: int, center_y: int, half_width: int, half_height: int, direction_x: float, direction_y: float) -> tuple[int, int]:
    if abs(direction_x) < 1e-6:
        return int(center_x), int(center_y + math.copysign(half_height, direction_y))

    slope = direction_y / direction_x
    x_edge = center_x + math.copysign(half_width, direction_x)
    y_edge = center_y + slope * (x_edge - center_x)

    if abs(y_edge - center_y) <= half_height:
        return int(x_edge), int(y_edge)

    y_edge = center_y + math.copysign(half_height, direction_y)
    x_edge = center_x + (y_edge - center_y) / slope
    return int(x_edge), int(y_edge)


def _point_on_circle_edge(center_x: int, center_y: int, radius: int, angle: float) -> tuple[int, int]:
    return (
        int(center_x + math.cos(angle) * radius),
        int(center_y + math.sin(angle) * radius),
    )


def create_mind_map(title: str, nodes_or_model: list[dict] | dict[str, Any], theme: str = "light") -> str:
    """Create a polished emoji-first mind map with improved layout and hierarchy.
    
    Features:
    - Dynamic node sizing based on content
    - Proper text centering and vertical alignment
    - Visual hierarchy (level 1 larger than level 2)
    - Smart spacing and collision avoidance
    - Professional educational design
    """
    logger.info("ENTER: create_mind_map at %s", datetime.utcnow().isoformat(timespec="milliseconds"))
    if theme not in COLOR_SCHEMES:
        theme = "light"

    # Compatibility: accept either a legacy flattened `nodes` list or the new
    # hierarchical layout model produced by the adapter. If a layout model dict
    # is provided, construct an equivalent flattened node list for the existing
    # rendering pipeline while preserving the original layout_model data for
    # potential future use.
    layout_model = None
    if isinstance(nodes_or_model, dict):
        layout_model = nodes_or_model
        # Use adapter-provided flattened nodes if present, otherwise build one
        if isinstance(layout_model.get("nodes"), list):
            nodes = list(layout_model.get("nodes"))
        else:
            nodes = []
            center = layout_model.get("center_node") or {}
            if center:
                nodes.append({
                    "text": center.get("label", title),
                    "emoji": "🧠",
                    "level": 0,
                    "visual_style": center.get("visual_style", {}),
                })
            for branch in layout_model.get("branch_nodes", []) or []:
                nodes.append({
                    "text": branch.get("label", ""),
                    "emoji": "📌",
                    "level": 1,
                    "visual_style": branch.get("visual_style", {}),
                })
            for child in layout_model.get("child_nodes", []) or []:
                nodes.append({
                    "text": child.get("label", ""),
                    "emoji": "📍",
                    "level": 2,
                    "visual_style": child.get("visual_style", {}),
                })
    else:
        nodes = list(nodes_or_model or [])

    logger.info("[MindMap] Step 1 - create_mind_map started: title=%r nodes=%d theme=%r", title, len(nodes), theme)

    colors = COLOR_SCHEMES[theme]
    emojis = get_topic_emojis(title)

    # Canvas parameters with balanced layout
    img_width = 2200
    img_height = 1800
    margin = 110
    min_radius = 500
    padding = 35
    max_nodes = min(len(nodes), 12)

    image = Image.new("RGB", (img_width, img_height), hex_to_rgb(colors["background"]))
    draw = ImageDraw.Draw(image)

    try:
        title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 46)
        node_font_l1 = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 28)
        node_font_l2 = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 24)
        subtitle_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 26)
    except (IOError, OSError):
        try:
            title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 46)
            node_font_l1 = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 28)
            node_font_l2 = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 24)
            subtitle_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 26)
        except (IOError, OSError):
            title_font = ImageFont.load_default()
            node_font_l1 = ImageFont.load_default()
            node_font_l2 = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

    cx = img_width // 2
    cy = img_height // 2

    # Draw title
    title_lines = _wrap_text(draw, title, title_font, img_width - margin * 2, max_lines=2)
    draw.multiline_text(
        (cx, margin // 2),
        "\n".join(title_lines),
        fill=hex_to_rgb(colors["title"]),
        font=title_font,
        anchor="ma",
        align="center",
        spacing=12,
    )

    # Build and measure central node
    central_icon = emojis.get("main", emojis.get("process", "🧠"))
    central_image = _load_emoji_png(central_icon)
    central_label_lines = _wrap_text(draw, title, node_font_l1, 280, max_lines=2)
    central_text_width, central_text_height = _measure_text_block(draw, central_label_lines, node_font_l1, spacing=10)
    central_icon_size = 130
    
    central_box_width = max(360, central_text_width + padding * 2, central_icon_size + padding * 2)
    central_box_height = central_icon_size + central_text_height + padding * 3
    central_box_width = int(central_box_width * 1.25)
    central_box_height = int(central_box_height * 1.25)

    # Draw central node
    central_box = [
        cx - central_box_width // 2,
        cy - central_box_height // 2,
        cx + central_box_width // 2,
        cy + central_box_height // 2,
    ]
    draw.rounded_rectangle(
        central_box,
        radius=50,
        fill=hex_to_rgb(colors["box_bg"]),
        outline=hex_to_rgb(colors["box_border"]),
        width=5,
    )

    central_icon_y = central_box[1] + padding + central_icon_size // 2
    if central_image:
        _draw_emoji_png(image, central_image, cx, central_icon_y, central_icon_size)
    else:
        draw.text((cx, central_icon_y), central_icon, font=subtitle_font, fill=hex_to_rgb(colors["text"]), anchor="mm")

    # Draw central text - vertically centered
    text_y = central_icon_y + central_icon_size // 2 + padding // 2
    draw.multiline_text(
        (cx, text_y),
        "\n".join(central_label_lines),
        font=node_font_l1,
        fill=hex_to_rgb(colors["text"]),
        anchor="ma",
        align="center",
        spacing=10,
    )

    # Build child nodes with dynamic sizing based on hierarchy level
    child_nodes = []
    for index, node_item in enumerate(nodes[:max_nodes]):
        node_text = node_item.get("text", "") if isinstance(node_item, dict) else str(node_item)
        node_icon = node_item.get("emoji", "📍") if isinstance(node_item, dict) else "📍"
        node_level = node_item.get("level", 1) if isinstance(node_item, dict) else 1
        
        if not node_icon or not node_icon.strip():
            node_icon = "📍"
        
        # Use appropriate font based on hierarchy level
        node_font = node_font_l1 if node_level == 1 else node_font_l2
        max_width = 360 if node_level == 1 else 300
        
        wrapped = _wrap_text(draw, node_text, node_font, max_width, max_lines=2)
        emoji_image = _load_emoji_png(node_icon)
        
        # Determine icon size based on level
        icon_size = 95 if node_level == 1 else 75
        
        # Calculate dynamic node dimensions
        node_width, node_height = _calculate_node_dimensions(
            draw, wrapped, node_font, node_icon, subtitle_font,
            padding=padding, level=node_level
        )
        
        child_nodes.append({
            "text_lines": wrapped,
            "emoji": node_icon,
            "emoji_image": emoji_image,
            "width": node_width,
            "height": node_height,
            "angle": 0.0,
            "center": (0, 0),
            "icon_size": icon_size,
            "level": node_level,
            "font": node_font,
        })

    node_count = len(child_nodes)
    logger.info("[MindMap] Step 2 - nodes prepared: node_count=%d", node_count)
    
    # Calculate radial layout with improved spacing
    angle_step = (2 * math.pi) / max(node_count, 1)
    radius = max(min_radius, 520 + (node_count - 8) * 100)
    node_rects: list[tuple[int, int, int, int]] = []
    central_half_w = central_box_width // 2
    central_half_h = central_box_height // 2
    central_rect = (central_box[0], central_box[1], central_box[2], central_box[3])

    # Layout resolution loop - now with better bounds checking
    MAX_LAYOUT_ATTEMPTS = 25
    for attempt in range(MAX_LAYOUT_ATTEMPTS):
        loop_start = time.perf_counter()
        node_rects.clear()
        
        for i, node in enumerate(child_nodes):
            angle = angle_step * i
            node["angle"] = angle
            x = int(cx + math.cos(angle) * radius)
            y = int(cy + math.sin(angle) * radius)
            node["center"] = (x, y)
            half_w = node["width"] // 2
            half_h = node["height"] // 2
            node_rects.append((x - half_w, y - half_h, x + half_w, y + half_h))

        # Check for overlaps with improved padding
        overlaps = any(
            _rectangles_overlap(node_rects[a_index], node_rects[b_index], padding=60)
            for a_index in range(len(node_rects))
            for b_index in range(a_index + 1, len(node_rects))
        )

        any_overlap_central = any(
            _rectangles_overlap(rect, central_rect, padding=50)
            for rect in node_rects
        )

        # Check bounds
        outside_bounds = False
        for _ni, (_rect, _node) in enumerate(zip(node_rects, child_nodes)):
            if _rect[0] < margin or _rect[1] < margin or _rect[2] > img_width - margin or _rect[3] > img_height - margin:
                outside_bounds = True
                break

        loop_duration = time.perf_counter() - loop_start
        logger.info(
            "[MindMap] Step 3 - attempt=%d radius=%d overlaps=%s central_overlap=%s outside_bounds=%s "
            "canvas=%dx%d loop_time=%.4fs",
            attempt, radius, overlaps, any_overlap_central, outside_bounds,
            img_width, img_height, loop_duration,
        )

        if not overlaps and not outside_bounds and not any_overlap_central:
            logger.info("[MindMap] Step 3 complete - layout settled after %d attempts", attempt)
            break

        # Grow radius and canvas with better progression
        radius += 70
        img_width += 140
        img_height += 140
        image = Image.new("RGB", (img_width, img_height), hex_to_rgb(colors["background"]))
        draw = ImageDraw.Draw(image)
        cx = img_width // 2
        cy = img_height // 2
        central_box = [
            cx - central_box_width // 2,
            cy - central_box_height // 2,
            cx + central_box_width // 2,
            cy + central_box_height // 2,
        ]
        central_rect = (central_box[0], central_box[1], central_box[2], central_box[3])
        
        logger.warning("[MindMap] Step 3 retrying attempt=%d radius=%d canvas=%dx%d", attempt + 1, radius, img_width, img_height)
    else:
        logger.warning(
            "[MindMap] Step 3 reached MAX_LAYOUT_ATTEMPTS=%d — using best layout found",
            MAX_LAYOUT_ATTEMPTS,
        )

    # Render connectors (pass 1: behind everything)
    for idx, node in enumerate(child_nodes):
        x, y = node["center"]
        half_w = node["width"] // 2
        half_h = node["height"] // 2
        branch_color = BRANCH_PALETTE[idx % len(BRANCH_PALETTE)]
        start = _point_on_rect_edge(cx, cy, central_half_w, central_half_h, math.cos(node["angle"]), math.sin(node["angle"]))
        end = _point_on_rect_edge(x, y, half_w + 10, half_h + 10, math.cos(node["angle"]), math.sin(node["angle"]))
        draw.line([start, end], fill=hex_to_rgb(branch_color["border"]), width=4)

    # Redraw central box on top of connectors (pass 2)
    draw.rounded_rectangle(
        central_box,
        radius=50,
        fill=hex_to_rgb(colors["box_bg"]),
        outline=hex_to_rgb(colors["box_border"]),
        width=5,
    )
    if central_image:
        _draw_emoji_png(image, central_image, cx, central_icon_y, central_icon_size)
    else:
        draw.text((cx, central_icon_y), central_icon, font=subtitle_font, fill=hex_to_rgb(colors["text"]), anchor="mm")
    draw.multiline_text(
        (cx, text_y),
        "\n".join(central_label_lines),
        font=node_font_l1,
        fill=hex_to_rgb(colors["text"]),
        anchor="ma",
        align="center",
        spacing=10,
    )

    # Draw branch nodes with proper centering (pass 3)
    for idx, node in enumerate(child_nodes):
        x, y = node["center"]
        half_w = node["width"] // 2
        half_h = node["height"] // 2
        node_box = [x - half_w, y - half_h, x + half_w, y + half_h]
        branch_color = BRANCH_PALETTE[idx % len(BRANCH_PALETTE)]
        
        draw.rounded_rectangle(
            node_box,
            radius=36,
            fill=hex_to_rgb(branch_color["bg"]),
            outline=hex_to_rgb(branch_color["border"]),
            width=4,
        )

        # === Centered content block (emoji + text as one unit) ===
        # Measure text lines
        text_lines = node["text_lines"]
        line_height = 20
        line_spacing = 8
        text_total_height = sum(
            max(draw.textbbox((0, 0), line, font=node["font"])[3], line_height)
            for line in text_lines
        ) + (line_spacing * max(0, len(text_lines) - 1))
        
        # Total content height (emoji + spacing + text)
        content_total_height = node["icon_size"] + 12 + text_total_height
        
        # Vertical center of the box
        box_center_y = y
        
        # Top of the content block
        content_top = box_center_y - content_total_height // 2
        
        # Emoji position (top of content block)
        icon_y = content_top + node["icon_size"] // 2
        
        # Text position (below emoji with spacing)
        text_y = icon_y + node["icon_size"] // 2 + 12

        # Draw emoji
        if node["emoji_image"]:
            _draw_emoji_png(image, node["emoji_image"], x, icon_y, node["icon_size"])
        else:
            draw.text((x, icon_y), node["emoji"], font=subtitle_font, fill=hex_to_rgb(colors["text"]), anchor="mm")

        # Draw text
        draw.multiline_text(
            (x, text_y),
            "\n".join(text_lines),
            font=node["font"],
            fill=hex_to_rgb("#1A1A2E"),
            anchor="ma",
            align="center",
            spacing=8,
        )

    filename = f"mindmap_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(VISUALS_FOLDER, filename)
    logger.info("[MindMap] Step 4 - saving image to %s", filepath)
    image.save(filepath)
    logger.info("[MindMap] Step 4 complete - image saved")
    logger.info("EXIT: create_mind_map at %s", datetime.utcnow().isoformat(timespec="milliseconds"))
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

    try:
        from graphviz import Digraph
        return _create_flowchart_graphviz(title, steps, colors)
    except Exception:
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
        margin="0.8",
        pad="0.8",
        nodesep="1.2",
        ranksep="1.8",
        splines="ortho",
        label=title,
        labelloc="t",
        fontsize="28",
        fontname="Arial Bold",
        bgcolor="#F8FAFF",
    )

    graph.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fillcolor=colors["box_bg"],
        fontcolor=colors["text"],
        fontname="Arial Bold",
        fontsize="18",
        penwidth="2.5",
        color=colors["box_border"],
        margin="0.45,0.30",
        width="3.5",
    )

    graph.attr("edge", arrowsize="1.4", color=colors["line"], penwidth="2.5", fontname="Arial", minlen="2", arrowhead="vee")

    emojis = get_topic_emojis(title)
    emoji_keys = list(emojis.keys())
    for i, step in enumerate(steps[:10]):
        step_text = step[:45] + ("..." if len(step) > 45 else "")
        emoji = emojis.get(emoji_keys[i % len(emoji_keys)], "📍")
        graph.node(f"step{i}", label=f"{i + 1}. {emoji}  {step_text}")

    for i in range(len(steps) - 1):
        graph.edge(f"step{i}", f"step{i + 1}")

    filename = f"flowchart_edu_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(VISUALS_FOLDER, filename)

    try:
        graph.render(filepath.replace(".png", ""), view=False, quiet=True, cleanup=True)
        return filepath
    except Exception as exc:
        raise RuntimeError(f"Graphviz flowchart generation failed: {exc}") from exc


def _create_flowchart_pillow(title: str, steps: list[str], colors: dict) -> str:
    """Fallback flowchart creation using Pillow with proper text positioning.
    
    Features:
    - Content (emoji + text) centered as single block
    - No text overflow or clipping
    - Dynamic node sizing
    - Intelligent text shortening (no ellipsis)
    - Proper vertical centering
    """
    padding = 80
    step_gap = 120

    try:
        title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 38)
        text_font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 22)
        emoji_font = ImageFont.truetype("C:\\Windows\\Fonts\\seguiemj.ttf", 48)
    except (IOError, OSError):
        try:
            title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 38)
            text_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 22)
            emoji_font = ImageFont.load_default()
        except (IOError, OSError):
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            emoji_font = ImageFont.load_default()

    temp_img = Image.new("RGB", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)

    # Phase 1: Pre-measure all steps and calculate node sizes
    node_specs = []
    max_node_width = 0
    
    for i, step in enumerate(steps[:10]):
        # Wrap text to max width
        wrapped_lines = _wrap_text(temp_draw, step, text_font, 520, max_lines=2)
        
        # Measure text dimensions
        text_width, text_height = _measure_text_block(temp_draw, wrapped_lines, text_font, spacing=10)
        
        # Measure emoji
        emoji = get_topic_emojis(title).get(
            list(get_topic_emojis(title).keys())[i % len(get_topic_emojis(title))], 
            "📍"
        )
        emoji_bbox = temp_draw.textbbox((0, 0), emoji, font=emoji_font)
        emoji_width = emoji_bbox[2] - emoji_bbox[0]
        emoji_height = emoji_bbox[3] - emoji_bbox[1]
        
        # Calculate node dimensions
        node_content_width = max(text_width, emoji_width) + 60
        node_content_height = emoji_height + 20 + text_height + 60
        
        node_specs.append({
            "lines": wrapped_lines,
            "emoji": emoji,
            "emoji_width": emoji_width,
            "emoji_height": emoji_height,
            "text_width": text_width,
            "text_height": text_height,
            "width": max(280, node_content_width),
            "height": max(120, node_content_height),
        })
        max_node_width = max(max_node_width, node_specs[-1]["width"])

    # Phase 2: Calculate canvas size
    img_width = max(1000, max_node_width + padding * 2)
    total_content_height = sum(node["height"] for node in node_specs)
    total_gaps = step_gap * (len(node_specs) - 1)
    img_height = padding * 2 + total_content_height + total_gaps + 80

    image = Image.new("RGB", (img_width, img_height), hex_to_rgb(colors["background"]))
    draw = ImageDraw.Draw(image)

    # Phase 3: Draw title
    draw.text(
        (img_width // 2, padding // 2 + 20),
        title,
        fill=hex_to_rgb(colors["title"]),
        font=title_font,
        anchor="mm",
    )

    # Phase 4: Render each node with proper centering
    center_x = img_width // 2
    y_offset = padding + 50

    for index, node in enumerate(node_specs):
        box_width = node["width"]
        box_height = node["height"]
        top = y_offset
        left = center_x - box_width // 2
        right = center_x + box_width // 2
        bottom = top + box_height
        step_color = BRANCH_PALETTE[index % len(BRANCH_PALETTE)]

        # Draw node box
        draw.rounded_rectangle(
            [(left, top), (right, bottom)],
            radius=32,
            fill=hex_to_rgb(step_color["bg"]),
            outline=hex_to_rgb(step_color["border"]),
            width=4,
        )

        # Draw step number badge
        badge_r = 22
        badge_cx = left + badge_r + 12
        badge_cy = top + box_height // 2
        draw.ellipse(
            [badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r],
            fill=hex_to_rgb(step_color["border"]),
        )
        draw.text((badge_cx, badge_cy), str(index + 1), font=text_font, fill=(255, 255, 255), anchor="mm")

        # === Calculate centered content block ===
        # Total height of content (emoji + spacing + text)
        content_total_height = node["emoji_height"] + 20 + node["text_height"]
        
        # Vertical center of the box
        box_center_y = top + box_height // 2
        
        # Top of the content block (if centered)
        content_top = box_center_y - content_total_height // 2
        
        # Emoji position (top of content block)
        emoji_y = content_top + node["emoji_height"] // 2
        
        # Text position (below emoji with spacing)
        text_y = emoji_y + node["emoji_height"] // 2 + 10 + node["text_height"] // 2

        # Draw emoji centered horizontally
        draw.text(
            (center_x, emoji_y),
            node["emoji"],
            font=emoji_font,
            fill=hex_to_rgb(colors["text"]),
            anchor="mm",
        )

        # Draw text centered horizontally and positioned after emoji
        draw.multiline_text(
            (center_x, text_y),
            "\n".join(node["lines"]),
            font=text_font,
            fill=hex_to_rgb("#1A1A2E"),
            anchor="ma",
            align="center",
            spacing=10,
        )

        # Draw connector to next step if not the last step
        if index < len(node_specs) - 1:
            line_start = (center_x, bottom + 16)
            line_end = (center_x, bottom + step_gap - 16)
            draw.line([line_start, line_end], fill=hex_to_rgb(colors["line"]), width=5)
            
            # Draw arrow at end of connector
            arrow_tip = (center_x, bottom + step_gap - 4)
            arrow_width = 16
            arrow_height = 24
            draw.polygon(
                [
                    arrow_tip,
                    (center_x - arrow_width, bottom + step_gap - arrow_height),
                    (center_x + arrow_width, bottom + step_gap - arrow_height),
                ],
                fill=hex_to_rgb(colors["line"]),
            )

        y_offset += box_height + step_gap

    filename = f"flowchart_edu_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(VISUALS_FOLDER, filename)
    image.save(filepath)
    logger.info("[Flowchart] Generated: %s (canvas=%dx%d, nodes=%d, no ellipsis)", 
                filepath, img_width, img_height, len(node_specs))
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
