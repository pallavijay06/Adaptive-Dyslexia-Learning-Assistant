# Dyslexia Learning Assistant

An AI-powered learning assistant that helps learners upload study material,
generate dyslexia-friendly simplified content, and ask questions about the
uploaded document using Gemini.

## Run

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the Streamlit frontend:

```powershell
streamlit run app.py
```

## Environment

Create `.env` in the project root or inside `services/`:

```env
GEMINI_API_KEY=your_api_key_here
```

## Flow

1. Upload a PDF, PPTX, or DOCX file.
2. The existing backend parser pipeline saves and extracts text.
3. Gemini generates simplified content.
4. Ask questions in the chat box.
5. Answers are generated using the uploaded document as context.

## Backend Modules

- `backend/parser.py`: frontend-facing parser facade.
- `backend/rag.py`: document-aware question answering facade.
- `backend/llm.py`: Gemini helper facade.
- `backend/flask_app.py`: preserved Flask API entry point.
- `services/document_context.py`: upload saving, extraction, and document context.
- `services/gemini_service.py`: Gemini client, chat, simplification, quiz, summary, vocabulary.
