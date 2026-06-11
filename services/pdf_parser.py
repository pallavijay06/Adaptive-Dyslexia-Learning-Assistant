from pathlib import Path


class PDFParseError(RuntimeError):
    """Raised when a PDF cannot be read as text."""


def extract_text(file_path: str | Path) -> str:
    """Extract readable text from a PDF file.

    The function tries common PDF libraries in order. Install one of these if
    PDF uploads fail: pypdf, PyPDF2, or pdfplumber.
    """
    path = Path(file_path)
    _validate_file(path)

    errors: list[str] = []

    for parser in (_extract_with_pypdf, _extract_with_pypdf2, _extract_with_pdfplumber):
        try:
            text = parser(path)
        except ImportError as exc:
            errors.append(str(exc))
            continue
        except Exception as exc:
            raise PDFParseError(f"Failed to parse PDF '{path.name}': {exc}") from exc

        cleaned = _clean_text(text)
        if cleaned:
            return cleaned

    install_hint = "Install a PDF parser with: pip install pypdf"
    if errors:
        raise PDFParseError(f"No supported PDF parser is installed. {install_hint}")

    raise PDFParseError(f"No readable text found in PDF '{path.name}'.")


def parse_pdf(file_path: str | Path) -> str:
    """Backward-friendly alias for extract_text."""
    return extract_text(file_path)


def _extract_with_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("pypdf is not installed.") from exc

    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_with_pypdf2(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError as exc:
        raise ImportError("PyPDF2 is not installed.") from exc

    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_with_pdfplumber(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError("pdfplumber is not installed.") from exc

    with pdfplumber.open(str(path)) as pdf:
        return "\n\n".join(page.extract_text() or "" for page in pdf.pages)


def _validate_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    if not path.is_file():
        raise PDFParseError(f"Expected a PDF file, got a folder: {path}")
    if path.suffix.lower() != ".pdf":
        raise PDFParseError(f"Expected a .pdf file, got: {path.name}")


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()
