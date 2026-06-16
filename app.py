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

import io
import logging
import os
from pathlib import Path

import streamlit as st
from PIL import Image

from backend.chunker import chunk_text
from backend.parser import process_uploaded_file
from backend.retriever import retrieve_relevant_chunks_for_question
from backend.vector_store import build_index
from services.document_context import DocumentError, get_document_text
from services.gemini_service import (
    GeminiAPIError,
    GeminiConfigurationError,
)
from services.llm_router import generate_answer, LLMRouterError
from services.ocr_service import extract_text_from_image, OCRError
from services.simplification_service import simplify_text, SimplificationError
from services.vocabulary_service import generate_vocabulary, VocabularyError, explain_word
from services.tts_service import generate_audio, TTSError
from services.visual_service import generate_visual_content, VisualError

logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Dyslexic Learning Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_session_state() -> None:
    """Create Streamlit session keys."""
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
        
        # Settings
        "vocabulary_word_count": 10,
        "custom_word_input": "",
        
        # Accessibility settings
        "font_size": "Medium",      # Small, Medium, Large, Extra Large
        "line_spacing": "Relaxed",  # Normal, Relaxed, Extra Relaxed
        "reading_width": "Medium",  # Narrow, Medium, Wide
        
        # Chat
        "chat_history": [],
        
        # UI state
        "current_mode": "Read",  # Read, Listen, or Visual Learn
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
    """Apply larger fonts, wide spacing, and high readability for learners.
    
    Optimized for:
    - Dark mode compatibility
    - High contrast ratios
    - Readability
    - Dyslexia-friendly layout
    - Dynamic accessibility settings
    """
    # Get user accessibility settings
    font_size_map = {
        "Small": "18px",
        "Medium": "20px",
        "Large": "22px",
        "Extra Large": "24px",
    }
    
    line_spacing_map = {
        "Normal": "1.6",
        "Relaxed": "2.0",
        "Extra Relaxed": "2.4",
    }
    
    width_map = {
        "Narrow": "600px",
        "Medium": "1000px",
        "Wide": "1400px",
    }
    
    font_size = font_size_map.get(st.session_state.font_size, "18px")
    line_spacing = line_spacing_map.get(st.session_state.line_spacing, "2.0")
    reading_width = width_map.get(st.session_state.reading_width, "1000px")
    
    st.markdown(
        f"""
        <style>
        /* Base text styling */
        html, body, [class*="css"] {{
            font-size: {font_size};
            line-height: {line_spacing};
            letter-spacing: 0.05em;
        }}
        
        /* Main container */
        .block-container {{
            max-width: {reading_width};
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}
        
        /* Headings */
        h1, h2, h3, h4 {{
            letter-spacing: 0.02em;
            margin-top: 1.5rem !important;
            margin-bottom: 1rem !important;
            line-height: 1.4 !important;
        }}
        
        /* Paragraphs and text */
        .stMarkdown p, .stChatMessage {{
            font-size: {font_size};
            line-height: {line_spacing};
        }}
        
        /* Learning boxes - improved contrast */
        .document-meta, .learning-box {{
            padding: 1.2rem;
            border-left: 5px solid #1976d2;
            background: #f5f5f5;
            color: #121212;
            margin: 1.2rem 0;
            border-radius: 4px;
        }}
        
        /* Dark mode support for learning boxes */
        @media (prefers-color-scheme: dark) {{
            .document-meta, .learning-box {{
                background: #1e1e1e;
                color: #e0e0e0;
                border-left-color: #64b5f6;
            }}
        }}
        
        /* Vocabulary cards - high contrast */
        .vocabulary-item {{
            padding: 1.5rem;
            margin: 1.2rem 0;
            background: #ffffff;
            color: #111827;
            border-left: 6px solid #0f766e;
            border-radius: 6px;
            border: 1px solid #99f6e4;
        }}
        
        .vocabulary-item strong {{
            color: #0f172a;
            display: block;
            margin-bottom: 0.8rem;
            font-size: 1.2em;
            font-weight: 700;
        }}
        
        .vocabulary-item p {{
            color: #1f2937;
            margin: 0.5rem 0 0 0;
            font-size: 1.05em;
            line-height: {line_spacing};
            font-weight: 500;
        }}
        
        /* Dark mode vocabulary cards */
        @media (prefers-color-scheme: dark) {{
            .vocabulary-item {{
                background: #111827;
                color: #ffffff;
                border-left-color: #2dd4bf;
                border-color: #0f766e;
            }}
            
            .vocabulary-item strong {{
                color: #ffffff;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5);
            }}
            
            .vocabulary-item p {{
                color: #e2e8f0;
                text-shadow: 0 1px 1px rgba(0,0,0,0.3);
            }}
        }}
        
        /* Visual summary cards - high contrast */
        .visual-summary {{
            padding: 1.5rem;
            background: #ffffff;
            color: #111827;
            border-left: 6px solid #7c3aed;
            margin: 1.5rem 0;
            border-radius: 6px;
            border: 1px solid #ddd6fe;
        }}
        
        .visual-summary h3 {{
            color: #1f2937;
            margin: 0 0 1rem 0;
            font-size: 1.2em;
            font-weight: 700;
        }}
        
        .visual-summary p {{
            color: #374151;
            margin: 0.5rem 0;
            font-size: 1.05em;
            font-weight: 500;
        }}
        
        /* Dark mode visual summary */
        @media (prefers-color-scheme: dark) {{
            .visual-summary {{
                background: #111827;
                color: #ffffff;
                border-left-color: #a78bfa;
                border-color: #6d28d9;
            }}
            
            .visual-summary h3 {{
                color: #ffffff;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5);
            }}
            
            .visual-summary p {{
                color: #f3f4f6;
                text-shadow: 0 1px 1px rgba(0,0,0,0.3);
            }}
        }}
        
        /* Word explanation card */
        .word-explanation {{
            padding: 1.5rem;
            background: #fff3e0;
            border-left: 5px solid #f57c00;
            border-radius: 4px;
            margin: 1.5rem 0;
            border: 1px solid #ffe0b2;
        }}
        
        .word-explanation strong {{
            color: #e65100;
            font-size: 1.2em;
        }}
        
        .word-explanation .meaning {{
            color: #ef6c00;
            font-weight: 600;
            margin: 0.5rem 0;
        }}
        
        .word-explanation .explanation {{
            color: #e65100;
            margin: 0.5rem 0;
        }}
        
        .word-explanation .example {{
            color: #bf360c;
            font-style: italic;
            margin: 0.5rem 0;
        }}
        
        /* Dark mode word explanation */
        @media (prefers-color-scheme: dark) {{
            .word-explanation {{
                background: #bf360c;
                color: #ffe0b2;
                border-left-color: #ffb74d;
                border-color: #ff9800;
            }}
            
            .word-explanation strong {{
                color: #fff9c4;
            }}
            
            .word-explanation .meaning {{
                color: #ffcc80;
            }}
            
            .word-explanation .explanation {{
                color: #ffe0b2;
            }}
            
            .word-explanation .example {{
                color: #fff9c4;
            }}
        }}
        
        /* Buttons - high contrast */
        .stButton > button {{
            font-size: {font_size} !important;
            padding: 0.8rem 1.6rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.03em !important;
        }}
        
        /* Input fields */
        input, textarea, .stSelectbox, .stTextInput {{
            font-size: {font_size} !important;
            line-height: {line_spacing} !important;
            padding: 0.8rem !important;
        }}
        
        /* Radio buttons and selectors */
        .stRadio > label, .stSelectbox > label, .stTextInput > label {{
            font-size: {font_size} !important;
            font-weight: 500 !important;
            line-height: {line_spacing} !important;
        }}
        
        /* Expander styling */
        .streamlit-expanderHeader {{
            font-size: {font_size} !important;
            font-weight: 500 !important;
        }}
        
        /* Divider styling */
        hr {{
            margin: 2rem 0;
            border: none;
            border-top: 2px solid #e0e0e0;
        }}
        
        @media (prefers-color-scheme: dark) {{
            hr {{
                border-top-color: #404040;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_accessibility_settings() -> None:
    """Render accessibility settings panel in sidebar."""
    with st.sidebar:
        st.divider()
        st.markdown("### ⚙️ Accessibility Settings")
        
        st.session_state.font_size = st.radio(
            "Font Size:",
            options=["Small", "Medium", "Large", "Extra Large"],
            index=["Small", "Medium", "Large", "Extra Large"].index(st.session_state.font_size),
            key="font_size_selector",
            horizontal=True,
        )
        
        st.session_state.line_spacing = st.radio(
            "Line Spacing:",
            options=["Normal", "Relaxed", "Extra Relaxed"],
            index=["Normal", "Relaxed", "Extra Relaxed"].index(st.session_state.line_spacing),
            key="line_spacing_selector",
            horizontal=True,
        )
        
        st.session_state.reading_width = st.radio(
            "Reading Width:",
            options=["Narrow", "Medium", "Wide"],
            index=["Narrow", "Medium", "Wide"].index(st.session_state.reading_width),
            key="reading_width_selector",
            horizontal=True,
        )
        
        st.markdown("""
        **Tips for comfortable reading:**
        - **Extra Large** text with **Extra Relaxed** spacing is great for dyslexia
        - **Narrow** width helps focus on fewer words at a time
        - Use **Dark Mode** for better contrast at night
        """)
        st.divider()


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
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📖 Read", use_container_width=True, key="mode_read"):
            st.session_state.current_mode = "Read"
    with col2:
        if st.button("🎵 Listen", use_container_width=True, key="mode_listen"):
            st.session_state.current_mode = "Listen"
    with col3:
        if st.button("📊 Visual Learn", use_container_width=True, key="mode_visual"):
            st.session_state.current_mode = "Visual Learn"
    
    st.divider()
    
    # Render selected mode
    if st.session_state.current_mode == "Read":
        render_read_mode()
    elif st.session_state.current_mode == "Listen":
        render_listen_mode()
    elif st.session_state.current_mode == "Visual Learn":
        render_visual_mode()


def render_read_mode() -> None:
    """Render Read mode with simplified notes and vocabulary."""
    st.subheader("📖 Read Mode")
    
    col1, col2 = st.columns(2)
    
    # Simplified Content
    with col1:
        st.markdown("### ✨ Simplified Notes")
        if st.button("Generate Simplified Version", key="gen_simplify"):
            with st.spinner("Simplifying text..."):
                try:
                    content = simplify_text(st.session_state.document_text)
                    st.session_state.simplified_content = content
                    st.success("✅ Simplified content generated!")
                except (SimplificationError, LLMRouterError) as exc:
                    show_user_error("Simplification could not be completed right now. Please try again.", exc)
        
        if st.session_state.simplified_content:
            st.markdown(st.session_state.simplified_content)
            
            # Download button
            st.download_button(
                label="⬇️ Download Simplified Text",
                data=st.session_state.simplified_content,
                file_name="simplified_notes.txt",
                mime="text/plain",
                key="download_simplified"
            )
    
    # Vocabulary
    with col2:
        st.markdown("### 🔤 Vocabulary List")
        
        # Word count selector
        st.markdown("**How many words would you like to learn?**")
        
        word_choice = st.radio(
            "Choose number of words:",
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
        
        if st.button("Extract Difficult Words", key="gen_vocab"):
            with st.spinner("Extracting vocabulary..."):
                try:
                    vocab = generate_vocabulary(
                        st.session_state.document_text,
                        word_count=st.session_state.vocabulary_word_count
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
                    unsafe_allow_html=True
                )
            
            # Download vocabulary
            import json
            vocab_json = json.dumps(st.session_state.vocabulary, indent=2)
            st.download_button(
                label="⬇️ Download Vocabulary",
                data=vocab_json,
                file_name="vocabulary.json",
                mime="application/json",
                key="download_vocab"
            )
    
    # Custom Word Explorer Section
    st.divider()
    st.markdown("### 🔍 Custom Word Explorer")
    st.markdown("**Learn the meaning of any word - even if it's not in your document!**")
    
    col_explorer1, col_explorer2 = st.columns([3, 1])
    
    with col_explorer1:
        word_input = st.text_input(
            "Enter a word to learn about:",
            placeholder="e.g., photosynthesis, algorithm, mitochondria",
            key="word_explorer_input"
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
            unsafe_allow_html=True
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
    
    # Audio generation options
    col1, col2 = st.columns([2, 1])
    with col1:
        speed = st.select_slider(
            "Speaking Speed",
            options=["Slow", "Normal"],
            value="Normal",
            key="audio_speed"
        )
    
    if st.button("🎙️ Generate Audio", type="primary", key="gen_audio"):
        with st.spinner("Generating audio..."):
            try:
                slow = (speed == "Slow")
                audio_path = generate_audio(text_to_listen, slow=slow)
                st.session_state.audio_file = audio_path
                st.success("✅ Audio generated!")
            except TTSError as exc:
                show_user_error("Audio generation failed. Try a shorter text selection.", exc)
    
    if st.session_state.audio_file and os.path.exists(st.session_state.audio_file):
        st.markdown("### 🎧 Play Audio")
        with open(st.session_state.audio_file, "rb") as audio_file:
            audio_data = audio_file.read()
            st.audio(audio_data, format="audio/mp3")
        
        # Download button
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
    apply_dyslexia_friendly_styles()
    render_accessibility_settings()
    
    render_home()
    st.divider()
    render_upload_section()
    st.divider()
    render_learning_modes()
    st.divider()
    render_chat_section()


if __name__ == "__main__":
    main()

