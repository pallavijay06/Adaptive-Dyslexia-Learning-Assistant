# test_ocr.py

from services.ocr_service import extract_text_from_image

text = extract_text_from_image("sample1.png")

print(text)