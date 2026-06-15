"""Theme management for Prototype 2.

Provides color theme selection and management for accessibility and readability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from components.ui_constants import THEMES, DEFAULT_THEME


@dataclass
class ThemeDefinition:
    """Theme color configuration."""

    name: str
    primary_bg: str
    primary_text: str
    secondary_bg: str
    secondary_text: str
    accent: str
    warning: str

    @classmethod
    def from_dict(cls, name: str, theme_dict: dict[str, str]) -> ThemeDefinition:
        """Create ThemeDefinition from dictionary.
        
        Args:
            name: Theme name.
            theme_dict: Dictionary with color keys.
        
        Returns:
            ThemeDefinition: Theme configuration object.
        
        TODO: Add validation for required keys.
        """
        # TODO: Implement validation
        return cls(
            name=name,
            primary_bg=theme_dict.get("primary_bg", "#FFFFFF"),
            primary_text=theme_dict.get("primary_text", "#000000"),
            secondary_bg=theme_dict.get("secondary_bg", "#F5F5F5"),
            secondary_text=theme_dict.get("secondary_text", "#404040"),
            accent=theme_dict.get("accent", "#2E7D32"),
            warning=theme_dict.get("warning", "#F57C00"),
        )


class ThemeManager:
    """Manages application theme selection and color configuration.
    
    TODO: Integrate with Streamlit UI controls.
    TODO: Handle CSS/styling callbacks.
    TODO: Support custom theme creation.
    """

    def __init__(self) -> None:
        """Initialize theme manager with available themes."""
        self._current_theme: ThemeDefinition | None = None
        self._on_change_callbacks: list[Callable[[ThemeDefinition], None]] = []
        self._available_themes = self._load_available_themes()

    @staticmethod
    def _load_available_themes() -> dict[str, ThemeDefinition]:
        """Load available themes from constants.
        
        Returns:
            dict[str, ThemeDefinition]: Available theme definitions.
        
        TODO: Handle missing or malformed theme data.
        """
        # TODO: Implement theme loading with validation
        themes = {}
        for name, colors in THEMES.items():
            themes[name] = ThemeDefinition.from_dict(name, colors)
        return themes

    def get_current_theme(self) -> ThemeDefinition:
        """Get currently active theme.
        
        Returns:
            ThemeDefinition: Current theme configuration.
        
        TODO: Load from session state if available.
        """
        # TODO: Implement theme retrieval
        if self._current_theme is None:
            self._current_theme = self._available_themes.get(
                DEFAULT_THEME,
                ThemeDefinition.from_dict(DEFAULT_THEME, THEMES[DEFAULT_THEME])
            )
        return self._current_theme

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names.
        
        Returns:
            list[str]: Theme names.
        """
        return list(self._available_themes.keys())

    def set_theme(self, theme_name: str) -> None:
        """Set active theme by name.
        
        Args:
            theme_name: Name of theme to activate.
        
        Raises:
            ValueError: If theme_name not in available themes.
        
        TODO: Validate theme_name.
        TODO: Trigger on_change callbacks.
        """
        # TODO: Implement theme switching with validation
        pass

    def register_on_change(self, callback: Callable[[ThemeDefinition], None]) -> None:
        """Register callback for theme changes.
        
        Args:
            callback: Function to call when theme changes.
        """
        self._on_change_callbacks.append(callback)

    def create_custom_theme(
        self,
        name: str,
        colors: dict[str, str]
    ) -> ThemeDefinition:
        """Create and register a custom theme.
        
        Args:
            name: Custom theme name.
            colors: Dictionary with color keys (see THEMES for required keys).
        
        Returns:
            ThemeDefinition: Created theme definition.
        
        Raises:
            ValueError: If required keys are missing.
        
        TODO: Validate all required color keys present.
        TODO: Register theme in manager.
        TODO: Persist custom theme if needed.
        """
        # TODO: Implement custom theme creation
        return ThemeDefinition.from_dict(name, colors)

    def reset_to_default(self) -> None:
        """Reset to default theme.
        
        TODO: Trigger on_change callbacks.
        """
        # TODO: Implement reset to default
        pass
