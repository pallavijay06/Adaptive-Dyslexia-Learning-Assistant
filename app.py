"""Streamlit frontend for the Dyslexic Learning Assistant.

Features:
- Document Upload (PDF, PPTX, DOCX)
- Image OCR (PNG, JPG, GIF, WebP)
- Simplified Content Generation
- Text-to-Speech Audio (with natural text cleaning)
- Visual Learning (Flowcharts, Mind Maps)
- Multi-mode Learning (Read, Listen, Visual Learn)
- RAG-based Chat with Documents
- Interactive vocabulary learning inline with reading
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from backend.chunker import chunk_text
from backend.parser import process_uploaded_file
from backend.retriever import retrieve_relevant_chunks_for_question
from backend.vector_store import build_index
from database.db import (
    attach_learning_support_logs_to_quiz,
    save_document,
    save_learning_support_log,
    save_learning_session,
    save_quiz_question_responses,
    save_quiz_score,
    save_user,
    save_chat,
    get_user,
    update_user_last_login,
    update_user_logout,
)
from components.accessibility.read_mode_accessibility import render_read_mode_accessibility_panel
from components.reading.reading_view import (
    render_key_takeaways,
    render_learning_mode_switcher,
    render_read_mode as render_reading_mode,
)
from components.session_state import (
    get_ui_preferences,
    initialize_learning_mode,
    initialize_ui_preferences,
)
from components.progress_dashboard import render_dashboard
from components.quiz_interactive import (
    initialize_quiz_session_state,
    mark_question_completed,
    _start_question_viewing,
    get_quiz_submission_attempt_metadata,
    render_quiz_progress_indicator,
    render_quiz_question,
    render_question_timer,
    render_hint_button,
    get_current_question_time_seconds,
    format_time_seconds,
    persist_question_timing,
    get_quiz_summary,
)
from services.auth_service import (
    hash_password,
    normalize_email,
    verify_password,
    validate_email,
    validate_registration_fields,
)
from services.document_context import DocumentError, get_document_text
from services.gemini_service import (
    GeminiAPIError,
    GeminiConfigurationError,
)
from services.quiz_service import (
    combine_quiz_report_with_short_answers,
    evaluate_mcq,
    evaluate_short_answer,
    evaluate_short_answer_locally,
    generate_mcq_quiz,
    generate_personalized_quiz_feedback,
    generate_short_questions,
)
from services.progress_dashboard_service import calculate_quiz_comprehension_score
from services.quiz_hint_service import generate_quiz_hint, generate_short_answer_hint
from services.adaptive_tutor import AdaptiveAITutor
from services.llm_router import generate_answer, LLMRouterError
from services.ocr_service import (
    extract_images_from_pdf,
    extract_text_from_image,
    extract_text_from_pdf_images,
    OCRError,
)
from services.simplification_service import simplify_text, SimplificationError
from services.vocabulary_service import generate_vocabulary, VocabularyError, explain_word
from services.tts_service import cleanup_audio_file, generate_audio, split_text_into_sentences, TTSError
from services.visual_service import generate_visual_content, VisualError
from backend.stem.stem_page import render_stem_mode

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logger.debug("app module loaded as %s", __name__)


st.set_page_config(
    page_title="Dyslexic Learning Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_session_state() -> None:
    """Create Streamlit session keys for backend state."""
    defaults = {
        # Document processing
        "uploaded_signature": None,
        "document_record": None,
        "document_text": None,
        "document_chunks": None,
        "document_index": None,

        # Learning mode state
        "selected_learning_mode": None,  # Tracks which mode is selected (None = no mode selected)

        # Generated content
        "simplified_content": None,
        "visual_content": None,
        "audio_file": None,
        "selected_visual": None,
        "visual_choice": "Select a visual type",

        # Chat
        "chat_history": [],
        "quiz_mcqs": None,
        "quiz_short_questions": None,
        "quiz_answers": None,
        "quiz_short_answers": None,
        "quiz_report": None,
        "quiz_short_feedback": None,
        "quiz_question_start_times": {},

        # STEM PDF image extraction
        "document_diagram_images": [],

        # Caching
        "vocab_explain_cache": {},
        # Authentication state
        "current_user_id": None,
        "current_user_name": None,
        "login_timestamp": None,
        "authenticated": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Ensure authentication flag and current_user_id remain consistent.
    if st.session_state.get("authenticated") and st.session_state.get("current_user_id") is None:
        st.session_state.authenticated = False


def _handle_login(email: str, password: str) -> bool:
    """Authenticate the user and initialize session state."""
    normalized_email = normalize_email(email)
    is_valid, error_message = validate_email(normalized_email)
    if not is_valid:
        st.error(error_message)
        return False

    user = get_user(normalized_email)
    if user is None or not verify_password(password, user.password_hash):
        st.error("Invalid email or password.")
        return False

    st.session_state.current_user_id = user.id
    st.session_state.current_user_name = user.name
    st.session_state.login_timestamp = datetime.utcnow()
    st.session_state.authenticated = True
    st.success(f"Welcome back, {user.name}!")
    st.rerun()
    return True


def _handle_registration(
    full_name: str,
    email: str,
    password: str,
    confirm_password: str,
    age: str,
    grade: str,
    institution: str,
    field_of_study: str,
    preferred_language: str,
    learning_goal: str,
    dyslexia_status: str,
) -> bool:
    """Validate and register a new user."""
    valid, error_message = validate_registration_fields(
        full_name,
        email,
        password,
        confirm_password,
        age,
        grade,
        institution,
        field_of_study,
    )
    if not valid:
        st.error(error_message)
        return False

    normalized_email = normalize_email(email)
    if get_user(normalized_email) is not None:
        st.error("A user with that email already exists.")
        return False

    try:
        user = save_user(
            name=full_name.strip(),
            email=normalized_email,
            password_hash=hash_password(password),
            age=int(age.strip()),
            grade=grade.strip(),
            institution=institution.strip(),
            field_of_study=field_of_study.strip(),
            preferred_language=preferred_language.strip() or None,
            learning_goal=learning_goal.strip() or None,
            dyslexia_status=dyslexia_status.strip() or None,
            registration_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
    except ValueError as exc:
        st.error(str(exc))
        return False

    st.session_state.current_user_id = user.id
    st.session_state.current_user_name = user.name
    st.session_state.login_timestamp = datetime.utcnow()
    st.session_state.authenticated = True
    st.success(f"Account created. Welcome, {user.name}!")
    st.rerun()
    return True


def render_login_page() -> None:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        submit = st.form_submit_button("Login")

        if submit:
            _handle_login(email, password)


def render_registration_page() -> None:
    with st.form("register_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        age = st.text_input("Age")
        grade = st.text_input("Grade / College Year")
        institution = st.text_input("Institution")
        field_of_study = st.text_input("Field of Study")
        preferred_language = st.text_input("Preferred Language (Optional)")
        learning_goal = st.text_input("Learning Goal (Optional)")
        dyslexia_status = st.text_input("Dyslexia Status (Optional)")

        submit = st.form_submit_button("Register")

        if submit:
            _handle_registration(
                full_name,
                email,
                password,
                confirm_password,
                age,
                grade,
                institution,
                field_of_study,
                preferred_language,
                learning_goal,
                dyslexia_status,
            )
            
def render_authentication() -> None:
    """Render the authentication screen."""

    st.title("🎓 Dyslexic Learning Assistant")
    st.markdown("### Welcome!")
    st.write(
        "Please log in or create an account to continue using the Adaptive Dyslexic Learning Assistant."
    )

    auth_page = st.radio(
        "Choose an option",
        ("Login", "Register"),
        horizontal=True,
        key="auth_page_selection",
    )

    st.markdown("---")

    if auth_page == "Login":
        render_login_page()
    else:
        render_registration_page()

def logout_user() -> None:
    """Log the current user out, persist auth timestamps, and clear session state."""
    if not st.session_state.authenticated or st.session_state.current_user_id is None:
        return

    login_time = st.session_state.login_timestamp or datetime.utcnow()
    logout_time = datetime.utcnow()
    duration_minutes = max(
        1,
        int((logout_time - login_time).total_seconds() / 60),
    )

    update_user_last_login(st.session_state.current_user_id, login_time)
    update_user_logout(st.session_state.current_user_id, logout_time)
    save_learning_session(
        user_id=st.session_state.current_user_id,
        mode_used="authentication",
        duration=duration_minutes,
        login_time=login_time,
        logout_time=logout_time,
        session_duration_minutes=duration_minutes,
    )

    st.session_state.clear()
    initialize_session_state()
    st.rerun()


def render_sidebar_user_panel() -> None:
    """Render the authenticated user panel and logout button in the sidebar."""
    with st.sidebar:
        st.markdown("### Account")
        st.write(f"**{st.session_state.current_user_name or 'Learner'}**")
        if st.button("Logout"):
            logout_user()



def show_user_error(message: str, exc: Exception | None = None) -> None:
    """Show a friendly message while logging technical details."""
    if exc is not None:
        logger.exception("%s", message)
    st.error(message)


def apply_dyslexia_friendly_styles() -> None:
    """Apply global accessibility styles from the unified UI preferences."""
    initialize_ui_preferences()
    preferences = get_ui_preferences()

    from components.ui_constants import CHARACTER_SPACING, FONT_SIZES, THEMES

    theme = THEMES[preferences["theme"]]
    font_size = FONT_SIZES[preferences["font_size"]]
    character_spacing = CHARACTER_SPACING[preferences["character_spacing"]]
    font_family = preferences["font_family"]

    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: '{font_family}', sans-serif;
            color: {theme['text_color']};
            background-color: {theme['background_color']};
            letter-spacing: {character_spacing};
        }}

        .stApp {{
            background-color: {theme['background_color']};
        }}

        .block-container {{
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}

        h1, h2, h3, h4 {{
            letter-spacing: 0.02em;
            margin-top: 1.5rem !important;
            margin-bottom: 1rem !important;
            line-height: 1.4 !important;
        }}

        .stMarkdown p, .stChatMessage, .stTextInput, .stSelectbox, .stRadio, .stButton > button {{
            font-size: {font_size}px !important;
            line-height: 1.8 !important;
            letter-spacing: {character_spacing} !important;
        }}

        input, textarea, .stTextInput, .stSelectbox {{
            font-size: {font_size}px !important;
            letter-spacing: {character_spacing} !important;
        }}

        .streamlit-expanderHeader {{
            font-size: {font_size}px !important;
            font-weight: 500 !important;
        }}

        hr {{
            margin: 2rem 0;
            border: none;
            border-top: 2px solid {theme['border_color']};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_accessibility_settings() -> None:
    """Deprecated: accessibility sidebar is now rendered through Prototype 2 components."""
    pass


def render_home() -> None:
    """Render welcome and instructions."""
    st.title("🎓 Dyslexic Learning Assistant")
    st.subheader("Learn in your favorite way: Read, Listen, or Visualize")
    
    st.write(
        """
        Welcome! This assistant helps you learn better by:
        
        📄 **Upload Documents** - PDF, PPTX, DOCX, or Images  
        ✨ **Simplified Notes** - Short sentences and bullet points  
        🔤 **Learn Words** - See difficult words with simple meanings  
        🎵 **Listen** - Generate audio of content  
        📊 **Visualize** - See flowcharts and concept maps  
        🔍 **Explore Words** - Get meanings of any word
        """
    )


def render_upload_section() -> None:
    """Handle document and image uploads with OCR support."""
    st.header("📤 Upload Content")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Documents")
        doc_file = st.file_uploader(
            "Upload: PDF, PPTX, or DOCX",
            type=["pdf", "pptx", "docx"],
            key="doc_upload"
        )
        
        if doc_file is not None:
            if st.button("Process Document", type="primary", key="process_doc"):
                _process_document(doc_file)
    
    with col2:
        st.subheader("Images & Scanned PDFs")
        image_file = st.file_uploader(
            "Upload: PNG, JPG, GIF, WebP, or Scanned PDF",
            type=["png", "jpg", "jpeg", "gif", "webp", "pdf"],
            key="image_upload"
        )
        
        if image_file is not None:
            if st.button("Extract Text (OCR)", type="primary", key="ocr_btn"):
                _process_image_ocr(image_file)


def _process_document(uploaded_file) -> None:
    """Process uploaded document and extract content."""
    with st.spinner("📖 Processing document..."):
        try:
            file_bytes = uploaded_file.getvalue()
            record = process_uploaded_file(uploaded_file.name, file_bytes)
            document_text = get_document_text(record.document_id)

            # Persist the uploaded document and extracted text to SQLite so the
            # Streamlit client and Flask backend share the same store of records.
            user_id = st.session_state.current_user_id
            saved_document = save_document(
                user_id=user_id,
                file_name=record.original_filename,
                file_type=Path(record.original_filename).suffix.lstrip("."),
                document_text=document_text or "",
            )

            # Expose saved DB id to the session so chat turns can reference it.
            print(f"Saved document: {record.original_filename}")
            st.session_state.saved_document_id = saved_document.id

            st.session_state.document_record = record
            st.session_state.document_text = document_text
            st.session_state.document_chunks = chunk_text(document_text or "")
            st.session_state.document_index = build_index(st.session_state.document_chunks)
            st.session_state.simplified_content = None
            st.session_state.vocabulary = None
            st.session_state.visual_content = None
            st.session_state.chat_history = []
            st.session_state.document_diagram_images = []
            if record.file_type == "pdf":
                try:
                    st.session_state.document_diagram_images = extract_images_from_pdf(record.uploaded_path)
                except Exception:
                    st.session_state.document_diagram_images = []
            
            st.success(f"✅ Document processed: {Path(record.original_filename).name}")
            st.info(f"📊 {record.characters_extracted:,} characters extracted")
            
        except (DocumentError, GeminiConfigurationError, GeminiAPIError, ValueError) as exc:
            show_user_error("Document processing failed. Please try another file or check that it contains readable text.", exc)
        except Exception as exc:
            show_user_error("Something went wrong while processing the document. Please try again.", exc)


def _process_image_ocr(image_file) -> None:
    """Process image file with OCR."""
    with st.spinner("🔍 Extracting text from image..."):
        try:
            # Save temp file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(image_file.name).suffix) as tmp:
                tmp.write(image_file.getvalue())
                temp_path = tmp.name
            
            try:
                # Extract text
                if image_file.name.lower().endswith(".pdf"):
                    text = extract_text_from_pdf_images(temp_path)
                    try:
                        st.session_state.document_diagram_images = extract_images_from_pdf(temp_path)
                    except Exception:
                        st.session_state.document_diagram_images = []
                else:
                    text = extract_text_from_image(temp_path)
                
                if text and text.strip():
                    # Use extracted text as document
                    st.session_state.document_text = text
                    st.session_state.document_chunks = chunk_text(text)
                    st.session_state.document_index = build_index(st.session_state.document_chunks)
                    st.session_state.simplified_content = None
                    st.session_state.vocabulary = None
                    st.session_state.visual_content = None
                    st.session_state.chat_history = []
                    st.session_state.document_record = type('obj', (object,), {
                        'original_filename': image_file.name,
                        'characters_extracted': len(text)
                    })()
                    
                    st.success(f"✅ Text extracted from {image_file.name}")
                    st.info(f"📊 {len(text):,} characters extracted")
                    
                    # Show preview
                    with st.expander("👀 Preview extracted text"):
                        st.text(text[:500] + "..." if len(text) > 500 else text)
                else:
                    st.warning("⚠️ No text could be extracted from the image")
            finally:
                # Clean up temp file
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
        except OCRError as exc:
            show_user_error("OCR could not read text from this image. Try a clearer image or another file.", exc)
        except Exception as exc:
            show_user_error("Something went wrong during OCR. Please try again.", exc)


def render_learning_modes() -> None:
    """Render learning mode selector with Read, Listen, Visual Learn, and Quiz.
    
    No mode is selected by default. Content only renders after explicit user selection.
    """
    if not st.session_state.document_text:
        st.info("📤 Upload a document or image first to get started!")
        return

    st.header("🎯 Choose Your Learning Mode")
    
    # Display learning mode selector with "Select a Mode" as default (no auto-selection)
    selected_mode = st.radio(
        "Select a learning mode:",
        ["Select a Mode", "📖 Read", "🔊 Listen", "🧠 Visual Learn", "📝 Quiz", "🧮 STEM Support"],
        horizontal=True,
        index=0,  # First option is always default
    )
    st.session_state.selected_learning_mode = selected_mode
    st.divider()

    # Only render content if a real mode is selected (not the placeholder)
    if selected_mode == "Select a Mode":
        st.info("👆 Please choose a learning mode to get started.")
    elif selected_mode == "📖 Read":
        render_read_mode()
    elif selected_mode == "🔊 Listen":
        render_listen_mode()
    elif selected_mode == "🧠 Visual Learn":
        render_visual_mode()
    elif selected_mode == "📝 Quiz":
        render_quiz_section()
    elif selected_mode == "🧮 STEM Support":
        # Use the uploaded document text as STEM input; do not prompt for uploads here.
        document_text = st.session_state.document_text or ""
        if not document_text:
            st.info("Upload a document first to use STEM Support.")
        else:
            diagram_images: list[str] = st.session_state.document_diagram_images or []
            render_stem_mode(document_text=document_text, diagram_images=diagram_images)


def render_read_mode() -> None:
    """Render Read mode with simplified notes, takeaways, and vocabulary."""
    st.subheader("📖 Read Mode")

    with st.expander("✨ Simplified notes and reading experience", expanded=True):
        render_read_mode_accessibility_panel()

        if st.button("Generate Simplified Version", key="gen_simplify"):
            _log_learning_support_event("simplify")
            with st.spinner("Simplifying text..."):
                try:
                    content = simplify_text(st.session_state.document_text)
                    st.session_state.simplified_content = content
                    st.success("✅ Simplified content generated!")
                except (SimplificationError, LLMRouterError) as exc:
                    show_user_error("Simplification could not be completed right now. Please try again.", exc)

        if st.session_state.simplified_content:
            render_reading_mode(st.session_state.simplified_content)
            render_key_takeaways(st.session_state.simplified_content)
            st.download_button(
                label="⬇️ Download Simplified Text",
                data=st.session_state.simplified_content,
                file_name="simplified_notes.txt",
                mime="text/plain",
                key="download_simplified"
            )
        else:
            st.info("Generate a simplified version to view the dyslexia-friendly reading experience. Important words will be highlighted—click them to learn meanings!")



def render_listen_mode() -> None:
    """Render Listen mode with audio generation and playback.
    
    Audio is automatically cleaned for natural speech before generation.
    """
    st.subheader("🎵 Listen Mode")
    
    st.markdown("**Generate audio of your content and listen to it!**")
    st.info(
        "💡 **Note:** Audio is automatically cleaned to sound natural - "
        "punctuation, special symbols, and formatting are removed for better speech."
    )
    
    # Choose what to listen to
    listen_option = st.radio(
        "What would you like to listen to?",
        ["Original Text", "Simplified Version"],
        key="listen_option"
    )
    
    if listen_option == "Simplified Version" and not st.session_state.simplified_content:
        st.info("Generate simplified content first in Read Mode!")
        return
    
    text_to_listen = (
        st.session_state.simplified_content 
        if listen_option == "Simplified Version"
        else st.session_state.document_text
    )
    
    if st.button("🎙️ Generate Audio", type="primary", key="gen_audio"):
        _log_learning_support_event("audio")
        with st.spinner("Generating audio..."):
            try:
                previous_audio = st.session_state.get("audio_file")
                if previous_audio and os.path.exists(previous_audio):
                    cleanup_audio_file(previous_audio)

                audio_path = generate_audio(text_to_listen)
                st.session_state.audio_file = audio_path
                st.success("✅ Audio generated!")
            except TTSError as exc:
                show_user_error("Audio generation failed. Try a shorter text selection.", exc)
    
    if st.session_state.audio_file and os.path.exists(st.session_state.audio_file):
        st.markdown("### 🎧 Play Audio")
        with open(st.session_state.audio_file, "rb") as audio_file:
            audio_data = audio_file.read()

        audio_base64 = base64.b64encode(audio_data).decode("ascii")
        sentences = split_text_into_sentences(text_to_listen)
        sentences_b64 = base64.b64encode(json.dumps(sentences).encode('utf-8')).decode('ascii')
        full_text_b64 = base64.b64encode(text_to_listen.encode('utf-8')).decode('ascii')
        audio_html = f"""
        <style>
            #ttsAudio::-webkit-media-controls-playback-rate-button {{
                display: none !important;
            }}
            #ttsAudio::-moz-media-controls-playback-rate-button {{
                display: none !important;
            }}
            #ttsAudio::-ms-media-controls-playback-rate-button {{
                display: none !important;
            }}
            .audio-player-container {{
                max-width: 100%;
            }}
            .speed-buttons {{
                margin-top: 12px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }}
            .speed-button {{
                padding: 10px 16px;
                border-radius: 999px;
                border: 1px solid rgba(255, 255, 255, 0.22);
                background-color: rgba(255, 255, 255, 0.05);
                color: #f8fafc;
                font-weight: 600;
                cursor: pointer;
                transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
            }}
            .speed-button:hover {{
                background-color: rgba(255, 255, 255, 0.12);
                transform: translateY(-1px);
            }}
            .speed-button.active {{
                background-color: rgba(255, 214, 88, 0.28);
                border-color: rgba(255, 214, 88, 0.75);
            }}
            .listen-text-container {{
                margin-top: 18px;
                padding: 18px 18px;
                border-radius: 18px;
                background-color: rgba(15, 23, 42, 0.97);
                color: #f8fafc;
                line-height: 1.9;
                font-size: 1.08rem;
                letter-spacing: 0.01em;
                word-break: break-word;
                word-wrap: break-word;
                white-space: normal;
            }}
            .listen-text-header {{
                margin: 0 0 16px 0;
                font-size: 1.1rem;
                font-weight: 700;
                color: #f8fafc;
            }}
            .listen-sentence {{
                display: inline;
                padding: 0;
                margin: 0;
                border-radius: 6px;
                transition: background-color 0.15s ease, box-shadow 0.15s ease;
                background-color: transparent;
            }}
            .listen-sentence.active {{
                background-color: rgba(255, 214, 88, 0.28);
                box-shadow: 0 0 0 2px rgba(255, 214, 88, 0.4), inset 0 0 0 1px rgba(255, 214, 88, 0.2);
                padding: 2px 6px;
                border-radius: 8px;
            }}
            @media (max-width: 768px) {{
                .listen-text-container {{
                    padding: 16px;
                    font-size: 1rem;
                    line-height: 1.8;
                }}
            }}
        </style>
        <div class='audio-player-container'>
            <audio id='ttsAudio' controls controlsList='nodownload' style='width: 100%; display: block; min-height: 48px;'>
                <source src='data:audio/mp3;base64,{audio_base64}' type='audio/mpeg'>
                Your browser does not support HTML5 audio.
            </audio>
            <div class='speed-buttons' id='speedButtons'></div>
            <div id='sentenceContainer' class='listen-text-container' aria-live='polite'></div>
            <div id='fullTextContainer' class='listen-text-container' aria-live='polite'></div>
        </div>
        <script>
            const sentences = JSON.parse(atob('{sentences_b64}'));
            const fullText = atob('{full_text_b64}');
            const sentenceContainer = document.getElementById('sentenceContainer');
            const fullTextContainer = document.getElementById('fullTextContainer');
            const audioElem = document.getElementById('ttsAudio');
            const speedButtons = document.getElementById('speedButtons');
            const speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
            let activeSentence = -1;
            const sentenceWeights = sentences.map(function(sentence) {{
                return Math.max(1, sentence.trim().split(/\\s+/).length);
            }});
            const sentenceTimings = [];

            console.log('Sentence count:', sentences.length);
            console.log('Full text length:', fullText.length);
            console.log('Sentences array:', sentences);

            function createSpeedButtons() {{
                speedButtons.innerHTML = '';
                speeds.forEach(function(speed) {{
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'speed-button';
                    button.dataset.speed = speed;
                    button.textContent = speed + 'x';
                    if (speed === 1.0) {{
                        button.classList.add('active');
                    }}
                    button.addEventListener('click', function() {{
                        audioElem.playbackRate = parseFloat(this.dataset.speed);
                        updateSpeedButtons();
                    }});
                    speedButtons.appendChild(button);
                }});
            }}

            function updateSpeedButtons() {{
                const nodes = speedButtons.querySelectorAll('.speed-button');
                nodes.forEach(function(node) {{
                    node.classList.toggle('active', parseFloat(node.dataset.speed) === audioElem.playbackRate);
                }});
            }}

            function computeSentenceTimings() {{
                sentenceTimings.length = 0;
                const duration = audioElem.duration || 0;
                const totalWeight = sentenceWeights.reduce(function(sum, weight) {{
                    return sum + weight;
                }}, 0);
                console.log('Audio duration:', duration);
                if (!duration || totalWeight === 0) {{
                    return;
                }}
                let start = 0;
                sentences.forEach(function(_, index) {{
                    const weight = sentenceWeights[index];
                    const length = (weight / totalWeight) * duration;
                    const end = Math.min(duration, start + length);
                    sentenceTimings.push({{ start: start, end: end }});
                    start = end;
                }});
            }}

            function renderSentences() {{
                if (!sentences || sentences.length === 0) {{
                    sentenceContainer.innerHTML =
                        '<div class="listen-text-header">Text being read:</div>' +
                        '<p style="margin: 0;">No sentences were found.</p>';
                }} else {{
                    const sentenceSpans = sentences
                        .map(function(sentence, index) {{
                            return '<span class="listen-sentence" data-index="' + index + '">' +
                                sentence +
                                '</span>';
                        }})
                        .join(' ');
                    sentenceContainer.innerHTML =
                        '<div class="listen-text-header">Text being read:</div>' +
                        '<p style="margin: 0; text-align: left; word-wrap: break-word;">' +
                        sentenceSpans +
                        '</p>';
                }}
            }}

            function renderFullText() {{
                if (!fullText || fullText.trim().length === 0) {{
                    fullTextContainer.innerHTML = '';
                }}
            }}

            function updateActiveSentence() {{
                const currentTime = audioElem.currentTime;
                console.log('audio currentTime:', currentTime);
                console.log('audio duration (rechecked):', audioElem.duration);
                if (sentences.length === 0 || sentenceTimings.length === 0) {{
                    return;
                }}
                let index = sentenceTimings.findIndex(function(timing) {{
                    return currentTime >= timing.start && currentTime < timing.end;
                }});
                if (index === -1 && !audioElem.ended) {{
                    index = currentTime >= audioElem.duration ? sentenceTimings.length - 1 : 0;
                }}
                if (audioElem.ended) {{
                    activeSentence = -1;
                }} else {{
                    activeSentence = index;
                }}
                console.log('active sentence index:', activeSentence);
                const sentenceNodes = sentenceContainer.querySelectorAll('.listen-sentence');
                sentenceNodes.forEach(function(node) {{
                    const nodeIndex = Number(node.dataset.index);
                    const shouldBeActive = nodeIndex === activeSentence;
                    node.classList.toggle('active', shouldBeActive);
                    if (shouldBeActive) {{
                        node.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                    }}
                }});
            }}

            function initialize() {{
                createSpeedButtons();
                renderSentences();
                renderFullText();
                if (sentences.length > 0) {{
                    console.log('Loaded sentences:', sentences.length);
                }} else {{
                    console.log('No sentences loaded.');
                }}
                audioElem.addEventListener('loadedmetadata', function() {{
                    computeSentenceTimings();
                    updateActiveSentence();
                }});
                ['play', 'pause', 'timeupdate', 'seeked'].forEach(function(eventName) {{
                    audioElem.addEventListener(eventName, updateActiveSentence);
                }});
            }}

            initialize();
        </script>
        """

        components.html(audio_html, height=950)

        st.download_button(
            label="⬇️ Download Audio",
            data=audio_data,
            file_name="learning_audio.mp3",
            mime="audio/mpeg",
            key="download_audio"
        )


def _render_visual_mode_legacy() -> None:
    """Render Visual Learn mode with a single selected visual type."""
    st.subheader("🖼️ Choose a visual learning style")

    st.markdown("**Pick one visual type before generating:**")
    st.markdown(
        "🔄 Flowchart – Step-by-step visual process\n"
        "🧠 Mind Map – Concept connections and relationships"
    )

    # Get UI preferences for theme
    preferences = get_ui_preferences()
    theme = preferences.get("theme", "Light").lower().replace(" ", "_")
    theme_mapping = {
        "light": "light",
        "dark": "dark",
        "cream": "dyslexia_cream",
        "yellow": "dyslexia_yellow",
    }
    visual_theme = theme_mapping.get(theme, "light")

def render_visual_mode() -> None:
    """Render Visual Learn mode with an explicit selected visual type."""
    st.subheader("Visual Learning")

    selected_visual = st.selectbox(
        "Choose a visual type",
        [
            "Select a visual type",
            "Flowchart",
            "Mind Map",
        ],
        index=0,
        key="visual_choice",
    )

    preferences = get_ui_preferences()
    theme = preferences.get("theme", "Light").lower().replace(" ", "_")
    theme_mapping = {
        "light": "light",
        "dark": "dark",
        "cream": "dyslexia_cream",
        "yellow": "dyslexia_yellow",
    }
    visual_theme = theme_mapping.get(theme, "light")

    visual_type_map = {
        "Flowchart": "flowchart",
        "Mind Map": "mind_map",
    }

    if st.button("Generate Visual", type="primary", key="gen_visual_btn"):
        _log_learning_support_event("visual")
        if selected_visual not in visual_type_map:
            st.warning("Please choose a visual type before generating.")
            return

        with st.spinner("Generating your visual..."):
            try:
                visual_content = generate_visual_content(
                    st.session_state.document_text or "",
                    theme=visual_theme,
                    visual_type=visual_type_map[selected_visual],
                )
                st.session_state.visual_content = visual_content
                st.session_state.selected_visual = selected_visual
                st.success("Visual generated.")
            except (VisualError, LLMRouterError, ValueError):
                logger.exception("Visual generation failed")
                st.error("Visual generation is temporarily unavailable.")
                return
            except Exception:
                logger.exception("Unexpected error during visual generation")
                st.error("Something went wrong. Please try again.")
                return

    visual_content = st.session_state.get("visual_content")
    generated_visual = st.session_state.get("selected_visual")
    if not visual_content:
        st.info("Choose a visual type and generate it to begin.")
        return

    if generated_visual != selected_visual:
        st.info("Generate the selected visual type to view it here.")
        return

    image_key = "flowchart_path" if visual_type_map.get(generated_visual) == "flowchart" else "mindmap_path"
    image_path = visual_content.get(image_key)
    if not image_path:
        st.info("No visual image was created for the selected type.")
        return

    st.markdown(f"### {generated_visual}")
    if visual_content.get("description"):
        st.write(visual_content["description"])

    st.image(image_path, use_container_width=True)
    try:
        with open(image_path, "rb") as visual_file:
            st.download_button(
                label="Download Visual",
                data=visual_file.read(),
                file_name=Path(image_path).name,
                mime="image/png",
                key=f"download_{image_key}",
            )
    except OSError:
        logger.exception("Generated visual file could not be opened")


def _shorten_explanation(text: str, max_sentences: int = 3) -> str:
    """Return the first `max_sentences` sentences from `text` for concise explanations."""
    if not text:
        return ""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", str(text).strip())
    short = " ".join(s.strip() for s in sentences[:max_sentences] if s.strip())
    return short


def _quiz_question_key(question_type: str, index: int, question: dict) -> str:
    """Build a stable session key for hidden per-question timing."""
    question_id = str(question.get("question_id") or f"Q{index + 1:03d}").strip()
    return f"{question_type}:{question_id}:{index}"


def _initialize_quiz_question_start_times(force: bool = False) -> None:
    """Capture the timestamp when generated quiz questions first become visible."""
    if not force and st.session_state.get("quiz_question_start_times"):
        return

    now = datetime.utcnow()
    start_times = {}
    mcqs = st.session_state.quiz_mcqs if isinstance(st.session_state.quiz_mcqs, list) else []
    short_questions = (
        st.session_state.quiz_short_questions
        if isinstance(st.session_state.quiz_short_questions, list)
        else []
    )

    for index, question in enumerate(mcqs):
        if isinstance(question, dict):
            start_times[_quiz_question_key("MCQ", index, question)] = now
    for index, question in enumerate(short_questions):
        if isinstance(question, dict):
            start_times[_quiz_question_key("Short Answer", index, question)] = now

    st.session_state.quiz_question_start_times = start_times


def _quiz_question_duration(
    question_type: str,
    index: int,
    question: dict,
    submit_time: datetime,
) -> tuple[datetime, int]:
    """Return the hidden start timestamp and elapsed seconds for one question."""
    start_times = st.session_state.get("quiz_question_start_times") or {}
    start_time = start_times.get(_quiz_question_key(question_type, index, question))
    if not isinstance(start_time, datetime):
        start_time = submit_time
    return start_time, max(0, int(round((submit_time - start_time).total_seconds())))


def _infer_quiz_topic(quiz_mcqs: list[dict], short_questions: list[dict]) -> str:
    """Infer a compact topic label from generated quiz metadata."""
    for question in [*quiz_mcqs, *short_questions]:
        if isinstance(question, dict):
            topic = str(question.get("concept") or question.get("subcategory") or "").strip()
            if topic:
                return topic
    document_record = st.session_state.get("document_record")
    return str(getattr(document_record, "original_filename", None) or "Document Quiz")


def _compute_quiz_feedback_metadata(
    report: dict,
    total_questions: int,
    question_durations: list[int],
    support_count: int = 0,
    first_attempt_success_count: int | None = None,
) -> tuple[float, dict[str, str]]:
    quiz_accuracy = float(report.get("percentage") or 0.0)
    conceptual_score = float(report.get("conceptual_score") or quiz_accuracy)
    avg_response_time = round(sum(question_durations) / len(question_durations), 1) if question_durations else 0.0
    if first_attempt_success_count is None:
        first_attempt_success_rate = quiz_accuracy
    else:
        first_attempt_success_rate = (
            round((first_attempt_success_count / total_questions) * 100.0, 1)
            if total_questions else quiz_accuracy
        )
    comprehension_score = calculate_quiz_comprehension_score(
        quiz_accuracy=quiz_accuracy,
        conceptual_score=conceptual_score,
        support_count=support_count,
        total_questions=total_questions,
        first_attempt_success_rate=first_attempt_success_rate,
        avg_time_per_question=avg_response_time,
    )
    weak_concepts = report.get("wrong_concepts") if isinstance(report.get("wrong_concepts"), list) else []
    feedback = generate_personalized_quiz_feedback(
        quiz_accuracy=quiz_accuracy,
        conceptual_score=conceptual_score,
        avg_response_time=avg_response_time,
        support_count=support_count,
        total_questions=total_questions,
        first_attempt_success_rate=first_attempt_success_rate,
        weak_concepts=weak_concepts,
    )
    return comprehension_score, feedback


def _active_quiz_question_ids() -> list[str]:
    """Return generated quiz question ids for behaviour log association."""
    question_ids = []
    mcqs = st.session_state.quiz_mcqs if isinstance(st.session_state.quiz_mcqs, list) else []
    short_questions = (
        st.session_state.quiz_short_questions
        if isinstance(st.session_state.quiz_short_questions, list)
        else []
    )

    for index, question in enumerate([*mcqs, *short_questions]):
        if isinstance(question, dict):
            question_ids.append(str(question.get("question_id") or f"Q{index + 1:03d}"))
    return question_ids


def _current_quiz_support_question_id() -> str | None:
    """Choose the best available question id for a background support event."""
    if not st.session_state.quiz_mcqs or st.session_state.quiz_report:
        return None

    mcqs = st.session_state.quiz_mcqs if isinstance(st.session_state.quiz_mcqs, list) else []
    mcq_answers = st.session_state.quiz_answers if isinstance(st.session_state.quiz_answers, list) else []
    for index, question in enumerate(mcqs):
        if index >= len(mcq_answers) or not mcq_answers[index]:
            return str(question.get("question_id") or f"Q{index + 1:03d}")

    short_questions = (
        st.session_state.quiz_short_questions
        if isinstance(st.session_state.quiz_short_questions, list)
        else []
    )
    short_answers = st.session_state.quiz_short_answers if isinstance(st.session_state.quiz_short_answers, list) else []
    offset = len(mcqs)
    for index, question in enumerate(short_questions):
        answer = short_answers[index] if index < len(short_answers) else ""
        if not str(answer or "").strip():
            return str(question.get("question_id") or f"Q{offset + index + 1:03d}")

    question_ids = _active_quiz_question_ids()
    return question_ids[-1] if question_ids else None


def _log_learning_support_event(support_type: str, question_id: str | None = None) -> None:
    """Persist a hidden support-use event when the learner is solving a quiz."""
    user_id = st.session_state.current_user_id
    if user_id is None:
        return

    active_question_id = question_id or _current_quiz_support_question_id()
    if not active_question_id:
        return

    try:
        save_learning_support_log(
            user_id=user_id,
            quiz_id=None,
            question_id=active_question_id,
            support_type=support_type,
            timestamp=datetime.utcnow(),
        )
    except Exception:
        logger.exception("[Support Tracking] Failed to save %s support event.", support_type)


def _active_quiz_started_at() -> datetime | None:
    """Return the earliest hidden start timestamp for the active quiz."""
    start_times = st.session_state.get("quiz_question_start_times") or {}
    values = [value for value in start_times.values() if isinstance(value, datetime)]
    return min(values) if values else None


def _persist_quiz_question_timings(
    quiz_mcqs: list[dict],
    short_questions: list[dict],
    short_feedback: list[dict],
    report: dict,
) -> None:
    """Save one permanent SQLite row for each answered quiz question."""
    user_id = st.session_state.current_user_id
    if user_id is None:
        return

    submit_time = datetime.utcnow()
    topic = _infer_quiz_topic(quiz_mcqs, short_questions)
    total_questions = len(quiz_mcqs) + len(short_questions)
    quiz_state = st.session_state.get("quiz_state", {}) or {}
    hint_used = quiz_state.get("hint_used", {}) if isinstance(quiz_state.get("hint_used", {}), dict) else {}
    first_attempt_success_flags = quiz_state.get("first_attempt_success_flags", {}) if isinstance(quiz_state.get("first_attempt_success_flags", {}), dict) else {}
    support_count = sum(int(value) for value in hint_used.values() if isinstance(value, (int, float)))
    first_attempt_success_count = sum(
        1 for idx in range(total_questions) if first_attempt_success_flags.get(idx, False)
    ) if total_questions else None

    question_results = report.get("question_results") or []
    records: list[dict] = []
    question_durations: list[int] = []

    for index, question in enumerate(quiz_mcqs):
        if not isinstance(question, dict):
            continue
        start_time, duration = _quiz_question_duration("MCQ", index, question, submit_time)
        question_durations.append(duration)
        result = question_results[index] if index < len(question_results) and isinstance(question_results[index], dict) else {}
        records.append(
            {
                "user_id": user_id,
                "question_id": str(question.get("question_id") or f"Q{index + 1:03d}"),
                "question_type": str(question.get("question_type") or "MCQ"),
                "topic": str(question.get("concept") or topic),
                "difficulty": str(question.get("difficulty") or ""),
                "question_start_time": start_time,
                "question_submit_time": submit_time,
                "time_taken_seconds": duration,
                "is_correct": bool(result.get("is_correct")),
            }
        )

    for index, question in enumerate(short_questions):
        if not isinstance(question, dict):
            continue
        start_time, duration = _quiz_question_duration("Short Answer", index, question, submit_time)
        question_durations.append(duration)
        feedback_item = short_feedback[index] if index < len(short_feedback) and isinstance(short_feedback[index], dict) else {}
        evaluation = feedback_item.get("evaluation") if isinstance(feedback_item.get("evaluation"), dict) else {}
        records.append(
            {
                "user_id": user_id,
                "question_id": str(question.get("question_id") or f"Q{index + 1:03d}"),
                "question_type": str(question.get("question_type") or "Short Answer"),
                "topic": str(question.get("concept") or topic),
                "difficulty": str(question.get("difficulty") or ""),
                "question_start_time": start_time,
                "question_submit_time": submit_time,
                "time_taken_seconds": duration,
                "is_correct": str(evaluation.get("result") or "").strip() == "Correct",
            }
        )

    comprehension_score, feedback_fields = _compute_quiz_feedback_metadata(
        report=report,
        total_questions=total_questions,
        question_durations=question_durations,
        support_count=support_count,
        first_attempt_success_count=first_attempt_success_count,
    )
    quiz_attempt = save_quiz_score(
        user_id=user_id,
        topic=topic,
        score=int(report.get("score") or 0),
        total_questions=total_questions,
        comprehension_score=comprehension_score,
        **feedback_fields,
    )

    for record in records:
        record["quiz_id"] = quiz_attempt.id

    if records:
        save_quiz_question_responses(records)
        attach_learning_support_logs_to_quiz(
            user_id=user_id,
            quiz_id=quiz_attempt.id,
            question_ids=_active_quiz_question_ids(),
            started_after=_active_quiz_started_at(),
        )


def render_quiz_section() -> None:
    """Render the enhanced interactive one-question-at-a-time quiz experience.
    
    Features:
    - One question at a time with Previous/Next navigation
    - Cumulative timer for each question
    - Live timer display
    - Progress indicator
    - AI-generated hints (cached to avoid repeated API calls)
    - Final quiz summary with timing analytics
    """
    # Generate Quiz button
    if st.button("📝 Generate Quiz", type="primary", key="gen_quiz_btn"):
        logger.info("[Quiz] Starting quiz generation")
        with st.spinner("Generating quiz from your document..."):
            try:
                document_text = st.session_state.document_text or ""
                mcqs = generate_mcq_quiz(document_text, num_questions=4)
                short_questions = generate_short_questions(document_text, num_questions=4)
                st.session_state.quiz_mcqs = mcqs
                st.session_state.quiz_short_questions = short_questions
                st.session_state.quiz_report = None
                st.session_state.quiz_short_feedback = None
                st.session_state.quiz_attempt_count = 1
                
                # Initialize new quiz state
                initialize_quiz_session_state(mcqs, short_questions)
                
                st.success("✅ Quiz generated! Start answering questions below.")
            except (DocumentError, LLMRouterError, ValueError):
                logger.exception("Quiz generation failed")
                st.error("Quiz generation is temporarily unavailable.")
                return
            except Exception:
                logger.exception("Unexpected error during quiz generation")
                st.error("Quiz generation is temporarily unavailable.")
                return

    if not st.session_state.get("quiz_mcqs") or not st.session_state.get("quiz_short_questions"):
        st.info("📝 Generate a quiz to begin. The quiz will use the currently uploaded document.")
        return

    # Show old quiz results if they exist
    if st.session_state.get("quiz_report"):
        _render_quiz_summary_results()
        return

    # Interactive one-question-at-a-time quiz
    _render_interactive_quiz()


def _sanitize_incorrect_feedback(feedback: str) -> str:
    """Ensure incorrect feedback does not reveal the correct answer."""
    sanitized = str(feedback or "").strip()
    # Remove explicit correct-answer reveal patterns.
    sanitized = sanitized.replace("Correct answer is:", "Your answer is incorrect.")
    sanitized = sanitized.replace("the correct answer is", "consider reviewing the question and trying again")
    sanitized = sanitized.replace("Correct Answer:", "Review the question again.")
    return sanitized


def _render_interactive_quiz() -> None:
    """Render the interactive one-question-at-a-time quiz experience with retry support.
    
    Layout:
    - Top: Progress indicator (Question X of Y + progress bar + timer)
    - Middle: Question + options/text area + hint
    - Evaluation: If submitted, show result (Correct/Incorrect + feedback)
    - Bottom: Navigation (Previous/Next/Try Again/Submit)
    """
    # Ensure quiz state is initialized
    if "quiz_state" not in st.session_state:
        initialize_quiz_session_state(
            st.session_state.quiz_mcqs,
            st.session_state.quiz_short_questions,
        )
    
    quiz_state = st.session_state.quiz_state
    current_index = quiz_state["current_question_index"]
    questions = quiz_state["questions"]
    answers = quiz_state["answers"]
    
    # Start viewing the current question (tracks time from when they navigate to it)
    _start_question_viewing(current_index)
    
    # TOP: Progress and timer
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_quiz_progress_indicator(current_index, len(questions))
    
    with col2:
        render_question_timer(current_index)
    
    st.markdown("---")
    
    # MIDDLE: Question, options, and hints
    current_question = questions[current_index]
    stored_answer = answers[current_index] if current_index < len(answers) else ""
    
    # Render the question and get the answer
    answer = render_quiz_question(current_question, current_index, stored_answer)
    answers[current_index] = answer
    
    st.markdown("---")
    
    # Hint area
    render_hint_button(current_index, current_question)
    
    st.markdown("---")
    st.info("🧭 Answer each question in any order, then submit the full quiz once when you are ready.")
    st.markdown("---")
    
    # BOTTOM: Navigation that never blocks progress
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if current_index > 0:
            if st.button("◀ Previous", key="nav_prev", use_container_width=True):
                mark_question_completed(current_index)
                persist_question_timing(current_index)
                quiz_state["current_question_index"] = current_index - 1
                st.rerun()
        else:
            st.button("◀ Previous", key="nav_prev", disabled=True, use_container_width=True)
    
    with col2:
        if current_index < len(questions) - 1:
            if st.button("Next ▶", key="nav_next", use_container_width=True):
                mark_question_completed(current_index)
                persist_question_timing(current_index)
                quiz_state["current_question_index"] = current_index + 1
                st.rerun()
        else:
            if st.button("Submit Quiz", key="nav_submit", use_container_width=True):
                mark_question_completed(current_index)
                persist_question_timing(current_index)
                _submit_interactive_quiz()


def _submit_interactive_quiz() -> None:
    """Submit the completed quiz and show results."""
    quiz_state = st.session_state.quiz_state
    questions = quiz_state["questions"]
    answers = quiz_state["answers"]
    
    # Pause final question timer
    current_index = quiz_state["current_question_index"]
    persist_question_timing(current_index)
    
    # Mark quiz as submitted
    quiz_state["quiz_submitted"] = True
    
    with st.spinner("Evaluating your quiz answers..."):
        total_start = time.perf_counter()
        
        # Separate MCQs and short answers
        mcqs = [q for q in questions if q.get("original_type") == "MCQ"]
        short_questions = [q for q in questions if q.get("original_type") == "Short Answer"]
        
        # Get answers in original order
        mcq_answers = [answers[q["quiz_index"]] for q in mcqs]
        short_answers = [answers[q["quiz_index"]] for q in short_questions]
        
        try:
            # Evaluate MCQs
            mcq_start = time.perf_counter()
            report = evaluate_mcq(mcq_answers, mcqs)
            logger.info("[Quiz] MCQ evaluation completed in %.2f sec", time.perf_counter() - mcq_start)
        except Exception:
            logger.exception("[Quiz Evaluation] MCQ evaluation failed")
            report = {
                "score": 0,
                "total": len(mcqs),
                "percentage": 0,
                "correct_answers": 0,
                "incorrect_answers": len(mcqs),
                "strengths": "Complete the quiz to see a summary of your strengths.",
                "weaknesses": "The quiz could not be evaluated normally.",
                "recommendations": "Review the quiz material and try again.",
                "evaluations": [],
            }
        
        # Evaluate short answers
        short_feedback = []
        for index, short_question in enumerate(short_questions):
            short_start = time.perf_counter()
            question_text = str(short_question.get("question", "")).strip()
            expected_answer = str(short_question.get("answer", "")).strip()
            student_response = short_answers[index] if index < len(short_answers) else ""
            student_response = str(student_response or "").strip()
            
            try:
                if student_response:
                    feedback = evaluate_short_answer(
                        student_response,
                        expected_answer,
                        question_text=question_text,
                    )
                else:
                    feedback = evaluate_short_answer_locally(
                        student_response,
                        expected_answer,
                        question_text=question_text,
                    )
            except Exception:
                logger.exception("[Quiz Evaluation] Short answer %s failed", index + 1)
                feedback = evaluate_short_answer_locally(
                    student_response,
                    expected_answer,
                    question_text=question_text,
                )
            
            logger.info("[Quiz] Short answer %s completed in %.2f sec", index + 1, time.perf_counter() - short_start)
            short_feedback.append({
                "question": question_text,
                "student_answer": student_response,
                "expected_answer": expected_answer,
                "evaluation": feedback,
            })
        
        # Combine reports
        try:
            st.session_state.quiz_report = combine_quiz_report_with_short_answers(report, short_feedback)
        except Exception:
            logger.exception("[Quiz Evaluation] Report merge failed")
            st.session_state.quiz_report = report
        
        st.session_state.quiz_short_feedback = short_feedback
        
        # Persist timing and learning support data
        try:
            _persist_interactive_quiz_timings(mcqs, short_questions, short_feedback, st.session_state.quiz_report)
        except Exception:
            logger.exception("[Quiz Timing] Failed to save timing data")
        
        logger.info("[Quiz] Total evaluation completed in %.2f sec", time.perf_counter() - total_start)
        st.success("✅ Quiz submitted! See your results below.")
        st.rerun()


def _reset_quiz_for_retake() -> None:
    """Reset state for a retake of the same generated quiz."""
    if "quiz_state" in st.session_state:
        del st.session_state["quiz_state"]
    st.session_state.quiz_report = None
    st.session_state.quiz_short_feedback = None
    st.session_state.quiz_attempt_count = st.session_state.get("quiz_attempt_count", 1) + 1


def _persist_interactive_quiz_timings(
    mcqs: list[dict],
    short_questions: list[dict],
    short_feedback: list[dict],
    report: dict,
) -> None:
    """Save timing data, attempt tracking, and learning support logs for the interactive quiz."""
    user_id = st.session_state.current_user_id
    if user_id is None:
        return
    
    quiz_state = st.session_state.quiz_state
    hint_used = quiz_state.get("hint_used", {}) if isinstance(quiz_state.get("hint_used", {}), dict) else {}
    
    submit_time = datetime.utcnow()
    topic = _infer_quiz_topic(mcqs, short_questions)
    total_questions = len(mcqs) + len(short_questions)
    support_count = sum(int(value) for value in hint_used.values() if isinstance(value, (int, float)))
    attempt_number = max(1, int(st.session_state.get("quiz_attempt_count", 1)))
    first_attempt_success_count = None
    if total_questions and attempt_number == 1:
        first_attempt_success_count = sum(
            1 for result in report.get("question_results", []) if bool(result.get("is_correct", False))
        )

    question_results = report.get("question_results", [])
    records: list[dict] = []
    question_durations: list[int] = []
    
    # Save MCQ timing records with attempt tracking
    for index, question in enumerate(mcqs):
        if not isinstance(question, dict):
            continue
        
        # Get cumulative time from quiz_state
        time_taken = get_current_question_time_seconds(question["quiz_index"])
        question_durations.append(time_taken)
        result = question_results[index] if index < len(question_results) else {}
        
        question_index = question["quiz_index"]
        is_correct = bool(result.get("is_correct", False))
        attempt_num, first_attempt_success = get_quiz_submission_attempt_metadata(attempt_number, is_correct)
        
        records.append({
            "user_id": user_id,
            "question_id": str(question.get("question_id", f"mcq_{index}")),
            "question_type": "MCQ",
            "topic": str(question.get("concept", topic)),
            "difficulty": str(question.get("difficulty", "")),
            "question_start_time": submit_time - timedelta(seconds=time_taken),
            "question_submit_time": submit_time,
            "time_taken_seconds": time_taken,
            "is_correct": is_correct,
            "attempt_number": attempt_num,
            "first_attempt_success": first_attempt_success,
        })
     
    # Save short answer timing records with attempt tracking
    for index, question in enumerate(short_questions):
        if not isinstance(question, dict):
            continue
        
        time_taken = get_current_question_time_seconds(question["quiz_index"])
        question_durations.append(time_taken)
        feedback_item = short_feedback[index] if index < len(short_feedback) else {}
        evaluation = feedback_item.get("evaluation", {})
        
        question_index = question["quiz_index"]
        is_correct = str(evaluation.get("result", "")).strip() == "Correct"
        attempt_num, first_attempt_success = get_quiz_submission_attempt_metadata(attempt_number, is_correct)
        
        records.append({
            "user_id": user_id,
            "question_id": str(question.get("question_id", f"short_{index}")),
            "question_type": "Short Answer",
            "topic": str(question.get("concept", topic)),
            "difficulty": str(question.get("difficulty", "")),
            "question_start_time": submit_time - timedelta(seconds=time_taken),
            "question_submit_time": submit_time,
            "time_taken_seconds": time_taken,
            "is_correct": is_correct,
            "attempt_number": attempt_num,
            "first_attempt_success": first_attempt_success,
        })
    
    comprehension_score, feedback_fields = _compute_quiz_feedback_metadata(
        report=report,
        total_questions=total_questions,
        question_durations=question_durations,
        support_count=support_count,
        first_attempt_success_count=first_attempt_success_count,
    )
    quiz_attempt = save_quiz_score(
        user_id=user_id,
        topic=topic,
        score=int(report.get("score") or 0),
        total_questions=total_questions,
        comprehension_score=comprehension_score,
        **feedback_fields,
    )

    for record in records:
        record["quiz_id"] = quiz_attempt.id

    if records:
        save_quiz_question_responses(records)
    
    # Save hint usage as learning support logs
    for question_index, hint_count in hint_used.items():
        question = quiz_state["questions"][question_index]
        for _ in range(hint_count):
            try:
                save_learning_support_log(
                    user_id=user_id,
                    quiz_id=quiz_attempt.id,
                    question_id=str(question.get("question_id", f"q_{question_index}")),
                    support_type="hint",
                    timestamp=submit_time,
                )
            except Exception:
                logger.exception("Failed to save hint usage log")


def _render_quiz_summary_results() -> None:
    """Render the final quiz summary with results and timing analytics."""
    report = st.session_state.quiz_report
    quiz_state = st.session_state.get("quiz_state", {})
    
    st.header("✅ Quiz Completed")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score", f"{report.get('score', 0)}/{report.get('total', 0)}")
    with col2:
        st.metric("Percentage", f"{report.get('percentage', 0)}%")
    with col3:
        # Calculate total time
        if quiz_state:
            total_time = 0
            for idx in range(len(quiz_state.get("questions", []))):
                total_time += get_current_question_time_seconds(idx)
            st.metric("Total Time", format_time_seconds(total_time))
    
    st.progress(report.get("percentage", 0) / 100 if report.get("total") else 0)
    
    total_questions = len(quiz_state.get("questions", []))
    hint_used = quiz_state.get("hint_used", {}) if isinstance(quiz_state.get("hint_used", {}), dict) else {}
    support_count = sum(int(value) for value in hint_used.values() if isinstance(value, (int, float)))
    attempt_number = max(1, int(st.session_state.get("quiz_attempt_count", 1)))
    first_attempt_success_count = sum(
        1 for result in report.get("question_results", []) if bool(result.get("is_correct", False)) and attempt_number == 1
    ) if total_questions else 0
    first_attempt_success_pct = round((first_attempt_success_count / total_questions) * 100) if total_questions else 0
    question_durations = [get_current_question_time_seconds(idx) for idx in range(total_questions)]
    comprehension_score, feedback_fields = _compute_quiz_feedback_metadata(
        report=report,
        total_questions=total_questions,
        question_durations=question_durations,
        support_count=support_count,
        first_attempt_success_count=first_attempt_success_count,
    )

    st.markdown("### Quiz Comprehension")
    st.metric("Comprehension Score", f"{comprehension_score}%")
    st.write(
        f"Based on accuracy, concept mastery, support dependency, first-attempt success, and response efficiency."
    )

    st.markdown("### Personalized Feedback")
    st.subheader("Focus Areas")
    st.write(feedback_fields.get("feedback_strengths", "No strengths identified."))
    st.write(feedback_fields.get("feedback_weaknesses", "No weaknesses identified."))
    st.write("**Recommended concepts:**")
    st.write(feedback_fields.get("feedback_recommended_concepts", "Review the concepts behind questions missed."))
    st.write("**Suggested mode:**")
    st.write(feedback_fields.get("feedback_suggested_learning_mode", "Simplified Notes"))
    st.markdown("---")

    attempt_count = st.session_state.get("quiz_attempt_count", 1)
    st.markdown(f"### Quiz Attempt {attempt_count}")
    st.write(
        "This quiz has been submitted as a separate attempt. You can retake the same questions to compare progress across attempts."
    )
    st.markdown("---")

    st.markdown("### First Attempt Success")
    st.metric("Score", f"{first_attempt_success_pct}%")
    st.write(f"{first_attempt_success_count} / {total_questions} questions answered correctly on the first attempt.")
    st.markdown("---")
    
    # Question-wise timing breakdown
    if quiz_state:
        st.subheader("Question-wise Time Breakdown")
        summary = get_quiz_summary()
        
        timing_cols = st.columns([2, 1])
        with timing_cols[0]:
            st.markdown("**Question**")
        with timing_cols[1]:
            st.markdown("**Time**")
        
        for qt in summary["question_times"]:
            timing_cols = st.columns([2, 1])
            with timing_cols[0]:
                st.write(f"Q{qt['question_number']}: {qt['question'][:60]}...")
            with timing_cols[1]:
                st.write(qt["time_formatted"])
    
    # Analysis
    st.subheader("Performance Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Strengths**")
        st.write(str(report.get("strengths", "No data")))
    with col2:
        st.markdown("**Weaknesses**")
        st.write(str(report.get("weaknesses", "No data")))
    
    st.markdown("**Recommendations**")
    st.write(str(report.get("recommendations", "No data")))
    
    # Detailed evaluation
    evaluations = report.get("evaluations", [])
    if evaluations:
        st.subheader("Detailed Evaluation")
        for index, evaluation in enumerate(evaluations, start=1):
            with st.expander(f"Question {index} — View Evaluation"):
                st.markdown("**Question:**")
                st.write(evaluation.get("question", ""))
                
                st.markdown("**Your Answer:**")
                st.write(evaluation.get("your_answer", ""))
                
                st.markdown("**Correct Answer:**")
                st.write(evaluation.get("correct_answer", ""))
                
                st.markdown("**Result:**")
                result = str(evaluation.get("result", "Incorrect"))
                if result == "Correct":
                    st.write("✅ Correct")
                elif result in {"Partially Correct", "Partially"}:
                    st.write("⚠️ Partially Correct")
                else:
                    st.write("❌ Incorrect")
                
                feedback = str(evaluation.get("feedback", "")).strip()
                improvement_tip = str(evaluation.get("improvement_tip", "")).strip()
                local_explanation = str(evaluation.get("local_explanation", "")).strip()
                fallback_explanation = str(evaluation.get("explanation", "")).strip()
                
                st.markdown("**Feedback:**")
                st.write(feedback or local_explanation or fallback_explanation or "No feedback available")
    
    retake_col, new_quiz_col = st.columns(2)
    with retake_col:
        if st.button("🔁 Retake This Quiz", type="secondary"):
            _reset_quiz_for_retake()
            st.rerun()
    with new_quiz_col:
        if st.button("📝 Generate a New Quiz", type="secondary"):
            st.session_state.quiz_mcqs = None
            st.session_state.quiz_short_questions = None
            st.session_state.quiz_report = None
            st.session_state.quiz_short_feedback = None
            if "quiz_state" in st.session_state:
                del st.session_state.quiz_state
            st.rerun()


def render_chat_section() -> None:
    """Render the adaptive AI Tutor chat with document context."""
    if not st.session_state.document_text:
        return

    document_id_for_db = st.session_state.get("saved_document_id")
    tutor = AdaptiveAITutor(
        user_id=st.session_state.current_user_id,
        document_id=document_id_for_db,
    )

    st.header("🧠 AI Tutor")
    st.markdown("Get personalized explanations, examples, and recommendations based on your document and learning history.")
    st.info(tutor.get_session_greeting())

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_question = st.chat_input("Ask your tutor a question about the content...")
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
                    st.session_state.document_chunks = chunk_text(st.session_state.document_text)
                    vector_store = build_index(st.session_state.document_chunks)
                    st.session_state.document_index = vector_store

                relevant_chunks = retrieve_relevant_chunks_for_question(
                    user_question,
                    vector_store,
                    top_k=3,
                )
                context = "\n\n".join(chunk["text"] for chunk in relevant_chunks)
                adaptive_prompt = tutor.generate_adaptive_system_prompt()
                full_context = f"{adaptive_prompt}\n\nDOCUMENT CONTEXT:\n{context}"
                answer = generate_answer(user_question, full_context)
                tutor.track_interaction(
                    interaction_type="question",
                    topic=None,
                    duration_seconds=0,
                    session_id=None,
                )
            except (DocumentError, GeminiConfigurationError, GeminiAPIError, LLMRouterError, ValueError) as exc:
                logger.exception("Chat answer generation failed.")
                answer = "I could not answer that right now. Please try rephrasing your question."
            except Exception as exc:
                logger.exception("Unexpected chat failure.")
                answer = "Something went wrong while answering. Please try again."

        st.markdown(answer)

    try:
        user_id = st.session_state.current_user_id
        if user_id is None:
            raise ValueError("No authenticated user available.")
        saved_chat = save_chat(
            user_id=user_id,
            document_id=document_id_for_db,
            user_message=user_question,
            ai_response=answer,
        )
        print("Chat saved to database")
    except Exception as exc:
        logger.exception("Failed to save chat to database: %s", exc)

    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    adaptive_recommendations = tutor.get_adaptive_recommendations()
    if adaptive_recommendations:
        with st.expander("💡 AI Tutor Suggestions"):
            for recommendation in adaptive_recommendations:
                title = recommendation.get("title") or recommendation.get("type", "Suggestion").replace("_", " ").title()
                message = recommendation.get("text") or recommendation.get("message") or ""
                if title:
                    st.markdown(f"**{title}**")
                if message:
                    st.write(message)
                if recommendation.get("topic"):
                    st.write(f"**Topic:** {recommendation['topic']}")
                if recommendation.get("suggested"):
                    st.write(f"**Suggested:** {recommendation['suggested']}")
                st.divider()


def render_word_explorer() -> None:
    """Render a standalone word explorer for learning any word's meaning.
    
    This feature works independently—no document or vocabulary generation required.
    Uses explain_word() backend with session caching to avoid repeated LLM calls.
    """
    st.header("🔍 Word Explorer")
    st.markdown("**Learn the meaning of any word—even if it's not in your document!**")
    
    # Initialize session state for word exploration
    if "word_explorer_input" not in st.session_state:
        st.session_state.word_explorer_input = ""
    if "word_explorer_result" not in st.session_state:
        st.session_state.word_explorer_result = None
    
    # Input layout: text field and button side-by-side
    col1, col2 = st.columns([3, 1])
    
    with col1:
        word_input = st.text_input(
            "Enter a word to explore:",
            placeholder="e.g., photosynthesis, algorithm, mitochondria",
            key="word_explorer_input_field",
            help="Type any word you'd like to learn about."
        )
    
    with col2:
        explore_clicked = st.button("Explore 🔍", type="primary", key="word_explorer_btn")
    
    # Handle exploration
    if explore_clicked:
        if not word_input or not word_input.strip():
            st.error("🚫 Please enter a word.")
        else:
            _log_learning_support_event("vocabulary")
            with st.spinner(f"Looking up '{word_input.strip()}'..."):
                try:
                    # Check cache first
                    cache = st.session_state.get("vocab_explain_cache", {})
                    cache_key = word_input.strip().lower()
                    
                    if cache_key in cache:
                        explanation = cache[cache_key]
                    else:
                        # Fetch from backend
                        explanation = explain_word(word_input.strip())
                        cache[cache_key] = explanation
                        st.session_state["vocab_explain_cache"] = cache
                    
                    st.session_state.word_explorer_result = explanation
                    st.success("✅ Explanation found!")
                    
                except VocabularyError as exc:
                    st.error("❌ Unable to explain this word right now. Please try another word.")
                    logger.warning("Word exploration failed for '%s': %s", word_input, exc)
                except LLMRouterError as exc:
                    st.error("❌ AI service temporarily unavailable. Please try again.")
                    logger.warning("LLM routing failed for word exploration: %s", exc)
                except Exception as exc:
                    st.error("❌ Something went wrong. Please try again.")
                    logger.exception("Unexpected error during word exploration")
    
    # Display result if available
    if st.session_state.word_explorer_result:
        exp = st.session_state.word_explorer_result
        
        from components.ui_constants import CHARACTER_SPACING, FONT_SIZES, THEMES
        preferences = get_ui_preferences()
        theme = THEMES[preferences["theme"]]
        font_size = FONT_SIZES[preferences["font_size"]]
        character_spacing = CHARACTER_SPACING[preferences["character_spacing"]]
        
        # Simple accent color logic
        accent_color = "#93C5FD" if theme["background_color"] == "#121826" else "#1D4ED8"

        # Ensure generated content text remains readable on all themes.
        is_dark_theme = theme["background_color"] == "#121826"
        content_text_color = theme["text_color"] if is_dark_theme else "#1a1a1a"
        
        html_result = f"""
        <div style="margin-top: 1rem; padding: 1rem; background-color: {theme['secondary_background']}; 
                    border: 1px solid {theme['border_color']}; border-radius: 8px; font-size: {font_size}px; 
                    line-height: 1.8; letter-spacing: {character_spacing}; color: {content_text_color};">
            <div style="display: inline-block; background-color: {accent_color}; color: {theme['background_color']}; 
                        padding: 0.5rem 0.75rem; border-radius: 6px; font-weight: 800; margin-bottom: 0.9rem;">
                {exp.get('word', 'Unknown').capitalize()}
            </div>
            <div style="margin-top: 0.75rem;"><strong>📖 Meaning:</strong> {exp.get('meaning', '')}</div>
            <div style="margin-top: 0.5rem;"><strong>📝 Explanation:</strong> {exp.get('explanation', '')}</div>
            <div style="margin-top: 0.5rem;"><strong>💡 Example:</strong> \"{exp.get('example', '')}</strong></div>
        </div>
        """
        st.markdown(html_result, unsafe_allow_html=True)


def main() -> None:
    """Run the Streamlit app."""
    initialize_session_state()
    initialize_ui_preferences()
    auth_state = st.session_state.get("authenticated", None)
    current_user_id = st.session_state.get("current_user_id", None)
    logger.debug("Initialize session state complete: authenticated=%s current_user_id=%s", auth_state, current_user_id)

    
    if not st.session_state.authenticated or st.session_state.current_user_id is None:
        logger.debug("Authentication required; calling render_authentication()")
        render_authentication()
        return

    logger.debug("Authenticated, calling render_home()")
    render_sidebar_user_panel()

    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Learning Hub"],
        index=0,
        key="navigation_selection",
    )

    if page == "Dashboard":
        render_dashboard(st.session_state.current_user_id)
    else:
        render_home()
        st.divider()
        render_upload_section()
        st.divider()
        render_learning_modes()
        st.divider()
        render_word_explorer()
        st.divider()
        render_chat_section()


if __name__ == "__main__":
    main()

