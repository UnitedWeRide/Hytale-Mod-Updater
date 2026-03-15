"""
Settings Manager

This module handles loading, saving, and managing user settings for the Hytale Mod Updater.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manage user settings for the application."""
    
    DEFAULT_SETTINGS = {
        "theme": "forest",
        "theme_mode": "auto",
        "mod_directory": "",
        "debug_mode": False,
        "backup_enabled": True,
        "app_mode": "curseforge",
        "game_id": 70216,  # Hytale default game ID
        "game_name": "Hytale",
        "only_stable": True,  # Only update to stable versions
        "ignore_beta": True,  # Ignore beta versions
        "close_terminal_on_exit": True,  # Close terminal when app exits
        "download_rate_limit": 0.5,  # Rate limit delay between downloads in seconds
        "full_speed_db_pagination": False,  # Use all CPU threads for database pagination without rate limiting
        "automated_update_check": False,  # Automatically check for updates and download after loading mods
        "first_run": True,  # Flag to track first run (shows API key dialog)
        "restore_mods_on_launch": False  # Restore mods folder on app launch
    }
    
    def __init__(self, config_path: str | None = None):
        """
        Initialize the settings manager.
        
        Args:
            config_path: Path to the config file (default: config.json in parent directory)
        """
        if config_path is None:
            # Use the same logic as PathManager for frozen executables
            if getattr(sys, 'frozen', False):
                # Running as frozen executable
                base_dir = os.path.dirname(sys.executable)
                config_path = os.path.join(base_dir, "config.json")
            else:
                # Running as script
                config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        
        self.config_path = config_path
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from config file, or use defaults if not found."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    loaded = json.load(f)
                    logger.info(f"Loaded settings from {self.config_path}")
                    return {**self.DEFAULT_SETTINGS, **loaded}
            except (OSError, IOError, json.JSONDecodeError) as e:
                logger.error(f"Error loading settings: {e}, using defaults")
                return self.DEFAULT_SETTINGS.copy()
        else:
            logger.info("No config file found, using defaults")
            return self.DEFAULT_SETTINGS.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a setting value."""
        self.settings[key] = value
    
    def save(self):
        """Save settings to config file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.settings, f, indent=4)
            logger.info(f"Saved settings to {self.config_path}")
        except (OSError, IOError) as e:
            logger.error(f"Error saving settings: {e}")
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple settings at once."""
        self.settings.update(updates)