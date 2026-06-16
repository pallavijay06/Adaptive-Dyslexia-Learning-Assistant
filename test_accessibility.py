import streamlit as st

from components.session_state import initialize_ui_preferences
from components.accessibility.theme_settings import render_accessibility_sidebar

st.title("Accessibility Test")

initialize_ui_preferences()

settings = render_accessibility_sidebar()

st.write("Current Settings")

st.json(settings)