"""Vocabulary support for Prototype 2.

Provides word definitions and explanations during reading.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class VocabularyEntry:
    """A vocabulary word and its explanation."""

    word: str
    definition: str
    context: str | None = None
    example: str | None = None


class VocabularyManager:
    """Manages vocabulary popup and word explanations.
    
    TODO: Integrate with reading view.
    TODO: Extract vocabulary from content.
    TODO: Support custom vocabulary lists.
    TODO: Handle word selection/highlighting in Streamlit.
    """

    def __init__(self) -> None:
        """Initialize vocabulary manager."""
        self._vocabulary: dict[str, VocabularyEntry] = {}
        self._selected_word: str | None = None
        self._on_word_selected_callbacks: list[Callable[[VocabularyEntry], None]] = []

    def add_vocabulary_entry(self, entry: VocabularyEntry) -> None:
        """Add a word to vocabulary.
        
        Args:
            entry: Vocabulary entry to add.
        
        TODO: Handle duplicate words.
        TODO: Validate entry data.
        """
        # TODO: Implement entry addition
        pass

    def get_vocabulary_entry(self, word: str) -> VocabularyEntry | None:
        """Get vocabulary entry for a word.
        
        Args:
            word: Word to look up.
        
        Returns:
            VocabularyEntry: Entry if found, None otherwise.
        
        TODO: Handle case-insensitive lookup.
        """
        # TODO: Implement entry retrieval
        return None

    def select_word(self, word: str) -> None:
        """Select a word for vocabulary display.
        
        Args:
            word: Word to select.
        
        TODO: Look up word in vocabulary.
        TODO: Trigger on_word_selected callbacks.
        """
        # TODO: Implement word selection
        pass

    def get_selected_word_entry(self) -> VocabularyEntry | None:
        """Get vocabulary entry for currently selected word.
        
        Returns:
            VocabularyEntry: Selected word entry, or None if none selected.
        """
        if self._selected_word is None:
            return None
        return self.get_vocabulary_entry(self._selected_word)

    def clear_selection(self) -> None:
        """Clear word selection.
        
        TODO: Trigger state change callbacks.
        """
        # TODO: Implement selection clearing
        pass

    def extract_vocabulary_from_content(self, content: str) -> list[VocabularyEntry]:
        """Extract vocabulary entries from content.
        
        Args:
            content: Text to extract vocabulary from.
        
        Returns:
            list[VocabularyEntry]: Extracted vocabulary entries.
        
        TODO: Implement vocabulary extraction logic.
        TODO: Integrate with backend summarization/analysis services.
        TODO: Handle duplicate detection.
        """
        # TODO: Implement vocabulary extraction
        return []

    def populate_from_extracted_vocabulary(
        self,
        entries: list[VocabularyEntry]
    ) -> None:
        """Populate vocabulary manager from extracted entries.
        
        Args:
            entries: Extracted vocabulary entries.
        
        TODO: Add entries to manager.
        TODO: Handle duplicates.
        """
        # TODO: Implement population
        pass

    def register_word_selection_callback(
        self,
        callback: Callable[[VocabularyEntry], None]
    ) -> None:
        """Register callback for word selection.
        
        Args:
            callback: Function to call when word is selected.
        """
        self._on_word_selected_callbacks.append(callback)

    def get_all_vocabulary(self) -> dict[str, VocabularyEntry]:
        """Get all vocabulary entries.
        
        Returns:
            dict[str, VocabularyEntry]: All vocabulary entries by word.
        """
        return self._vocabulary.copy()

    def search_vocabulary(self, query: str) -> list[VocabularyEntry]:
        """Search vocabulary entries.
        
        Args:
            query: Search query (case-insensitive substring match).
        
        Returns:
            list[VocabularyEntry]: Matching vocabulary entries.
        
        TODO: Implement search algorithm.
        """
        # TODO: Implement vocabulary search
        return []
