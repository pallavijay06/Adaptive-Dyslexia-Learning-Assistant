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
2. The backend parser pipeline saves and extracts text.
3. The extracted text is chunked and embedded locally.
4. A FAISS vector index is built from the document chunks.
5. User questions retrieve only the top 3 relevant chunks.
6. Gemini answers first; if Gemini fails, Ollama is used as a fallback.

## Local RAG Architecture

- Upload
- Text extraction
- Chunking
- Local embeddings
- FAISS vector store
- Retriever
- Gemini primary
- Ollama fallback
- Answer returned

## Ollama Setup

Install Ollama and pull the Qwen model:

```powershell
# Install Ollama from https://ollama.com/docs
ollama pull qwen3:4b
```

Verify the model is runnable:

```powershell
ollama run qwen3:4b
```

## Backend Modules

- `backend/parser.py`: frontend-facing parser facade.
- `backend/rag.py`: document-aware question answering facade.
- `backend/llm.py`: Gemini helper facade.
- `backend/flask_app.py`: preserved Flask API entry point.
- `services/document_context.py`: upload saving, extraction, and document context.
- `services/gemini_service.py`: Gemini client, chat, simplification, quiz, summary, vocabulary.
