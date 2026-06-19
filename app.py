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
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from backend.chunker import chunk_text
from backend.parser import process_uploaded_file
from backend.retriever import retrieve_relevant_chunks_for_question
from backend.vector_store import build_index
from database.db import save_document, save_user, get_user, save_chat
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
from services.document_context import DocumentError, get_document_text
from services.gemini_service import (
    GeminiAPIError,
    GeminiConfigurationError,
)
<<<<<<< HEAD
from services.llm_router import generate_answer
from services.quiz_service import (
    evaluate_mcq,
    evaluate_short_answer,
    generate_mcq_quiz,
    generate_short_questions,
)
=======
from services.llm_router import generate_answer, LLMRouterError
from services.ocr_service import extract_text_from_image, OCRError
from services.simplification_service import simplify_text, SimplificationError
from services.vocabulary_service import generate_vocabulary, VocabularyError, explain_word
from services.tts_service import cleanup_audio_file, generate_audio, split_text_into_sentences, TTSError
from services.visual_service import generate_visual_content, VisualError

logger = logging.getLogger(__name__)
>>>>>>> main


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

        # Generated content
        "simplified_content": None,
        "visual_content": None,
        "audio_file": None,
        "selected_visual": None,
        "visual_choice": "Select a visual",

        # Chat
        "chat_history": [],
<<<<<<< HEAD
        "quiz_mcqs": None,
        "quiz_short_questions": None,
        "quiz_answers": None,
        "quiz_short_answers": None,
        "quiz_report": None,
        "quiz_short_feedback": None,
=======

        # Caching
        "vocab_explain_cache": {},
>>>>>>> main
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _resolve_anonymous_user_id() -> int:
    """Return an existing anonymous user id or create one for local storage.

    This helper mirrors the backend fallback used by Flask routes so Streamlit
    interactions can persist without a full auth system.
    """
    user = get_user("anonymous@cheal.local")
    if user is not None:
        return user.id  # type: ignore[index]

    anonymous = save_user(name="Anonymous Learner", email="anonymous@cheal.local", password_hash="")
    return anonymous.id  # type: ignore[index]





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
            user_id = _resolve_anonymous_user_id()
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
                    from services.ocr_service import extract_text_from_pdf_images
                    text = extract_text_from_pdf_images(temp_path)
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
    """Render learning mode selector and content."""
    if not st.session_state.document_text:
        st.info("📤 Upload a document or image first to get started!")
        return

    st.header("🎯 Choose Your Learning Mode")
    initialize_learning_mode()
    selected_mode = render_learning_mode_switcher()
    st.divider()

    if selected_mode == "📖 Read":
        render_read_mode()
    elif selected_mode == "🔊 Listen":
        render_listen_mode()
    elif selected_mode == "🧠 Visual Learn":
        render_visual_mode()


def render_read_mode() -> None:
    """Render Read mode with simplified notes, takeaways, and vocabulary."""
    st.subheader("📖 Read Mode")

    with st.expander("✨ Simplified notes and reading experience", expanded=True):
        render_read_mode_accessibility_panel()

        if st.button("Generate Simplified Version", key="gen_simplify"):
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
                return Math.max(1, sentence.trim().split(/\s+/).length);
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


def render_visual_mode() -> None:
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
    selected_label = st.selectbox(
        "Choose one visual type",
        options=["Select a visual", "🔄 Flowchart", "🧠 Mind Map"],
        key="visual_choice",
    )

    if selected_label == "🔄 Flowchart":
        st.session_state.selected_visual = "flowchart"
    elif selected_label == "🧠 Mind Map":
        st.session_state.selected_visual = "mind_map"
    else:
        st.session_state.selected_visual = None

    selected_visual = st.session_state.get("selected_visual")
    if not selected_visual:
        st.info("Please select exactly one visual type before generating.")

    if st.button("🎨 Generate Visual", type="primary", key="gen_visual"):
        if not st.session_state.document_text:
            st.warning("Upload a document or extract text before generating a visual.")
        elif selected_visual not in {"flowchart", "mind_map"}:
            st.warning("Please select exactly one visual type before generating.")
        else:
            with st.spinner("Generating visual..."):
                try:
                    visual = generate_visual_content(
                        st.session_state.document_text,
                        theme=visual_theme,
                        visual_type=selected_visual,
                    )
                    st.session_state.visual_content = visual
                    st.success(f"✅ { 'Flowchart' if selected_visual == 'flowchart' else 'Mind Map' } created")
                except (VisualError, LLMRouterError) as exc:
                    show_user_error("Could not create the selected visual. Please try again.", exc)

    if st.session_state.visual_content:
        visual = st.session_state.visual_content
        st.markdown(f"## 🖼️ {visual.get('title', 'Visual Learning')}")
        st.markdown(f"**Topic:** {visual.get('topic', 'General').title()}")
        if visual.get("description"):
            st.markdown(f"*{visual.get('description')}*")

        st.divider()

        if selected_visual == "flowchart":
            st.markdown("### 🔄 Flowchart")
            st.markdown("*Step-by-step process — emoji nodes, color-coded boxes, minimal text*")
            flowchart_path = visual.get("flowchart_path", "")
            if flowchart_path and os.path.exists(flowchart_path):
                try:
                    image = Image.open(flowchart_path)
                    st.image(image, use_container_width=True, caption="Flowchart")
                    with open(flowchart_path, "rb") as img_file:
                        st.download_button(
                            label="⬇️ Download Flowchart",
                            data=img_file.read(),
                            file_name="flowchart.png",
                            mime="image/png",
                            key="download_flowchart",
                        )
                except Exception as exc:
                    logger.exception("Could not display flowchart.")
                    st.warning("Flowchart could not be displayed.")
            else:
                st.info("Flowchart not available.")

        elif selected_visual == "mind_map":
            st.markdown("### 🧠 Mind Map")
            st.markdown("*Central concept with colorful emoji branches and short labels*")
            mindmap_path = visual.get("mindmap_path", "")
            if mindmap_path and os.path.exists(mindmap_path):
                try:
                    image = Image.open(mindmap_path)
                    st.image(image, use_container_width=True, caption="Mind Map")
                    with open(mindmap_path, "rb") as img_file:
                        st.download_button(
                            label="⬇️ Download Mind Map",
                            data=img_file.read(),
                            file_name="mind_map.png",
                            mime="image/png",
                            key="download_mindmap",
                        )
                except Exception as exc:
                    logger.exception("Could not display mind map.")
                    st.warning("Mind map could not be displayed.")
            else:
                st.info("Mind map not available.")

        st.divider()
        structure = visual.get("structure", {})
        if structure:
            col1, col2 = st.columns(2)
            with col1:
                steps = structure.get("steps", [])
                if steps:
                    st.markdown("#### 📍 Process Steps")
                    for i, step in enumerate(steps, 1):
                        st.markdown(f"{i}. {step}")
                inputs = structure.get("inputs", [])
                if inputs:
                    st.markdown("#### 📥 Inputs/Resources")
                    for input_item in inputs:
                        st.markdown(f"• {input_item}")
            with col2:
                outputs = structure.get("outputs", [])
                if outputs:
                    st.markdown("#### 📤 Outputs/Results")
                    for output_item in outputs:
                        st.markdown(f"• {output_item}")
                key_comp = structure.get("key_component", "")
                if key_comp:
                    st.markdown("#### ⚙️ Key Component")
                    st.info(f"**{key_comp}**")


def render_chat_section() -> None:
    """Render RAG-based chat with document."""
    if not st.session_state.document_text:
        return
    
    st.header("💬 Ask Questions")
    st.markdown("Ask anything about your document and get smart answers!")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    user_question = st.chat_input("Ask a question about the content...")
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
                answer = generate_answer(user_question, context)
                
            except (DocumentError, GeminiConfigurationError, GeminiAPIError, LLMRouterError, ValueError) as exc:
                logger.exception("Chat answer generation failed.")
                answer = "I could not answer that right now. Please try rephrasing your question."
            except Exception as exc:
                logger.exception("Unexpected chat failure.")
                answer = "Something went wrong while answering. Please try again."
        
        st.markdown(answer)
        # Persist chat turn to SQLite so chat_history appears immediately
        try:
            user_id = _resolve_anonymous_user_id()
            document_id_for_db = st.session_state.get("saved_document_id")
            save_chat(
                user_id=user_id,
                document_id=document_id_for_db,
                user_message=user_question,
                ai_response=answer,
            )
            print("Chat saved to database")
        except Exception as exc:
            logger.exception("Failed to save chat to database: %s", exc)
    
    st.session_state.chat_history.append({"role": "assistant", "content": answer})


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

    render_home()
    st.divider()
    render_upload_section()
    st.divider()
<<<<<<< HEAD
    render_quiz_section()
    st.divider()
    render_simplified_content()
=======
    render_word_explorer()
    st.divider()
    render_learning_modes()
>>>>>>> main
    st.divider()
    render_chat_section()


if __name__ == "__main__":
    main()

