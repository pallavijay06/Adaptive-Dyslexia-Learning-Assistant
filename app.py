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
from services.quiz_service import (
    evaluate_mcq,
    evaluate_short_answer,
    generate_mcq_quiz,
    generate_short_questions,
)


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
        "quiz_mcqs": None,
        "quiz_short_questions": None,
        "quiz_answers": None,
        "quiz_short_answers": None,
        "quiz_report": None,
        "quiz_short_feedback": None,
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


def render_quiz_section() -> None:
    """Render the intelligent quiz mode UI."""
    st.header("📚 Quiz Mode")

    if not st.session_state.document_record:
        st.info("Upload and process a document first to generate a quiz.")
        return

    if st.button("Generate Quiz", type="primary"):
        with st.spinner("Generating quiz from your document..."):
            try:
                document_text = st.session_state.document_text or ""
                mcqs = generate_mcq_quiz(document_text, num_questions=8)
                short_questions = generate_short_questions(document_text, num_questions=4)
                st.session_state.quiz_mcqs = mcqs
                st.session_state.quiz_short_questions = short_questions
                st.session_state.quiz_answers = ["" for _ in mcqs]
                st.session_state.quiz_short_answers = ["" for _ in short_questions]
                st.session_state.quiz_report = None
                st.session_state.quiz_short_feedback = None
            except (DocumentError, GeminiConfigurationError, GeminiAPIError, ValueError) as exc:
                st.error(str(exc))
                return
            except Exception as exc:
                st.error(f"Quiz generation failed: {exc}")
                return

    if not st.session_state.quiz_mcqs or not st.session_state.quiz_short_questions:
        st.info("Generate a quiz to begin. The quiz will use the currently uploaded document.")
        return

    st.subheader("Multiple Choice Questions")
    for index, mcq in enumerate(st.session_state.quiz_mcqs):
        key = f"mcq_{index}"
        st.write(f"**{index + 1}. {mcq['question']}**")
        current_answer = st.session_state.quiz_answers[index] if st.session_state.quiz_answers else ""
        selected = st.radio(
            "Choose the best answer:",
            options=mcq["options"],
            key=key,
            index=mcq["options"].index(current_answer) if current_answer in mcq["options"] else 0,
        )
        if st.session_state.quiz_answers is None:
            st.session_state.quiz_answers = []
        if len(st.session_state.quiz_answers) < len(st.session_state.quiz_mcqs):
            st.session_state.quiz_answers = ["" for _ in st.session_state.quiz_mcqs]
        st.session_state.quiz_answers[index] = selected

    st.subheader("Short Answer Questions")
    for index, short_question in enumerate(st.session_state.quiz_short_questions):
        prompt = f"{index + 1}. {short_question['question']}"
        user_text = st.text_area(
            prompt,
            value=(st.session_state.quiz_short_answers[index] if st.session_state.quiz_short_answers else ""),
            key=f"short_{index}",
            height=120,
        )
        if st.session_state.quiz_short_answers is None:
            st.session_state.quiz_short_answers = []
        if len(st.session_state.quiz_short_answers) < len(st.session_state.quiz_short_questions):
            st.session_state.quiz_short_answers = ["" for _ in st.session_state.quiz_short_questions]
        st.session_state.quiz_short_answers[index] = user_text

    if st.button("Submit Quiz", type="secondary"):
        with st.spinner("Evaluating your quiz answers..."):
            try:
                report = evaluate_mcq(st.session_state.quiz_answers or [], st.session_state.quiz_mcqs or [])
                short_feedback = []
                for index, short_question in enumerate(st.session_state.quiz_short_questions or []):
                    student_response = st.session_state.quiz_short_answers[index] if st.session_state.quiz_short_answers else ""
                    if student_response.strip():
                        feedback = evaluate_short_answer(student_response, short_question["answer"])
                    else:
                        feedback = {
                            "score": 0,
                            "max_score": 5,
                            "result": "Incorrect",
                            "feedback": "No answer was provided.",
                            "improvement_tip": "Try to answer the question using a sentence or two from the document.",
                        }
                    short_feedback.append(
                        {
                            "question": short_question["question"],
                            "student_answer": student_response,
                            "expected_answer": short_question["answer"],
                            "evaluation": feedback,
                        }
                    )
                st.session_state.quiz_report = report
                st.session_state.quiz_short_feedback = short_feedback
            except (GeminiConfigurationError, GeminiAPIError, ValueError) as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Quiz evaluation failed: {exc}")

    if st.session_state.quiz_report:
        report = st.session_state.quiz_report
        st.subheader("Quiz Results")
        st.metric("Score", f"{report['score']}/{report['total']}")
        st.progress(report["percentage"] / 100 if report["total"] else 0)

        st.markdown("**Topic Analysis**")
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Strengths**")
            if report["strengths"]:
                for item in report["strengths"]:
                    st.write(f"- {item}")
            else:
                st.write("No clear strengths identified yet.")
        with cols[1]:
            st.markdown("**Weaknesses**")
            if report["weaknesses"]:
                for item in report["weaknesses"]:
                    st.write(f"- {item}")
            else:
                st.write("No clear weaknesses identified yet.")

        st.markdown("**Recommendations**")
        for recommendation in report["recommendations"]:
            st.write(f"- {recommendation}")

        st.markdown("**Revision Material**")
        for revision in report["revision_material"]:
            st.markdown(f"**{revision.get('topic', 'Topic')}**")
            st.write(revision.get("simple_explanation", ""))
            st.write(f"*{revision.get('revision_note', '')}*")
            st.write(f"Practice: {revision.get('practice_question', '')}")

    if st.session_state.quiz_short_feedback:
        st.subheader("Short Answer Feedback")
        for feedback_item in st.session_state.quiz_short_feedback:
            st.markdown(f"**{feedback_item['question']}**")
            st.write(f"Your answer: {feedback_item['student_answer']}")
            evaluation = feedback_item["evaluation"]
            st.write(f"Result: {evaluation.get('result')}")
            st.write(f"Feedback: {evaluation.get('feedback')}")
            st.write(f"Tip: {evaluation.get('improvement_tip')}")


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
    render_quiz_section()
    st.divider()
    render_simplified_content()
    st.divider()
    render_chat_section()


if __name__ == "__main__":
    main()
