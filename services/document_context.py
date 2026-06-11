"""Document upload, extraction, and in-session context management.

Uploaded files are saved to uploads/, extracted text is saved to
extracted_content/, and lightweight document metadata is kept in memory for the
current backend process. The structure is intentionally ready for multiple
documents even though the latest uploaded document becomes the default context.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from shutil import copyfile
from threading import Lock
from uuid import uuid4

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from services import docx_parser, pdf_parser, ppt_parser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = PROJECT_ROOT / "uploads"
EXTRACTED_DIR = PROJECT_ROOT / "extracted_content"

ALLOWED_EXTENSIONS = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".txt"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class DocumentError(RuntimeError):
    """Raised for expected document upload or extraction failures."""


@dataclass(frozen=True)
class DocumentRecord:
    """Metadata for one uploaded document."""

    document_id: str
    original_filename: str
    saved_filename: str
    uploaded_path: str
    extracted_path: str
    file_type: str
    characters_extracted: int


_documents: dict[str, DocumentRecord] = {}
_active_document_id: str | None = None
_lock = Lock()


def process_uploaded_document(file: FileStorage) -> DocumentRecord:
    """Validate, save, parse, persist, and register an uploaded document."""
    if file is None or not file.filename:
        raise DocumentError("No file was uploaded.")

    original_filename = secure_filename(file.filename)
    if not original_filename:
        raise DocumentError("Uploaded file has an invalid filename.")

    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise DocumentError(f"Unsupported file type '{extension}'. Allowed: {allowed}.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    document_id = uuid4().hex
    saved_filename = f"{Path(original_filename).stem}_{document_id}{extension}"
    uploaded_path = UPLOAD_DIR / saved_filename
    file.save(uploaded_path)

    _validate_saved_file(uploaded_path)

    extracted_text = extract_text_from_file(uploaded_path)
    if not extracted_text:
        raise DocumentError("No readable text could be extracted from this document.")

    extracted_filename = f"{Path(original_filename).stem}_{document_id}.txt"
    extracted_path = EXTRACTED_DIR / extracted_filename
    extracted_path.write_text(extracted_text, encoding="utf-8")

    record = DocumentRecord(
        document_id=document_id,
        original_filename=original_filename,
        saved_filename=saved_filename,
        uploaded_path=str(uploaded_path),
        extracted_path=str(extracted_path),
        file_type=extension.lstrip("."),
        characters_extracted=len(extracted_text),
    )
    register_document(record)
    return record


def process_uploaded_bytes(filename: str, file_bytes: bytes) -> DocumentRecord:
    """Process an uploaded file represented by a filename and raw bytes.

    Streamlit uploads expose bytes rather than Flask's FileStorage object. This
    helper keeps Streamlit on the same validation, extraction, and context path.
    """
    if not file_bytes:
        raise DocumentError("Uploaded file is empty.")

    original_filename = secure_filename(filename or "")
    if not original_filename:
        raise DocumentError("Uploaded file has an invalid filename.")

    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise DocumentError(f"Unsupported file type '{extension}'. Allowed: {allowed}.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    document_id = uuid4().hex
    saved_filename = f"{Path(original_filename).stem}_{document_id}{extension}"
    uploaded_path = UPLOAD_DIR / saved_filename
    uploaded_path.write_bytes(file_bytes)

    return process_saved_document(uploaded_path, original_filename, document_id)


def process_saved_document(
    source_path: str | Path,
    original_filename: str | None = None,
    document_id: str | None = None,
) -> DocumentRecord:
    """Process a file that already exists on disk.

    If source_path is outside uploads/, the file is copied into uploads/ first.
    This is useful for local scripts and future ingestion jobs.
    """
    source = Path(source_path)
    if not source.exists() or not source.is_file():
        raise DocumentError("Document file does not exist.")

    original_filename = secure_filename(original_filename or source.name)
    if not original_filename:
        raise DocumentError("Document has an invalid filename.")

    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise DocumentError(f"Unsupported file type '{extension}'. Allowed: {allowed}.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    document_id = document_id or uuid4().hex
    saved_filename = f"{Path(original_filename).stem}_{document_id}{extension}"
    uploaded_path = UPLOAD_DIR / saved_filename

    if source.resolve() != uploaded_path.resolve():
        copyfile(source, uploaded_path)

    _validate_saved_file(uploaded_path)

    extracted_text = extract_text_from_file(uploaded_path)
    if not extracted_text:
        raise DocumentError("No readable text could be extracted from this document.")

    extracted_filename = f"{Path(original_filename).stem}_{document_id}.txt"
    extracted_path = EXTRACTED_DIR / extracted_filename
    extracted_path.write_text(extracted_text, encoding="utf-8")

    record = DocumentRecord(
        document_id=document_id,
        original_filename=original_filename,
        saved_filename=saved_filename,
        uploaded_path=str(uploaded_path),
        extracted_path=str(extracted_path),
        file_type=extension.lstrip("."),
        characters_extracted=len(extracted_text),
    )
    register_document(record)
    return record


def extract_text_from_file(path: str | Path) -> str:
    """Dispatch extraction to the correct parser based on file extension."""
    file_path = Path(path)
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return pdf_parser.extract_text(file_path)
    if extension == ".pptx":
        return ppt_parser.extract_text(file_path)
    if extension == ".docx":
        return docx_parser.extract_text(file_path)
    if extension == ".txt":
        return _extract_txt(file_path)
    if extension == ".ppt":
        raise DocumentError("Legacy .ppt files are accepted but not readable yet. Convert to .pptx and upload again.")
    if extension == ".doc":
        raise DocumentError("Legacy .doc files are accepted but not readable yet. Convert to .docx and upload again.")

    raise DocumentError(f"Unsupported file type: {extension}")


def register_document(record: DocumentRecord) -> None:
    """Add a document to the in-memory registry and make it active."""
    global _active_document_id

    with _lock:
        _documents[record.document_id] = record
        _active_document_id = record.document_id


def get_document(document_id: str | None = None) -> DocumentRecord | None:
    """Return the requested document, or the active document if no id is given."""
    with _lock:
        selected_id = document_id or _active_document_id
        if not selected_id:
            return None
        return _documents.get(selected_id)


def get_document_text(document_id: str | None = None) -> str | None:
    """Load extracted text for the requested or active document."""
    record = get_document(document_id)
    if record is None:
        return None

    path = Path(record.extracted_path)
    if not path.exists():
        raise DocumentError("Extracted document content is missing.")

    return path.read_text(encoding="utf-8")


def list_documents() -> list[dict[str, object]]:
    """Return registered document metadata for future multi-document UI work."""
    with _lock:
        return [asdict(record) for record in _documents.values()]


def active_document_metadata() -> dict[str, object] | None:
    """Return metadata for the active document."""
    record = get_document()
    return asdict(record) if record else None


def _extract_txt(path: Path) -> str:
    """Read TXT files with UTF-8 first, then a forgiving fallback."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore").strip()


def _validate_saved_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise DocumentError("Uploaded file could not be saved.")

    size = path.stat().st_size
    if size == 0:
        raise DocumentError("Uploaded file is empty.")
    if size > MAX_UPLOAD_BYTES:
        raise DocumentError("Uploaded file is too large. Maximum size is 25 MB.")
