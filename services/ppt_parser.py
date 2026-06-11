from pathlib import Path
from zipfile import BadZipFile, ZipFile
import re
import xml.etree.ElementTree as ET


class PPTParseError(RuntimeError):
    """Raised when a PPTX cannot be read as text."""


DRAWING_NAMESPACE = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
SLIDE_RE = re.compile(r"ppt/slides/slide(\d+)\.xml$")


def extract_text(file_path: str | Path) -> str:
    """Extract readable text from a PPTX file using the built-in ZIP/XML format."""
    path = Path(file_path)
    _validate_file(path)

    try:
        with ZipFile(path) as pptx:
            slide_names = sorted(
                (name for name in pptx.namelist() if SLIDE_RE.match(name)),
                key=_slide_number,
            )
            slides = [_extract_slide_text(pptx.read(name)) for name in slide_names]
    except BadZipFile as exc:
        raise PPTParseError(f"'{path.name}' is not a valid PPTX file.") from exc

    sections = []
    for index, slide_text in enumerate(slides, start=1):
        if slide_text:
            sections.append(f"Slide {index}\n{slide_text}")

    return "\n\n".join(sections).strip()


def parse_ppt(file_path: str | Path) -> str:
    """Backward-friendly alias for extract_text."""
    return extract_text(file_path)


def parse_pptx(file_path: str | Path) -> str:
    """Alias for code that names PowerPoint files by their modern extension."""
    return extract_text(file_path)


def _extract_slide_text(slide_xml: bytes) -> str:
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError as exc:
        raise PPTParseError("Could not parse slide XML.") from exc

    text_runs = [
        node.text.strip()
        for node in root.iter(f"{DRAWING_NAMESPACE}t")
        if node.text and node.text.strip()
    ]
    return "\n".join(text_runs).strip()


def _slide_number(name: str) -> int:
    match = SLIDE_RE.match(name)
    return int(match.group(1)) if match else 0


def _validate_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"PPTX file not found: {path}")
    if not path.is_file():
        raise PPTParseError(f"Expected a PPTX file, got a folder: {path}")
    if path.suffix.lower() != ".pptx":
        raise PPTParseError(f"Expected a .pptx file, got: {path.name}")
