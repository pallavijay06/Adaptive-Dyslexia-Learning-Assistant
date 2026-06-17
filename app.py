"""Streamlit frontend for the Dyslexic Learning Assistant.

Features:
- Document Upload (PDF, PPTX, DOCX)
- Image OCR (PNG, JPG, GIF, WebP)
- Simplified Content Generation
- Vocabulary Extraction with Custom Count
- Text-to-Speech Audio (with natural text cleaning)
- Visual Learning (Flowcharts, Concept Maps, Mermaid Diagrams)
- Custom Word Explorer
- Multi-mode Learning (Read, Listen, Visual Learn)
- RAG-based Chat with Documents
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
from components.accessibility.read_mode_accessibility import render_read_mode_accessibility_panel
from components.reading.reading_view import (
    render_key_takeaways,
    render_learning_mode_switcher,
    render_read_mode as render_reading_mode,
)
from components.reading.vocabulary_popup import render_vocabulary_panel
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
from services.llm_router import generate_answer, LLMRouterError
from services.ocr_service import extract_text_from_image, OCRError
from services.simplification_service import simplify_text, SimplificationError
from services.vocabulary_service import generate_vocabulary, VocabularyError, explain_word
from services.tts_service import cleanup_audio_file, generate_audio, TTSError
from services.visual_service import generate_visual_content, VisualError

logger = logging.getLogger(__name__)


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
        "vocabulary": None,
        "visual_content": None,
        "audio_file": None,
        "word_explanation": None,
        "reading_difficult_words": [],

        # Settings
        "vocabulary_word_count": 10,
        "custom_word_input": "",

        # Chat
        "chat_history": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
            render_vocabulary_panel(st.session_state.simplified_content)
            st.download_button(
                label="⬇️ Download Simplified Text",
                data=st.session_state.simplified_content,
                file_name="simplified_notes.txt",
                mime="text/plain",
                key="download_simplified"
            )
        else:
            st.info("Generate a simplified version to view the dyslexia-friendly reading experience.")

    st.divider()
    st.markdown("### 🔤 Vocabulary Tools")
    st.markdown("Use the backend vocabulary extractor to generate a custom study list.")

    col1, col2 = st.columns([2, 1])
    with col1:
        word_choice = st.radio(
            "How many words would you like to learn?",
            options=["5", "10", "20", "Custom"],
            index=(
                ["5", "10", "20"].index(str(st.session_state.vocabulary_word_count))
                if str(st.session_state.vocabulary_word_count) in ["5", "10", "20"]
                else 3
            ),
            horizontal=True,
            key="vocab_word_selector"
        )

        if word_choice == "Custom":
            custom_count = st.number_input(
                "Enter custom number:",
                min_value=1,
                max_value=100,
                value=10,
                step=1,
                key="vocab_custom_input"
            )
            st.session_state.vocabulary_word_count = custom_count
        else:
            st.session_state.vocabulary_word_count = int(word_choice)

    with col2:
        if st.button("Extract Difficult Words", key="gen_vocab"):
            with st.spinner("Extracting vocabulary..."):
                try:
                    vocab = generate_vocabulary(
                        st.session_state.document_text,
                        word_count=st.session_state.vocabulary_word_count,
                    )
                    st.session_state.vocabulary = vocab
                    st.success(f"✅ Found {len(vocab)} difficult words!")
                except (VocabularyError, LLMRouterError) as exc:
                    show_user_error("Vocabulary could not be extracted right now. Try again or use fewer words.", exc)

    if st.session_state.vocabulary:
        st.markdown(f"**Found {len(st.session_state.vocabulary)} words:**")
        for item in st.session_state.vocabulary:
            st.markdown(
                f"<div class='vocabulary-item'>"
                f"<strong>{item.get('word', 'Unknown')}</strong>"
                f"<p>{item.get('meaning', 'No meaning provided')}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )
        import json

        vocab_json = json.dumps(st.session_state.vocabulary, indent=2)
        st.download_button(
            label="⬇️ Download Vocabulary",
            data=vocab_json,
            file_name="vocabulary.json",
            mime="application/json",
            key="download_vocab"
        )

    st.divider()
    st.markdown("### 🔍 Custom Word Explorer")
    st.markdown("**Learn the meaning of any word - even if it's not in your document!**")

    col_explorer1, col_explorer2 = st.columns([3, 1])
    with col_explorer1:
        word_input = st.text_input(
            "Enter a word to learn about:",
            placeholder="e.g., photosynthesis, algorithm, mitochondria",
            key="word_explorer_input",
        )

    with col_explorer2:
        explore_button = st.button("Explore 🔍", key="explore_word_btn")

    if explore_button and word_input:
        with st.spinner(f"Learning about '{word_input}'..."):
            try:
                explanation = explain_word(word_input)
                st.session_state.word_explanation = explanation
                st.success("✅ Found explanation!")
            except (VocabularyError, LLMRouterError) as exc:
                show_user_error("I could not explain that word right now. Please try another word.", exc)

    if st.session_state.word_explanation:
        exp = st.session_state.word_explanation
        st.markdown(
            f"<div class='word-explanation'>"
            f"<strong>{exp.get('word', 'Unknown')}</strong><br><br>"
            f"<div class='meaning'><strong>📖 Meaning:</strong> {exp.get('meaning', '')}</div>"
            f"<div class='explanation'><strong>📝 Explanation:</strong> {exp.get('explanation', '')}</div>"
            f"<div class='example'><strong>💡 Example:</strong> \"{exp.get('example', '')}\"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


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
        audio_text = json.dumps(text_to_listen)
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
            .listen-sentence {{
                padding: 12px 14px;
                margin-bottom: 10px;
                border-radius: 12px;
                transition: background-color 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
                background-color: transparent;
                border: 1px solid transparent;
            }}
            .listen-sentence.active {{
                background-color: rgba(255, 241, 130, 0.25);
                border-color: rgba(255, 210, 0, 0.6);
                box-shadow: 0 0 0 1px rgba(255, 210, 0, 0.3);
            }}
            .listen-text-container {{
                margin-top: 18px;
                padding: 12px;
                border-radius: 14px;
                background-color: rgba(255, 255, 255, 0.04);
            }}
        </style>
        <div class='audio-player-container'>
            <audio id='ttsAudio' controls style='width: 100%; display: block; min-height: 48px;'>
                <source src='data:audio/mp3;base64,{audio_base64}' type='audio/mpeg'>
                Your browser does not support HTML5 audio.
            </audio>
            <div style='margin-top: 12px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;'>
                <label for='speedSelector' style='font-weight: 600; margin-bottom: 0;'>Playback speed:</label>
                <select id='speedSelector' style='padding: 6px 10px;'>
                    <option value='0.75'>0.75x</option>
                    <option value='1.0' selected>1.0x</option>
                    <option value='1.25'>1.25x</option>
                    <option value='1.5'>1.5x</option>
                    <option value='1.75'>1.75x</option>
                    <option value='2.0'>2.0x</option>
                </select>
            </div>
            <div id='sentenceContainer' class='listen-text-container'></div>
        </div>
        <script>
            const audioText = JSON.parse({audio_text});
            const sentenceContainer = document.getElementById('sentenceContainer');
            const audioElem = document.getElementById('ttsAudio');
            const speedSelector = document.getElementById('speedSelector');

            const sentences = audioText
                .replace(/\s+/g, ' ')
                .trim()
                .split(/(?<=[.!?])\s+/)
                .filter(Boolean);

            let sentenceDuration = 0;
            let activeSentence = -1;

            function renderSentences() {{
                sentenceContainer.innerHTML = '<p>TEST TEXT</p>' + sentences
                    .map(function(sentence, index) {{
                        return '<div class="listen-sentence" data-index="' + index + '">' + sentence + '</div>';
                    }})
                    .join('');
            }}

            function updateActiveSentence() {{
                if (sentences.length === 0 || !audioElem.duration || isNaN(audioElem.duration)) {{
                    return;
                }}

                const currentTime = audioElem.currentTime;
                const index = Math.min(
                    sentences.length - 1,
                    Math.floor(currentTime / sentenceDuration)
                );

                if (audioElem.ended) {{
                    activeSentence = -1;
                }} else {{
                    activeSentence = index;
                }}

                const sentenceNodes = sentenceContainer.querySelectorAll('.listen-sentence');
                sentenceNodes.forEach(function(node) {{
                    const nodeIndex = Number(node.dataset.index);
                    node.classList.toggle('active', nodeIndex === activeSentence);
                }});
            }}

            function resetSentences() {{
                activeSentence = -1;
                const sentenceNodes = sentenceContainer.querySelectorAll('.listen-sentence');
                sentenceNodes.forEach(function(node) {{
                    node.classList.remove('active');
                }});
            }}

            audioElem.addEventListener('loadedmetadata', function() {{
                sentenceDuration = audioElem.duration / Math.max(sentences.length, 1);
                updateActiveSentence();
            }});

            audioElem.addEventListener('play', function() {{
                updateActiveSentence();
            }});

            audioElem.addEventListener('pause', function() {{
                updateActiveSentence();
            }});

            audioElem.addEventListener('timeupdate', function() {{
                updateActiveSentence();
            }});

            audioElem.addEventListener('ended', function() {{
                resetSentences();
            }});

            audioElem.addEventListener('seeked', function() {{
                updateActiveSentence();
            }});

            speedSelector.addEventListener('change', function() {{
                audioElem.playbackRate = parseFloat(this.value);
                updateActiveSentence();
            }});

            renderSentences();
        </script>
        """

        components.html(audio_html, height=900)

        st.download_button(
            label="⬇️ Download Audio",
            data=audio_data,
            file_name="learning_audio.mp3",
            mime="audio/mpeg",
            key="download_audio"
        )


def render_visual_mode() -> None:
    """Render Visual Learn mode with actual PNG diagrams and visual content.
    
    Displays generated educational diagrams as images with supporting information.
    """
    st.subheader("📊 Visual Learn Mode")
    
    st.markdown("**See your content as professional educational diagrams!**")
    st.info("📈 Diagrams are generated as PNG images for clarity and accessibility.")
    
    if st.button("🎨 Generate Visual Diagram", type="primary", key="gen_visual"):
        with st.spinner("Creating visual diagram..."):
            try:
                visual = generate_visual_content(st.session_state.document_text)
                st.session_state.visual_content = visual
                st.success("✅ Visual diagram generated!")
            except (VisualError, LLMRouterError) as exc:
                show_user_error("Visual learning could not create a diagram right now. Please try again.", exc)
    
    if st.session_state.visual_content:
        visual = st.session_state.visual_content
        
        # Header with title and metadata
        st.markdown(
            f"<div class='visual-summary'>"
            f"<h3>{visual.get('title', 'Visual Summary')}</h3>"
            f"<p><strong>Type:</strong> {visual.get('type', 'flowchart').replace('_', ' ').title()}</p>"
            f"<p><strong>Description:</strong> {visual.get('description', '')}</p>"
            f"</div>",
            unsafe_allow_html=True
        )
        
        # Display diagram image
        diagram_path = visual.get('diagram_image_path', '')
        if diagram_path and os.path.exists(diagram_path):
            st.markdown("### 📈 Educational Diagram")
            try:
                image = Image.open(diagram_path)
                st.image(image, use_container_width=True, caption=visual.get('title', 'Diagram'))
            except Exception as exc:
                logger.exception("Could not display generated diagram.")
                st.warning("The diagram was created, but it could not be displayed here.")
        else:
            st.info("Diagram image not available, showing structure instead.")
        
        # Display structured content
        col1, col2 = st.columns(2)
        
        with col1:
            nodes = visual.get('nodes', [])
            if nodes:
                st.markdown("### 🔹 Key Concepts")
                for node in nodes:
                    st.markdown(f"• {node}")
        
        with col2:
            edges = visual.get('edges', [])
            if edges:
                st.markdown("### 🔗 Connections")
                for source, target in edges:
                    st.markdown(f"• {source} → {target}")
        
        # Branches for mind maps
        branches = visual.get('branches', {})
        if branches:
            st.markdown("### 🌳 Mind Map Branches")
            for branch_name, items in branches.items():
                with st.expander(f"📌 {branch_name}"):
                    for item in items:
                        st.markdown(f"• {item}")
        
        # Download options
        st.divider()
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        
        # Download diagram image
        if diagram_path and os.path.exists(diagram_path):
            with col_dl1:
                with open(diagram_path, "rb") as img_file:
                    st.download_button(
                        label="⬇️ Download Diagram",
                        data=img_file.read(),
                        file_name=f"{visual.get('title', 'diagram')}.png",
                        mime="image/png",
                        key="download_diagram_image"
                    )
        
        # Download structured data
        with col_dl2:
            import json
            # Remove image path from exported JSON
            export_data = {k: v for k, v in visual.items() if k != 'diagram_image_path'}
            visual_json = json.dumps(export_data, indent=2)
            st.download_button(
                label="⬇️ Download Structure",
                data=visual_json,
                file_name="visual_structure.json",
                mime="application/json",
                key="download_visual_structure"
            )
        
        # Full export
        with col_dl3:
            st.markdown("")  # Spacer for alignment


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
    
    st.session_state.chat_history.append({"role": "assistant", "content": answer})


def main() -> None:
    """Run the Streamlit app."""
    initialize_session_state()
    initialize_ui_preferences()

    render_home()
    st.divider()
    render_upload_section()
    st.divider()
    render_learning_modes()
    st.divider()
    render_chat_section()


if __name__ == "__main__":
    main()

