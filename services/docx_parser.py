from pathlib import Path
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET


class DOCXParseError(RuntimeError):
    """Raised when a DOCX cannot be read as text."""


WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_text(file_path: str | Path) -> str:
    """Extract readable text from a DOCX file using the built-in ZIP/XML format."""
    path = Path(file_path)
    _validate_file(path)

    try:
        with ZipFile(path) as docx:
            document_xml = docx.read("word/document.xml")
    except KeyError as exc:
        raise DOCXParseError(f"'{path.name}' does not contain word/document.xml.") from exc
    except BadZipFile as exc:
        raise DOCXParseError(f"'{path.name}' is not a valid DOCX file.") from exc

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        raise DOCXParseError(f"Could not parse document XML in '{path.name}'.") from exc

    paragraphs = []
    for paragraph in root.iter(f"{WORD_NAMESPACE}p"):
        text = _paragraph_text(paragraph)
        if text:
            paragraphs.append(text)

    return "\n\n".join(paragraphs).strip()


def parse_docx(file_path: str | Path) -> str:
    """Backward-friendly alias for extract_text."""
    return extract_text(file_path)


def _paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []

    for node in paragraph.iter():
        if node.tag == f"{WORD_NAMESPACE}t" and node.text:
            parts.append(node.text)
        elif node.tag == f"{WORD_NAMESPACE}tab":
            parts.append("\t")
        elif node.tag == f"{WORD_NAMESPACE}br":
            parts.append("\n")

    return "".join(parts).strip()


def _validate_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {path}")
    if not path.is_file():
        raise DOCXParseError(f"Expected a DOCX file, got a folder: {path}")
    if path.suffix.lower() != ".docx":
        raise DOCXParseError(f"Expected a .docx file, got: {path.name}")
