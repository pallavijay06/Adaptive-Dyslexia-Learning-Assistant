# Dyslexia Learning Assistant

An AI-powered learning assistant that helps learners upload study material,
generate dyslexia-friendly simplified content, and ask questions about the
uploaded document using OpenAI first, with Gemini and Ollama fallbacks.

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
OPENAI_API_KEY=YOUR_KEY_HERE
OPENAI_MODEL=gpt-5

# Optional fallbacks
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash
```

## Flow

1. Upload a PDF, PPTX, or DOCX file.
2. The backend parser pipeline saves and extracts text.
3. The extracted text is chunked and embedded locally.
4. A FAISS vector index is built from the document chunks.
5. User questions retrieve only the top 3 relevant chunks.
6. OpenAI answers first; if OpenAI fails, Gemini is tried, then Ollama.

## Local RAG Architecture

- Upload
- Text extraction
- Chunking
- Local embeddings
- FAISS vector store
- Retriever
- OpenAI primary
- Gemini fallback
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
- `backend/llm.py`: backward-compatible LLM helper facade.
- `backend/flask_app.py`: preserved Flask API entry point.
- `services/document_context.py`: upload saving, extraction, and document context.
- `services/openai_service.py`: OpenAI client for primary text generation.
- `services/llm_router.py`: OpenAI -> Gemini -> Ollama provider routing.
- `services/gemini_service.py`: Gemini fallback client and legacy helpers.
