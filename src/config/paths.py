"""
Path Manager

This module handles path resolution for the Hytale Mod Updater,
including base paths, resources paths, and data directories.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from src.os_detector.platform_detector import PlatformDetector


class PathManager:
    """Manage path resolution for the application."""
    
    def __init__(self):
        """Initialize path manager with resolved paths."""
        self._base_path = self._resolve_base_path()
        self._resources_path = os.path.join(self._base_path, "resources")
        self._data_path = os.path.join(self._base_path, "data")
        self._config_path = os.path.join(self._base_path, "config.json")
        self._log_path = os.path.join(self._base_path, "app_debug.log")
    
    @staticmethod
    def _resolve_base_path() -> str:
        """Resolve the base path (executable directory or workspace root)."""
        # For frozen apps, use the executable directory (not _MEIPASS temp dir)
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            # For development, use the parent directory of src (Hytale_Mod_Updater)
            return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    @property
    def base_path(self) -> str:
        """Get the base path."""
        return self._base_path
    
    @property
    def resources_path(self) -> str:
        """Get the resources directory path."""
        return self._resources_path
    
    @property
    def data_path(self) -> str:
        """Get the data directory path."""
        return self._data_path
    
    @property
    def config_path(self) -> str:
        """Get the config file path."""
        return self._config_path
    
    @property
    def log_path(self) -> str:
        """Get the log file path."""
        return self._log_path
    
    @property
    def playwright_browsers_path(self) -> str:
        """Get Playwright browsers path for current platform."""
        detector = PlatformDetector()
        browser_dir = detector.get_browser_directory_name()
        return os.path.join(self._base_path, "playwright_browsers", "chromium-1208", browser_dir)
    
    # Theme name constants to avoid magic strings
    THEME_FOREST_LIGHT = "forest_light"
    THEME_FOREST_DARK = "forest_dark"

    def get_theme_path(self, theme_name: str) -> Optional[str]:
        """Get the path to a theme file."""
        theme_files = {
            self.THEME_FOREST_LIGHT: os.path.join(self._resources_path, "Forest-ttk-theme", "forest-light.tcl"),
            self.THEME_FOREST_DARK: os.path.join(self._resources_path, "Forest-ttk-theme", "forest-dark.tcl"),
        }
        return theme_files.get(theme_name)
    
    def ensure_directories(self):
        """Ensure all required directories exist."""
        # Don't create resources directory for frozen apps - it's bundled in _MEIPASS
        if not getattr(sys, 'frozen', False):
            os.makedirs(self._resources_path, exist_ok=True)
        os.makedirs(self._data_path, exist_ok=True)
        # Removed unnecessary backups and cache folders
    
    def resolve_resource_path(self, resource_name: str) -> str:
        """
        Resolve resource path for both development and frozen states.
        
        Args:
            resource_name: Name of the resource file (e.g., "kofi_button.png")
            
        Returns:
            str: Resolved path to the resource file
        """
        if getattr(sys, 'frozen', False):
            # Running as frozen executable
            if hasattr(sys, '_MEIPASS'):
                # Running as onefile - resources are in _MEIPASS/resources
                meipass = getattr(sys, '_MEIPASS', '')
                return os.path.join(meipass, "resources", resource_name)
            else:
                # Running as folder-based executable - resources are in executable directory
                return os.path.join(os.path.dirname(sys.executable), "resources", resource_name)
        else:
            # Running as script - use the resources path directly
            return os.path.join(self._resources_path, resource_name)