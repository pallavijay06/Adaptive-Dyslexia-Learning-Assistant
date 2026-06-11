from pdf_parser import extract_text

text = extract_text("uploads/CN Unit 1 Slides.pdf")

print(text[:5000])  # Print first 5000 characters