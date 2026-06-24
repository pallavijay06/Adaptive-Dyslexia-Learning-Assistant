"""Tests for OCR fallback and local-first OCR optimization."""

from pathlib import Path

from PIL import Image
from services.ocr_service import extract_images_from_pdf, extract_text_from_image


def test_extract_text_from_image_local_ocr_success_skips_gemini(monkeypatch, tmp_path: Path):
    image_file = tmp_path / "ocr.png"
    image_file.write_bytes(b"PNG")

    called = {"gemini": False}

    def fake_tesseract(path):
        return "Newton's First Law", 85.0

    def fake_preprocessing(path):
        return "", None

    def fake_gemini(path):
        called["gemini"] = True
        return "Should not be called"

    monkeypatch.setattr("services.ocr_service._extract_with_tesseract", fake_tesseract)
    monkeypatch.setattr("services.ocr_service._extract_with_preprocessing", fake_preprocessing)
    monkeypatch.setattr("services.ocr_service._extract_with_gemini_vision", fake_gemini)

    text = extract_text_from_image(str(image_file))

    assert text == "Newton's First Law"
    assert called["gemini"] is False


def test_extract_text_from_image_invalid_local_ocr_uses_gemini_fallback(monkeypatch, tmp_path: Path):
    image_file = tmp_path / "ocr.png"
    image_file.write_bytes(b"PNG")

    def fake_tesseract(path):
        return "???", 90.0

    def fake_preprocessing(path):
        return "###", 90.0

    def fake_gemini(path):
        return "Force = Mass × Acceleration"

    monkeypatch.setattr("services.ocr_service._extract_with_tesseract", fake_tesseract)
    monkeypatch.setattr("services.ocr_service._extract_with_preprocessing", fake_preprocessing)
    monkeypatch.setattr("services.ocr_service._extract_with_gemini_vision", fake_gemini)

    text = extract_text_from_image(str(image_file))

    assert text == "Force = Mass × Acceleration"


def test_extract_images_from_pdf_writes_temporary_image_files(monkeypatch, tmp_path: Path):
    fake_image = Image.new("RGB", (10, 10), color="blue")

    class FakeImageObject:
        def __init__(self, image):
            self.image = image
            self.name = "diagram.png"
            self.data = None

    class FakePage:
        @property
        def images(self):
            return {"/I0": FakeImageObject(fake_image)}

    class FakePdfReader:
        def __init__(self, path):
            self.pages = [FakePage()]

    import sys
    fake_pypdf = type(sys)("pypdf")
    fake_pypdf.PdfReader = FakePdfReader
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%EOF")

    image_paths = extract_images_from_pdf(str(pdf_path))

    assert len(image_paths) == 1
    assert Path(image_paths[0]).exists()
