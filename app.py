"""Streamlit frontend for the Dyslexic Learning Assistant.

Features:
- Document Upload (PDF, PPTX, DOCX)
- Image OCR (PNG, JPG, GIF, WebP)
- Simplified Content Generation
- Text-to-Speech Audio (with natural text cleaning)
- Visual Learning (Flowcharts, Concept Maps, Mermaid Diagrams)
- Multi-mode Learning (Read, Listen, Visual Learn)
- RAG-based Chat with Documents
- Interactive vocabulary learning inline with reading
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import streamlit as st
from PIL import Image

from backend.chunker import chunk_text
from backend.parser import process_uploaded_file
from backend.retriever import retrieve_relevant_chunks_for_question
from backend.vector_store import build_index
from components.accessibility import render_accessibility_sidebar
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
from services.llm_router import generate_answer, LLMRouterError
from services.ocr_service import extract_text_from_image, OCRError
from services.simplification_service import simplify_text, SimplificationError
from services.vocabulary_service import explain_word, VocabularyError
from services.tts_service import generate_audio, TTSError
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
        "visual_content": None,
        "audio_file": None,

        # Chat
        "chat_history": [],

        # Caching
        "vocab_explain_cache": {},
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
    """Render Visual Learn mode with three educational visual types.
    
    Generates and displays:
    1. Educational Illustration - emoji-based learning flowchart
    2. Process Flowchart - step-by-step process diagram
    3. Concept Summary - visual summary card
    """
    st.subheader("📊 Visual Learn Mode")
    
    st.markdown("**Transform your learning into beautiful educational visuals!**")
    st.markdown(
        "Three visual types help you learn better:\n"
        "• 📚 **Educational Illustration** - Visual step-by-step guide\n"
        "• 🔄 **Process Flowchart** - Step-by-step process diagram\n"
        "• 🎯 **Concept Summary** - Key inputs, outputs, and components"
    )
    
    # Get UI preferences for theme
    preferences = get_ui_preferences()
    theme = preferences.get("theme", "Light").lower().replace(" ", "_")
    
    # Theme mapping to educational visuals theme names
    theme_mapping = {
        "light": "light",
        "dark": "dark",
        "cream": "dyslexia_cream",
        "yellow": "dyslexia_yellow",
    }
    visual_theme = theme_mapping.get(theme, "light")
    
    if st.button("🎨 Generate Educational Visuals", type="primary", key="gen_visual_edu"):
        with st.spinner("Creating three educational visuals..."):
            try:
                visual = generate_visual_content(st.session_state.document_text, theme=visual_theme)
                st.session_state.visual_content = visual
                st.success("✅ Three educational visuals created!")
            except (VisualError, LLMRouterError) as exc:
                show_user_error("Could not create educational visuals right now. Please try again.", exc)
    
    if st.session_state.visual_content:
        visual = st.session_state.visual_content
        
        # Header with topic and description
        st.markdown(f"## 🎓 {visual.get('title', 'Learning Visuals')}")
        st.markdown(f"**Topic:** {visual.get('topic', 'General').title()}")
        if visual.get('description'):
            st.markdown(f"*{visual.get('description')}*")
        
        st.divider()
        
        # 1. EDUCATIONAL ILLUSTRATION
        st.markdown("### 📚 Educational Illustration")
        st.markdown("*A visual step-by-step guide to understanding the concept*")
        
        illustration_path = visual.get('illustration_path', '')
        if illustration_path and os.path.exists(illustration_path):
            try:
                image = Image.open(illustration_path)
                st.image(image, use_container_width=True, caption="Educational Learning Flowchart")
                
                # Download button for illustration
                with open(illustration_path, "rb") as img_file:
                    st.download_button(
                        label="⬇️ Download Illustration",
                        data=img_file.read(),
                        file_name="educational_illustration.png",
                        mime="image/png",
                        key="download_illustration"
                    )
            except Exception as exc:
                logger.exception("Could not display educational illustration.")
                st.warning("Illustration could not be displayed.")
        else:
            st.info("Illustration not available.")
        
        st.divider()
        
        # 2. PROCESS FLOWCHART
        st.markdown("### 🔄 Process Flowchart")
        st.markdown("*A structured diagram showing the step-by-step process*")
        
        flowchart_path = visual.get('flowchart_path', '')
        if flowchart_path and os.path.exists(flowchart_path):
            try:
                image = Image.open(flowchart_path)
                st.image(image, use_container_width=True, caption="Process Flowchart")
                
                # Download button for flowchart
                with open(flowchart_path, "rb") as img_file:
                    st.download_button(
                        label="⬇️ Download Flowchart",
                        data=img_file.read(),
                        file_name="process_flowchart.png",
                        mime="image/png",
                        key="download_flowchart"
                    )
            except Exception as exc:
                logger.exception("Could not display process flowchart.")
                st.warning("Flowchart could not be displayed.")
        else:
            st.info("Flowchart not available.")
        
        st.divider()
        
        # 3. CONCEPT SUMMARY
        st.markdown("### 🎯 Concept Summary")
        st.markdown("*A visual summary of inputs, outputs, and key components*")
        
        summary_path = visual.get('summary_path', '')
        if summary_path and os.path.exists(summary_path):
            try:
                image = Image.open(summary_path)
                st.image(image, use_container_width=True, caption="Concept Summary Card")
                
                # Download button for summary
                with open(summary_path, "rb") as img_file:
                    st.download_button(
                        label="⬇️ Download Summary",
                        data=img_file.read(),
                        file_name="concept_summary.png",
                        mime="image/png",
                        key="download_summary"
                    )
            except Exception as exc:
                logger.exception("Could not display concept summary.")
                st.warning("Summary could not be displayed.")
        else:
            st.info("Summary not available.")
        
        st.divider()
        
        # Display extracted structure
        structure = visual.get('structure', {})
        if structure:
            col1, col2 = st.columns(2)
            
            with col1:
                steps = structure.get('steps', [])
                if steps:
                    st.markdown("#### 📍 Process Steps")
                    for i, step in enumerate(steps, 1):
                        st.markdown(f"{i}. {step}")
                
                inputs = structure.get('inputs', [])
                if inputs:
                    st.markdown("#### 📥 Inputs/Resources")
                    for input_item in inputs:
                        st.markdown(f"• {input_item}")
            
            with col2:
                outputs = structure.get('outputs', [])
                if outputs:
                    st.markdown("#### 📤 Outputs/Results")
                    for output_item in outputs:
                        st.markdown(f"• {output_item}")
                
                key_comp = structure.get('key_component', '')
                if key_comp:
                    st.markdown("#### ⚙️ Key Component")
                    st.info(f"**{key_comp}**")
        
        st.divider()
        
        # Download all visuals as JSON
        import json
        st.markdown("#### 💾 Export Options")
        export_data = {
            "topic": visual.get('topic'),
            "title": visual.get('title'),
            "description": visual.get('description'),
            "structure": visual.get('structure', {}),
        }
        visual_json = json.dumps(export_data, indent=2)
        st.download_button(
            label="⬇️ Download All Data as JSON",
            data=visual_json,
            file_name="visual_learning_data.json",
            mime="application/json",
            key="download_all_visuals"
        )


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
        
        html_result = f"""
        <div style="margin-top: 1rem; padding: 1rem; background-color: {theme['secondary_background']}; 
                    border: 1px solid {theme['border_color']}; border-radius: 8px; font-size: {font_size}px; 
                    line-height: 1.8; letter-spacing: {character_spacing};">
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
    apply_dyslexia_friendly_styles()
    render_accessibility_sidebar()

    render_home()
    st.divider()
    render_upload_section()
    st.divider()
    render_word_explorer()
    st.divider()
    render_learning_modes()
    st.divider()
    render_chat_section()


if __name__ == "__main__":
    main()

