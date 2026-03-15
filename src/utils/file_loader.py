"""
File Loader Module (Stripped Version)

This module provides functionality for loading and parsing .zip and .jar files
for display in the Hytale Mod Updater application.
"""

import zipfile
import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional
from typing import Union
from src.services.mod_id_store import ModIDStore
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FileLoader:
    """Handles loading and parsing of .zip and .jar files."""
    
    def __init__(self, app_instance=None):
        """Initialize the file loader."""
        self.current_file: Optional[Path] = None
        self.file_contents: List[Tuple[str, int, bool, Optional[int]]] = []  # (path, size, is_dir, fingerprint)
        self.app_instance = app_instance  # For API access
    
    def load_file(self, file_path: Path) -> bool:
        """
        Load a .zip or .jar file and extract its contents.
        
        Args:
            file_path: Path to the .zip or .jar file
            
        Returns:
            True if successful, False otherwise
        """
        self.current_file = file_path
        
        try:
            fingerprint = self._compute_file_fingerprint(file_path)
        except (OSError, IOError) as e:
            logger.error(f"Error computing fingerprint for {file_path}: {e}")
            return False
        
        try:
            self.file_contents = []
            
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                for info in zip_file.infolist():
                    path = info.filename
                    size = info.file_size
                    is_dir = path.endswith('/')
                    
                    # Normalize path separators
                    path = path.replace('\\', '/')
                    
                    self.file_contents.append((path, size, is_dir, fingerprint))
            
            # Log fingerprint calculation completion (entry count is irrelevant)
            logger.info(f"Fingerprint calculated for {file_path.name}")
            return True
            
        except zipfile.BadZipFile:
            logger.error(f"Invalid zip file: {file_path}")
            return False
        except (OSError, IOError) as e:
            logger.exception(f"Error loading file {file_path}: {e}")
            return False
    
    def get_contents(self) -> List[Tuple[str, int, bool, Optional[int]]]:
        """
        Get the loaded file contents.
        
        Returns:
            List of tuples (path, size, is_dir, fingerprint)
        """
        return self.file_contents  # type: ignore
    
    def _compute_file_fingerprint(self, file_path: Path) -> Optional[int]:
        """
        Compute the CurseForge fingerprint for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            The 32-bit fingerprint, or None if computation fails
        """
        try:
            from utils.fingerprint import compute_fingerprint
            return compute_fingerprint(file_path)
        except (OSError, IOError, ImportError) as e:
            logger.exception("Failed to compute fingerprint for %s during _compute_file_fingerprint: %s", file_path, e)
            return None
    
    def match_fingerprint(self, file_path: Path, store: Optional[ModIDStore] = None) -> Optional[int]:
        """
        Match a file's fingerprint to a CurseForge Mod ID.
        
        Args:
            file_path: Path to the file
            store: Optional ModIDStore instance. If None, creates a new one.
        Returns:
            The CurseForge Mod ID, or None if no match found
        """
        try:
            from src.utils.fingerprint import compute_fingerprint
            from src.services.mod_id_matcher import ModIDMatcher
            # Get game ID from settings
            if not self.app_instance:
                logger.warning("No app instance available for settings")
                return None
            
            game_id = self.app_instance.settings.get("game_id", 70216)
            
            # Use provided store or create a new one
            if store is None:
                cache_dir = self.app_instance.path_manager.data_path
                store = ModIDStore(game_id, cache_dir)
            
            # Check cache first
            fingerprint = compute_fingerprint(file_path)
            if fingerprint is None:
                return None
            
            cached_entry = store.get_entry(fingerprint)
            if cached_entry:
                return cached_entry.get("curseforge_mod_id")
            
            # Match via API if API key is available
            if self.app_instance.api_key:
                from src.services.curseforge_api import CurseForgeAPI
                api = CurseForgeAPI(self.app_instance.api_key)
                matcher = ModIDMatcher(api, store)
                
                result = matcher.match_single_file(file_path)
                if result:
                    return result.get("curseforge_mod_id")
            
            return None
            
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Error matching fingerprint: {e}")
            return None


def _format_size(size: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def _format_fingerprint(fingerprint: Optional[int]) -> str:
    """
    Format the fingerprint as a decimal string for display.
    
    Args:
        fingerprint: The 32-bit fingerprint integer
        
    Returns:
        Formatted decimal string (e.g., "865597533") or "N/A" if None
    """
    if fingerprint is None:
        return "N/A"
    return str(fingerprint)