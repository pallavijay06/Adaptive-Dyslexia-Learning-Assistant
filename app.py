"""Streamlit frontend for the Dyslexia Learning Assistant."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from backend.chunker import chunk_text
from backend.parser import process_uploaded_file
from backend.retriever import retrieve_relevant_chunks_for_question
from backend.vector_store import build_index
from services.document_context import DocumentError, get_document_text
from services.gemini_service import (
    GeminiAPIError,
    GeminiConfigurationError,
    simplify_document,
)
from services.llm_router import generate_answer


st.set_page_config(
    page_title="Dyslexia Learning Assistant",
    layout="wide",
)


def initialize_session_state() -> None:
    """Create Streamlit session keys used by upload, simplification, and chat."""
    defaults = {
        "uploaded_signature": None,
        "document_record": None,
        "document_text": None,
        "document_chunks": None,
        "document_index": None,
        "simplified_content": None,
        "chat_history": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_readable_styles() -> None:
    """Apply larger fonts, wider spacing, and high readability for learners."""
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
            font-size: 19px;
            line-height: 1.75;
        }
        .block-container {
            max-width: 1120px;
            padding-top: 2rem;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        .stMarkdown p, .stChatMessage {
            font-size: 19px;
            line-height: 1.75;
        }
        .document-meta {
            padding: 0.75rem 1rem;
            border-left: 5px solid #2e7d32;
            background: #f4fbf6;
            color: #18351f;
            margin: 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_home() -> None:
    """Render the page title and short product description."""
    st.title("Dyslexia Learning Assistant")
    st.write(
        "Upload learning material, receive a simplified version, and ask questions "
        "about the document in a clear conversational format."
    )


def render_upload_section() -> None:
    """Handle document upload, processing, and Gemini simplification."""
    st.header("Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a PDF, PPTX, or DOCX file",
        type=["pdf", "pptx", "docx"],
        accept_multiple_files=False,
    )

    if uploaded_file is None:
        return

    file_bytes = uploaded_file.getvalue()
    signature = (uploaded_file.name, len(file_bytes))

    if st.session_state.uploaded_signature == signature and st.session_state.document_record:
        render_document_status()
        return

    if st.button("Process Document", type="primary"):
        with st.spinner("Processing document and creating simplified content..."):
            try:
                record = process_uploaded_file(uploaded_file.name, file_bytes)
                document_text = get_document_text(record.document_id)
                simplified_content = simplify_document(document_text or "")
                document_chunks = chunk_text(document_text or "")
                document_index = build_index(document_chunks)
            except (DocumentError, GeminiConfigurationError, GeminiAPIError, ValueError) as exc:
                st.error(str(exc))
                return
            except Exception as exc:
                st.error(f"Document processing failed: {exc}")
                return

        st.session_state.uploaded_signature = signature
        st.session_state.document_record = record
        st.session_state.document_text = document_text
        st.session_state.document_chunks = document_chunks
        st.session_state.document_index = document_index
        st.session_state.simplified_content = simplified_content
        st.session_state.chat_history = []
        render_document_status()


def render_document_status() -> None:
    """Show metadata for the processed document."""
    record = st.session_state.document_record
    if not record:
        return

    st.markdown(
        f"""
        <div class="document-meta">
            <strong>{Path(record.original_filename).name}</strong><br>
            {record.characters_extracted:,} characters extracted
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_simplified_content() -> None:
    """Display Gemini-generated simplified content."""
    st.header("Simplified Content")
    content = st.session_state.simplified_content
    if not content:
        st.info("Upload and process a document to see simplified content.")
        return

    st.markdown(content)


def render_chat_section() -> None:
    """Render document-aware chat using the existing RAG/backend functions."""
    st.header("Chat with Document")

    if not st.session_state.document_record:
        st.info("Process a document first, then ask questions about it.")
        return

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_question = st.chat_input("Ask a question about the uploaded document")
    if not user_question:
        return

    st.session_state.chat_history.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                vector_store = st.session_state.document_index
                if vector_store is None:
                    document_text = st.session_state.document_text or ""
                    document_chunks = chunk_text(document_text)
                    vector_store = build_index(document_chunks)
                    st.session_state.document_chunks = document_chunks
                    st.session_state.document_index = vector_store

                relevant_chunks = retrieve_relevant_chunks_for_question(
                    user_question,
                    vector_store,
                    top_k=3,
                )
                context = "\n\n".join(chunk["text"] for chunk in relevant_chunks)
                answer = generate_answer(user_question, context)
            except (DocumentError, GeminiConfigurationError, GeminiAPIError, ValueError) as exc:
                answer = str(exc)
            except Exception as exc:
                answer = f"Chat failed: {exc}"

        st.markdown(answer)

    st.session_state.chat_history.append({"role": "assistant", "content": answer})


def main() -> None:
    """Run the Streamlit app."""
    initialize_session_state()
    apply_readable_styles()
    render_home()
    render_upload_section()
    st.divider()
    render_simplified_content()
    st.divider()
    render_chat_section()


if __name__ == "__main__":
    main()
