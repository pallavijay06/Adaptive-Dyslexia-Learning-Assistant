"""Test script to demonstrate the new educational visual learning system.

This script generates sample educational visuals for common topics
and displays them to show the improvements over the old system.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services.educational_visuals import (
    create_educational_illustration,
    create_process_flowchart,
    create_concept_summary,
    detect_topic,
)

# Sample test content for different topics
TEST_TOPICS = {
    "Photosynthesis": {
        "content": """
        Photosynthesis is the process by which plants convert light energy into chemical energy.
        During photosynthesis, plants take in sunlight, water, and carbon dioxide.
        They use these to create glucose and oxygen.
        Sunlight is captured by chlorophyll in the leaf cells.
        The light energy drives the chemical reactions.
        Water is absorbed through the roots and transported to the leaves.
        Carbon dioxide enters the leaf through tiny pores called stomata.
        The process occurs in two main stages: light reactions and dark reactions.
        The light reactions occur in the thylakoid membranes.
        The dark reactions, or Calvin cycle, occur in the stroma.
        Glucose produced is used by the plant for energy and growth.
        Oxygen is released as a byproduct into the atmosphere.
        """,
        "steps": [
            "☀️ Sunlight enters the leaf",
            "🌿 Chlorophyll captures light energy",
            "💧 Water is split into hydrogen and oxygen",
            "🫁 Oxygen is released as waste",
            "🍃 Glucose is created from carbon dioxide",
            "⚡ Energy is stored in the glucose",
        ],
        "inputs": ["Sunlight", "Water", "Carbon Dioxide"],
        "outputs": ["Glucose", "Oxygen"],
        "key_component": "Chlorophyll",
    },
    "Water Cycle": {
        "content": """
        The water cycle is the process by which water moves between the Earth's surface and atmosphere.
        The sun heats water in oceans, rivers, and lakes.
        This causes evaporation, where water becomes water vapor.
        Water vapor rises into the atmosphere and cools.
        When cooled, water vapor condenses into tiny water droplets.
        These droplets form clouds in the sky.
        As clouds become heavy with water, precipitation occurs.
        Precipitation can be rain, snow, sleet, or hail.
        The water falls back to Earth's surface.
        Some water is absorbed by soil and plants.
        This is called infiltration and transpiration.
        Some water flows across the surface as runoff.
        Runoff flows into rivers, lakes, and oceans.
        The cycle then repeats continuously.
        """,
        "steps": [
            "☀️ Sun heats water in oceans",
            "🌊 Water evaporates into vapor",
            "☁️ Vapor rises and condenses",
            "⛅ Clouds form in the atmosphere",
            "🌧️ Precipitation falls as rain",
            "🌍 Water collects in oceans and soil",
        ],
        "inputs": ["Solar Energy", "Water in Oceans"],
        "outputs": ["Rain", "Snow", "Water in Soil"],
        "key_component": "Solar Energy",
    },
    "Digestive System": {
        "content": """
        The digestive system breaks down food into nutrients the body can use.
        It starts when you put food in your mouth.
        Your teeth break food into smaller pieces.
        Saliva in your mouth helps soften the food.
        The food travels down the esophagus to the stomach.
        The stomach churns food with acids and enzymes.
        This creates a liquid called chyme.
        The chyme moves to the small intestine.
        The small intestine absorbs most nutrients.
        These nutrients pass into the bloodstream.
        Remaining waste moves to the large intestine.
        The large intestine absorbs water.
        Solid waste is stored in the rectum.
        Waste is eliminated through the anus.
        """,
        "steps": [
            "🍎 Food enters your mouth",
            "👄 Teeth and saliva break down food",
            "🫃 Food travels to stomach",
            "🔥 Stomach churns and digests food",
            "🧬 Small intestine absorbs nutrients",
            "💩 Remaining waste is eliminated",
        ],
        "inputs": ["Food", "Digestive Enzymes", "Water"],
        "outputs": ["Nutrients", "Energy", "Waste"],
        "key_component": "Small Intestine",
    },
}


def test_topic_detection():
    """Test topic detection functionality."""
    print("\n" + "=" * 60)
    print("TESTING TOPIC DETECTION")
    print("=" * 60)
    
    for topic_name, data in TEST_TOPICS.items():
        detected_topic = detect_topic(data["content"])
        expected = topic_name.lower().replace(" ", "_")
        match = "✓" if detected_topic in expected or expected in detected_topic else "✗"
        print(f"{match} {topic_name}: Detected as '{detected_topic}'")


def test_illustration_generation():
    """Test educational illustration generation."""
    print("\n" + "=" * 60)
    print("TESTING EDUCATIONAL ILLUSTRATION GENERATION")
    print("=" * 60)
    
    themes = ["light", "dark", "dyslexia_cream", "dyslexia_yellow"]
    
    for topic_name, data in list(TEST_TOPICS.items())[:1]:  # Test with first topic
        print(f"\nTopic: {topic_name}")
        
        for theme in themes:
            try:
                path = create_educational_illustration(
                    topic_name,
                    data["steps"],
                    theme=theme,
                )
                file_size = os.path.getsize(path) / 1024  # Convert to KB
                print(f"  ✓ {theme:20} - Generated: {path} ({file_size:.1f} KB)")
            except Exception as exc:
                print(f"  ✗ {theme:20} - Error: {exc}")


def test_flowchart_generation():
    """Test process flowchart generation."""
    print("\n" + "=" * 60)
    print("TESTING PROCESS FLOWCHART GENERATION")
    print("=" * 60)
    
    themes = ["light", "dark"]
    
    for topic_name, data in list(TEST_TOPICS.items())[:2]:  # Test with first two topics
        print(f"\nTopic: {topic_name}")
        
        for theme in themes:
            try:
                path = create_process_flowchart(
                    topic_name,
                    data["steps"],
                    theme=theme,
                )
                file_size = os.path.getsize(path) / 1024
                print(f"  ✓ {theme:20} - Generated: {path} ({file_size:.1f} KB)")
            except Exception as exc:
                print(f"  ✗ {theme:20} - Error: {exc}")


def test_concept_summary_generation():
    """Test concept summary card generation."""
    print("\n" + "=" * 60)
    print("TESTING CONCEPT SUMMARY GENERATION")
    print("=" * 60)
    
    themes = ["light", "dark", "dyslexia_cream"]
    
    for topic_name, data in TEST_TOPICS.items():
        print(f"\nTopic: {topic_name}")
        
        for theme in themes:
            try:
                path = create_concept_summary(
                    topic_name,
                    data["inputs"],
                    data["outputs"],
                    data.get("key_component", ""),
                    theme=theme,
                )
                file_size = os.path.getsize(path) / 1024
                print(f"  ✓ {theme:20} - Generated: {path} ({file_size:.1f} KB)")
            except Exception as exc:
                print(f"  ✗ {theme:20} - Error: {exc}")


def test_full_visual_generation():
    """Test complete visual generation for a topic."""
    print("\n" + "=" * 60)
    print("TESTING COMPLETE VISUAL GENERATION PIPELINE")
    print("=" * 60)
    
    # Use photosynthesis as the test case
    topic_name = "Photosynthesis"
    data = TEST_TOPICS[topic_name]
    
    print(f"\nGenerating all three visuals for: {topic_name}")
    print("-" * 60)
    
    try:
        # 1. Educational Illustration
        print("1. Creating Educational Illustration...")
        illust_path = create_educational_illustration(
            topic_name,
            data["steps"],
            theme="light",
        )
        print(f"   ✓ Created: {illust_path}")
        
        # 2. Process Flowchart
        print("2. Creating Process Flowchart...")
        flow_path = create_process_flowchart(
            topic_name,
            data["steps"],
            theme="light",
        )
        print(f"   ✓ Created: {flow_path}")
        
        # 3. Concept Summary
        print("3. Creating Concept Summary...")
        summary_path = create_concept_summary(
            topic_name,
            data["inputs"],
            data["outputs"],
            data.get("key_component", ""),
            theme="light",
        )
        print(f"   ✓ Created: {summary_path}")
        
        print("\n" + "=" * 60)
        print("VISUAL GENERATION SUCCESSFUL!")
        print("=" * 60)
        print(f"\nGenerated Files:")
        print(f"  1. Illustration: {illust_path}")
        print(f"  2. Flowchart:    {flow_path}")
        print(f"  3. Summary:      {summary_path}")
        print(f"\nThese are now ready for display in the Streamlit app!")
        
    except Exception as exc:
        print(f"\n✗ Error during generation: {exc}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  EDUCATIONAL VISUAL LEARNING SYSTEM - TEST SUITE  ".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Run tests
    test_topic_detection()
    test_illustration_generation()
    test_flowchart_generation()
    test_concept_summary_generation()
    test_full_visual_generation()
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run the Streamlit app: streamlit run app.py")
    print("2. Upload a document with educational content")
    print("3. Switch to 'Visual Learn' mode")
    print("4. Click 'Generate Educational Visuals'")
    print("5. View the three types of educational visuals!")


if __name__ == "__main__":
    main()
