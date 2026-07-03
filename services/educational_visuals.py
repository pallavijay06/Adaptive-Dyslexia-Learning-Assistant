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


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int, max_lines: int = 2) -> list[str]:
    """Wrap text to fit within max_width and limit the number of lines."""
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

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    if len(lines) == max_lines:
        last = lines[-1]
        while draw.textlength(last + "…", font=font) > max_width and last:
            last = last.rsplit(" ", 1)[0]
        if last:
            lines[-1] = last + "…"
        else:
            truncated = text[: max_width // 8].rstrip()
            lines[-1] = truncated + "…"

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
    widths = [draw.textbbox((0, 0), line, font=font)[2] for line in lines]
    height = sum(draw.textbbox((0, 0), line, font=font)[3] for line in lines)
    if len(lines) > 1:
        height += spacing * (len(lines) - 1)
    return max(widths) if widths else 0, height


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


def create_mind_map(title: str, nodes: list[dict], theme: str = "light") -> str:
    """Create a polished emoji-first mind map diagram with radial layout."""
    logger.info("ENTER: create_mind_map at %s", datetime.utcnow().isoformat(timespec="milliseconds"))
    if theme not in COLOR_SCHEMES:
        theme = "light"

    logger.info("[MindMap] Step 1 - create_mind_map started: title=%r nodes=%d theme=%r", title, len(nodes), theme)

    colors = COLOR_SCHEMES[theme]
    emojis = get_topic_emojis(title)

    img_width = 2200
    img_height = 1800
    margin = 110
    min_radius = 500
    padding = 30
    max_nodes = min(len(nodes), 12)

    image = Image.new("RGB", (img_width, img_height), hex_to_rgb(colors["background"]))
    draw = ImageDraw.Draw(image)

    try:
        title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 46)
        node_font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 28)
        subtitle_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 26)
    except (IOError, OSError):
        try:
            title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 46)
            node_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 28)
            subtitle_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 26)
        except (IOError, OSError):
            title_font = ImageFont.load_default()
            node_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

    cx = img_width // 2
    cy = img_height // 2

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

    central_icon = emojis.get("main", emojis.get("process", "🧠"))
    central_image = _load_emoji_png(central_icon)
    central_label_lines = _wrap_text(draw, title, node_font, 260, max_lines=2)
    central_text_width, central_text_height = _measure_text_block(draw, central_label_lines, node_font, spacing=10)
    central_icon_size = 120
    central_box_width = max(320, central_text_width + padding * 2, central_icon_size + padding * 2)
    central_box_height = central_icon_size + central_text_height + padding * 3
    central_box_width = int(central_box_width * 1.3)
    central_box_height = int(central_box_height * 1.3)

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

    draw.multiline_text(
        (cx, central_icon_y + central_icon_size // 2 + padding // 2),
        "\n".join(central_label_lines),
        font=node_font,
        fill=hex_to_rgb(colors["text"]),
        anchor="ma",
        align="center",
        spacing=10,
    )

    child_nodes = []
    for index, node_item in enumerate(nodes[:max_nodes]):
        node_text = node_item.get("text", "") if isinstance(node_item, dict) else str(node_item)
        node_icon = node_item.get("emoji", "📍") if isinstance(node_item, dict) else "📍"
        if not node_icon or not node_icon.strip():
            node_icon = "📍"
        wrapped = _wrap_text(draw, node_text, node_font, 340, max_lines=2)
        text_width, text_height = _measure_text_block(draw, wrapped, node_font, spacing=8)
        emoji_image = _load_emoji_png(node_icon)
        icon_size = 90
        node_width = max(260, text_width + padding * 2, icon_size + padding * 2)
        node_height = text_height + icon_size + padding * 3
        child_nodes.append(
            {
                "text_lines": wrapped,
                "emoji": node_icon,
                "emoji_image": emoji_image,
                "width": int(node_width),
                "height": int(node_height),
                "angle": 0.0,
                "center": (0, 0),
                "icon_size": icon_size,
            }
        )

    node_count = len(child_nodes)
    logger.info("[MindMap] Step 2 - nodes prepared: node_count=%d", node_count)
    angle_step = (2 * math.pi) / max(node_count, 1)
    radius = max(min_radius, 520 + (node_count - 8) * 80)
    node_rects: list[tuple[int, int, int, int]] = []
    central_half_w = central_box_width // 2
    central_half_h = central_box_height // 2
    central_rect = (central_box[0], central_box[1], central_box[2], central_box[3])

    MAX_LAYOUT_ATTEMPTS = 20
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

        overlaps = any(
            _rectangles_overlap(node_rects[a_index], node_rects[b_index], padding=50)
            for a_index in range(len(node_rects))
            for b_index in range(a_index + 1, len(node_rects))
        )

        any_overlap_central = any(
            _rectangles_overlap(rect, central_rect, padding=40)
            for rect in node_rects
        )

        outside_bounds = False
        for _ni, (_rect, _node) in enumerate(zip(node_rects, child_nodes)):
            _failed: list[str] = []
            if _rect[0] < margin:              _failed.append("LEFT")
            if _rect[1] < margin:              _failed.append("TOP")
            if _rect[2] > img_width - margin:  _failed.append("RIGHT")
            if _rect[3] > img_height - margin: _failed.append("BOTTOM")
            if _failed:
                outside_bounds = True
                logger.warning(
                    "[MindMap] BOUNDS FAIL attempt=%d node=%d text=%r "
                    "x=%d y=%d w=%d h=%d rect=(%d,%d,%d,%d) "
                    "canvas=%dx%d margin=%d boundary=%s",
                    attempt, _ni, " ".join(_node["text_lines"]),
                    _node["center"][0], _node["center"][1],
                    _node["width"], _node["height"],
                    _rect[0], _rect[1], _rect[2], _rect[3],
                    img_width, img_height, margin, ",".join(_failed),
                )

        loop_duration = time.perf_counter() - loop_start
        logger.info(
            "[MindMap] Step 3 - attempt=%d radius=%d overlaps=%s "
            "any_overlap_central=%s outside_bounds=%s canvas=%dx%d loop_time=%.4f",
            attempt, radius, overlaps, any_overlap_central, outside_bounds,
            img_width, img_height, loop_duration,
        )

        if not overlaps and not outside_bounds and not any_overlap_central:
            logger.info("[MindMap] Step 3 complete - layout settled after %d attempts", attempt)
            break

        # Grow both radius and canvas together so outside_bounds can resolve
        radius += 60
        img_width += 120
        img_height += 120
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
        logger.warning(
            "[MindMap] Step 3 retrying attempt=%d radius=%d canvas=%dx%d",
            attempt + 1, radius, img_width, img_height,
        )
    else:
        logger.warning(
            "[MindMap] Step 3 reached MAX_LAYOUT_ATTEMPTS=%d — using best layout found "
            "(overlaps=%s outside_bounds=%s)",
            MAX_LAYOUT_ATTEMPTS, overlaps, outside_bounds,
        )

    # Pass 1: draw connectors (behind everything)
    for idx, node in enumerate(child_nodes):
        x, y = node["center"]
        half_w = node["width"] // 2
        half_h = node["height"] // 2
        branch_color = BRANCH_PALETTE[idx % len(BRANCH_PALETTE)]
        start = _point_on_rect_edge(cx, cy, central_half_w, central_half_h, math.cos(node["angle"]), math.sin(node["angle"]))
        end = _point_on_rect_edge(x, y, half_w + 8, half_h + 8, math.cos(node["angle"]), math.sin(node["angle"]))
        draw.line([start, end], fill=hex_to_rgb(branch_color["border"]), width=4)

    # Pass 2: redraw central box on top of connectors
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
        (cx, central_icon_y + central_icon_size // 2 + padding // 2),
        "\n".join(central_label_lines),
        font=node_font,
        fill=hex_to_rgb(colors["text"]),
        anchor="ma",
        align="center",
        spacing=10,
    )

    # Pass 3: draw branch nodes
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

        icon_y = y - node["height"] // 3
        if node["emoji_image"]:
            _draw_emoji_png(image, node["emoji_image"], x, icon_y, node["icon_size"])
        else:
            draw.text((x, icon_y), node["emoji"], font=subtitle_font, fill=hex_to_rgb(colors["text"]), anchor="mm")

        draw.multiline_text(
            (x, y + node["icon_size"] // 6),
            "\n".join(node["text_lines"]),
            font=node_font,
            fill=hex_to_rgb("#1A1A2E"),
            anchor="mm",
            align="center",
            spacing=10,
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
    """Fallback flowchart creation using Pillow."""
    padding = 80
    step_gap = 100

    try:
        title_font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 38)
        text_font = ImageFont.truetype("C:\\Windows\\Fonts\\arialbd.ttf", 22)
        emoji_font = ImageFont.truetype("C:\\Windows\\Fonts\\seguiemj.ttf", 46)
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

    node_specs = []
    max_width = 0
    for i, step in enumerate(steps[:10]):
        step_lines = _wrap_text(temp_draw, step, text_font, 520)
        text_width, text_height = _measure_text_block(temp_draw, step_lines, text_font, spacing=8)
        emoji = get_topic_emojis(title).get(list(get_topic_emojis(title).keys())[i % len(get_topic_emojis(title))], "📍")
        emoji_height = temp_draw.textbbox((0, 0), emoji, font=emoji_font)[3]
        node_width = max(text_width + 80, 280, temp_draw.textbbox((0, 0), emoji, font=emoji_font)[2] + 60)
        node_height = text_height + emoji_height + 70
        node_specs.append({
            "lines": step_lines,
            "emoji": emoji,
            "width": int(node_width),
            "height": int(node_height),
        })
        max_width = max(max_width, node_width)

    img_width = max(1000, max_width + padding * 2)
    img_height = padding * 2 + sum(node["height"] for node in node_specs) + step_gap * (len(node_specs) - 1) + 60

    image = Image.new("RGB", (img_width, img_height), hex_to_rgb(colors["background"]))
    draw = ImageDraw.Draw(image)

    draw.text(
        (img_width // 2, padding // 2 + 20),
        title,
        fill=hex_to_rgb(colors["title"]),
        font=title_font,
        anchor="mm",
    )

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

        draw.rounded_rectangle(
            [(left, top), (right, bottom)],
            radius=32,
            fill=hex_to_rgb(step_color["bg"]),
            outline=hex_to_rgb(step_color["border"]),
            width=4,
        )

        # Step number badge
        badge_r = 22
        badge_cx = left + badge_r + 12
        badge_cy = top + box_height // 2
        draw.ellipse(
            [badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r],
            fill=hex_to_rgb(step_color["border"]),
        )
        draw.text((badge_cx, badge_cy), str(index + 1), font=text_font, fill=(255, 255, 255), anchor="mm")

        draw.text(
            (center_x, top + 28),
            node["emoji"],
            font=emoji_font,
            fill=hex_to_rgb(colors["text"]),
            anchor="mm",
        )

        draw.multiline_text(
            (center_x, top + 30 + temp_draw.textbbox((0, 0), node["emoji"], font=emoji_font)[3] // 2 + 14),
            "\n".join(node["lines"]),
            font=text_font,
            fill=hex_to_rgb("#1A1A2E"),
            anchor="ma",
            align="center",
            spacing=10,
        )

        if index < len(node_specs) - 1:
            line_start = (center_x, bottom + 18)
            line_end = (center_x, bottom + step_gap - 18)
            draw.line([line_start, line_end], fill=hex_to_rgb(colors["line"]), width=5)
            arrow_tip = (center_x, bottom + step_gap - 4)
            draw.polygon(
                [
                    arrow_tip,
                    (center_x - 14, bottom + step_gap - 22),
                    (center_x + 14, bottom + step_gap - 22),
                ],
                fill=hex_to_rgb(colors["line"]),
            )

        y_offset += box_height + step_gap

    filename = f"flowchart_edu_{uuid.uuid4().hex[:8]}.png"
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
