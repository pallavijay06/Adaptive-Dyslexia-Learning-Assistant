"""Standalone Streamlit demo for the STEM Diagram Explanation feature."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.stem.diagram_explainer import explain_diagram


def main() -> None:
    st.set_page_config(page_title="Diagram Explanation Demo", layout="centered")
    st.title("Diagram Explanation Demo")
    st.write(
        "Upload a clear PNG or JPG diagram image and get a simple explanation."
    )

    uploaded_file = st.file_uploader(
        "Upload PNG, JPG, or JPEG image",
        type=["png", "jpg", "jpeg"],
    )

    if uploaded_file is None:
        st.info("Upload an image to see a diagram explanation.")
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as temp_file:
        temp_file.write(uploaded_file.getvalue())
        temp_image_path = temp_file.name

    image = Image.open(temp_image_path)
    st.image(image, use_container_width=True, caption="Uploaded diagram")

    with st.spinner("Analyzing diagram..."):
        explanation = explain_diagram(temp_image_path)

    st.subheader("Diagram Type")
    st.write(explanation["diagram_type"])
    st.subheader("Purpose")
    st.write(explanation.get("purpose", ""))

    st.subheader("How It Works")
    steps = explanation.get("how_it_works") or []
    if steps:
        for i, step in enumerate(steps, start=1):
            st.write(f"{i}. {step}")
    else:
        st.write("No steps available.")

    st.subheader("Component Roles")
    comp_roles = explanation.get("component_roles") or []
    if comp_roles:
        for cr in comp_roles:
            comp = cr.get("component", "")
            role = cr.get("role", "")
            st.write(f"• {comp}: {role}")
    else:
        st.write("None identified.")

    st.subheader("Key Concept")
    st.write(explanation.get("key_concept", ""))

    st.subheader("Simplified Explanation")
    st.write(explanation.get("simplified_explanation", ""))

    st.subheader("Key Takeaway")
    st.write(explanation.get("key_takeaway", ""))


if __name__ == "__main__":
    main()
