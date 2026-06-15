"""Font settings management for Prototype 2.

Provides font family and font size configuration for dyslexia-friendly reading.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from components.ui_constants import FONT_FAMILIES, FONT_SIZES


@dataclass
class FontSettings:
    """Font configuration state."""

    family: str
    size: str

    def get_font_size_pixels(self) -> int:
        """Get current font size in pixels.
        
        Returns:
            int: Font size in pixels.
        
        TODO: Validate size key exists in FONT_SIZES.
        """
        # TODO: Implement font size lookup
        return FONT_SIZES.get(self.size, 16)

    def get_available_families(self) -> list[str]:
        """Get list of available font families.
        
        Returns:
            list[str]: Available font families.
        """
        return FONT_FAMILIES.copy()

    def get_available_sizes(self) -> list[str]:
        """Get list of available font sizes.
        
        Returns:
            list[str]: Available size keys.
        """
        return list(FONT_SIZES.keys())


class FontSettingsManager:
    """Manages font settings and rendering preferences.
    
    TODO: Integrate with Streamlit UI controls.
    TODO: Handle font rendering callbacks.
    """

    def __init__(self) -> None:
        """Initialize font settings manager with defaults."""
        self._settings: FontSettings | None = None
        self._on_change_callbacks: list[Callable[[FontSettings], None]] = []

    def get_settings(self) -> FontSettings:
        """Get current font settings.
        
        Returns:
            FontSettings: Current font configuration.
        
        TODO: Load from session state if available.
        """
        # TODO: Implement settings retrieval
        if self._settings is None:
            self._settings = FontSettings(family="sans-serif", size="normal")
        return self._settings

    def set_family(self, family: str) -> None:
        """Update font family.
        
        Args:
            family: Font family name.
        
        Raises:
            ValueError: If family is not in available families.
        
        TODO: Validate family against FONT_FAMILIES.
        TODO: Trigger on_change callbacks.
        """
        # TODO: Implement family validation and update
        pass

    def set_size(self, size: str) -> None:
        """Update font size.
        
        Args:
            size: Font size key (e.g., "normal", "large").
        
        Raises:
            ValueError: If size is not in available sizes.
        
        TODO: Validate size against FONT_SIZES.
        TODO: Trigger on_change callbacks.
        """
        # TODO: Implement size validation and update
        pass

    def increase_size(self) -> None:
        """Increase font size by one step.
        
        TODO: Determine next size in order.
        TODO: Trigger on_change callbacks.
        """
        # TODO: Implement size increment
        pass

    def decrease_size(self) -> None:
        """Decrease font size by one step.
        
        TODO: Determine previous size in order.
        TODO: Trigger on_change callbacks.
        """
        # TODO: Implement size decrement
        pass

    def register_on_change(self, callback: Callable[[FontSettings], None]) -> None:
        """Register callback for settings changes.
        
        Args:
            callback: Function to call when settings change.
        """
        self._on_change_callbacks.append(callback)

    def reset_to_defaults(self) -> None:
        """Reset font settings to application defaults.
        
        TODO: Trigger on_change callbacks.
        """
        # TODO: Implement reset to defaults
        pass
