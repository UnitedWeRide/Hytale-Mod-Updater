"""
Theme Manager

This module manages theme switching for the Hytale Mod Updater.
Simple dark forest theme with system detection.
"""

import os
import sys
import logging
import tkinter as tk
from typing import Optional

logger = logging.getLogger(__name__)


class ThemeManager:
    """Manage theme switching for the application."""
    
    def __init__(self, resources_path: str):
        """
        Initialize theme manager.
        
        Args:
            resources_path: Path to resources directory
        """
        self.resources_path = resources_path
        self._theme_name: Optional[str] = None
        self._theme_mode: Optional[str] = None
    
    def get_theme_paths(self) -> dict:
        """Get paths to all theme files."""
        return {
            "forest_light": os.path.join(self.resources_path, "Forest-ttk-theme", "forest-light.tcl"),
            "forest_dark": os.path.join(self.resources_path, "Forest-ttk-theme", "forest-dark.tcl"),
        }
    
    def _resolve_theme_path(self, theme_path: str) -> str:
        """
        Resolve theme path for both development and frozen states.
        
        Args:
            theme_path: Path to theme file
            
        Returns:
            str: Resolved path to theme file
        """
        if getattr(sys, 'frozen', False):
            # Running as frozen executable
            if hasattr(sys, '_MEIPASS'):
                # Running as onefile
                base_dir = os.path.join(sys._MEIPASS, "resources")  # type: ignore
                rel_path = os.path.relpath(theme_path, self.resources_path)
                return os.path.join(base_dir, rel_path)
            else:
                # Running as folder-based executable
                base_dir = os.path.join(os.path.dirname(sys.executable), "resources")
                rel_path = os.path.relpath(theme_path, self.resources_path)
                return os.path.join(base_dir, rel_path)
        else:
            # Running as script
            return theme_path
    
    def detect_system_theme(self) -> str:
        """
        Detect system theme preference.
        
        Returns:
            str: 'dark' if system prefers dark mode, 'light' otherwise
        """
        try:
            root = tk.Tk()
            root.withdraw()
            # Check Windows registry for dark mode preference
            if sys.platform == 'win32':
                import winreg
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                    )
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    winreg.CloseKey(key)
                    root.destroy()
                    return "dark" if value == 0 else "light"
                except (OSError, winreg.error) as e:
                    logger.warning("Failed to read Windows theme registry: %s", e)
            root.destroy()
        except (tk.TclError, RuntimeError) as e:
            logger.warning("Failed to initialize Tk root for theme detection: %s", e)
        return "dark"  # Default to dark
    
    def apply_theme(self, root: tk.Tk, theme_name: str = "forest", theme_mode: str = "auto") -> bool:
        """
        Apply a theme to the root window.
        
        Args:
            root: Tk root window
            theme_name: Name of the theme (only "forest" supported)
            theme_mode: Theme mode ("auto", "light", "dark")
            
        Returns:
            bool: True if successful, False otherwise
        """
        self._theme_name = theme_name
        
        # Auto-detect system theme if mode is "auto"
        if theme_mode == "auto":
            theme_mode = self.detect_system_theme()
        
        self._theme_mode = theme_mode
        
        theme_paths = self.get_theme_paths()
        
        try:
            if theme_name == "forest":
                if theme_mode == "light":
                    resolved_path = self._resolve_theme_path(theme_paths["forest_light"])
                    # Check if theme is already loaded
                    if "forest-light" not in root.tk.call("ttk::style", "theme", "names"):
                        root.tk.call("source", resolved_path)
                    root.tk.call("ttk::style", "theme", "use", "forest-light")
                else:
                    resolved_path = self._resolve_theme_path(theme_paths["forest_dark"])
                    # Check if theme is already loaded
                    if "forest-dark" not in root.tk.call("ttk::style", "theme", "names"):
                        root.tk.call("source", resolved_path)
                    root.tk.call("ttk::style", "theme", "use", "forest-dark")
            else:
                # Default to forest dark
                resolved_path = self._resolve_theme_path(theme_paths["forest_dark"])
                # Check if theme is already loaded
                if "forest-dark" not in root.tk.call("ttk::style", "theme", "names"):
                    root.tk.call("source", resolved_path)
                root.tk.call("ttk::style", "theme", "use", "forest-dark")
            
            logger.info(f"Theme applied: {theme_name}, mode: {theme_mode}")
            return True
        except (tk.TclError, OSError) as e:
            logger.error(f"Failed to apply theme: {e}")
            return False
    
    def get_current_theme(self) -> tuple:
        """Get the current theme name and mode."""
        return self._theme_name, self._theme_mode