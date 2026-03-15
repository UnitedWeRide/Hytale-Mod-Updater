"""
Mod ID Storage Module

This module provides functionality for storing and retrieving CurseForge Mod ID
mappings for mod files.
"""

import os
import json
import shutil
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ModIDStore:
    """Store and retrieve mod ID mappings."""
    
    def __init__(self, game_id: int, cache_dir: str):
        """
        Initialize the mod ID store.
        
        Args:
            game_id: The game ID (e.g., 70216 for Hytale)
            cache_dir: Directory to store cache files
        """
        self.game_id = game_id
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / f"{game_id}_mod_id_cache.json"
        self._cache: Dict[str, Any] = {}  # Can contain mod entries (dicts) or metadata (strings, etc.)
        self._load_cache()
    
    def _load_cache(self):
        """Load cache from file."""
        try:
            if self.cache_file.exists():
                self._load_cache_content()
            else:
                self._cache = {}
                logger.info(f"No cache file found, starting fresh")
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading cache: {e}, starting fresh")
            self._cache = {}

    def _load_cache_content(self):
        """Load and parse cache content from file."""
        with open(self.cache_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                logger.warning(f"Cache file is empty, starting fresh")
                self._cache = {}
            else:
                try:
                    self._cache = json.loads(content)
                    logger.info(f"Loaded mod ID cache from {self.cache_file}")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in cache: {e}, starting fresh")
                    self._cache = {}
    
    def _save_cache(self):
        """Save cache to file using atomic write to prevent corruption."""
        import tempfile
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            # Write to temp file first, then rename for atomic operation
            fd, temp_path = tempfile.mkstemp(dir=self.cache_dir, suffix='.tmp')
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f, indent=4)
                # Atomic rename
                os.replace(temp_path, self.cache_file)
                logger.info(f"Saved mod ID cache to {self.cache_file}")
            except (OSError, IOError):
                # Clean up temp file if something goes wrong
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError as e:
                        logger.warning(f"Failed to remove temp file {temp_path}: {e}")
                raise
        except (OSError, IOError) as e:
            logger.error(f"I/O error saving cache: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON error saving cache: {e}")
    
    def get_entry(self, fingerprint: int) -> Optional[Dict[str, Any]]:
        """
        Get mod entry by fingerprint.
        
        Args:
            fingerprint: The fingerprint to look up
            
        Returns:
            Mod entry dictionary, or None if not found
        """
        fingerprint_str = str(fingerprint)
        return self._cache.get(fingerprint_str)
    
    def add_entry(self, fingerprint: int, mod_id: int, file_id: int,
                  filename: str, game_id: int) -> bool:
        """
        Add a new mod entry.
        
        Args:
            fingerprint: The fingerprint
            mod_id: The CurseForge mod ID
            file_id: The CurseForge file ID
            filename: The filename
            game_id: The game ID
            
        Returns:
            True if successful, False otherwise
        """
        fingerprint_str = str(fingerprint)
        
        self._cache[fingerprint_str] = {
            "fingerprint": fingerprint,
            "curseforge_mod_id": mod_id,
            "curseforge_file_id": file_id,
            "filename": filename,
            "game_id": game_id,
            "last_updated": None  # Will be set by matcher
        }
        
        self._save_cache()
        logger.info(f"Added mod entry for fingerprint {fingerprint}: mod_id={mod_id}")
        return True
    
    def remove_entry(self, fingerprint: int) -> bool:
        """
        Remove a mod entry.
        
        Args:
            fingerprint: The fingerprint to remove
            
        Returns:
            True if successful, False otherwise
        """
        fingerprint_str = str(fingerprint)
        
        if fingerprint_str in self._cache:
            del self._cache[fingerprint_str]
            self._save_cache()
            logger.info(f"Removed mod entry for fingerprint {fingerprint}")
            return True
        
        logger.warning(f"Fingerprint {fingerprint} not found in cache")
        return False
    
    def clear_cache(self, preserve_folder_path: bool = False) -> bool:
        """
        Clear all mod entries from cache.
        
        Args:
            preserve_folder_path: If True, preserve the _stored_folder_path in cache
            
        Returns:
            True if successful, False otherwise
        """
        if preserve_folder_path:
            # Preserve the folder path when clearing cache
            folder_path = self._cache.get("_stored_folder_path")
            self._cache = {}
            if folder_path:
                self._cache["_stored_folder_path"] = folder_path
                logger.info(f"Preserved folder path in cache: {folder_path}")
        else:
            self._cache = {}
        self._save_cache()
        logger.info("Cleared mod ID cache")
        return True
    
    def get_mod_id_by_fingerprint(self, fingerprint: int) -> Optional[int]:
        """
        Get mod ID by fingerprint.
        
        Args:
            fingerprint: The fingerprint to look up
            
        Returns:
            Mod ID, or None if not found
        """
        entry = self.get_entry(fingerprint)
        if entry:
            return entry.get("curseforge_mod_id")
        return None
    
    def get_stored_folder_path(self) -> Optional[str]:
        """
        Get the stored folder path from cache.
        
        Returns:
            Folder path string, or None if not found
        """
        folder_path = self._cache.get("_stored_folder_path")
        if folder_path:
            return folder_path
        return None
    
    def set_stored_folder_path(self, folder_path: str):
        """
        Store the folder path in cache.
        
        Args:
            folder_path: The folder path to store
        """
        self._cache["_stored_folder_path"] = folder_path
        self._save_cache()
        logger.info(f"Stored folder path in cache: {folder_path}")
    
    def clear_stored_folder_path(self):
        """
        Clear the stored folder path from cache.
        """
        if "_stored_folder_path" in self._cache:
            del self._cache["_stored_folder_path"]
            self._save_cache()
            logger.info("Cleared stored folder path from cache")
    
    def populate_from_database(self, database_manager):
        """
        Populate the mod ID store from the database manager.
        
        Args:
            database_manager: ModDatabaseManager instance
        """
        database = database_manager.get_all_mods()
        
        # Collect all entries first, then save once at the end
        entries_to_add = {}
        
        for mod_id_str, mod_info in database.items():
            fingerprint = mod_info.get("latest_file_fingerprint")
            mod_id = mod_info.get("mod_id")
            
            if fingerprint and mod_id:
                fingerprint_str = str(fingerprint)
                
                # Use data from database directly - no API calls needed
                # The file_id can be fetched on-demand when needed
                entries_to_add[fingerprint_str] = {
                    "fingerprint": fingerprint,
                    "curseforge_mod_id": mod_id,
                    "curseforge_file_id": 0,  # Will be fetched on-demand
                    "filename": f"mod_{mod_id}",
                    "game_id": database_manager.game_id,
                    "last_updated": None
                }
        
        # Add all entries to cache
        self._cache.update(entries_to_add)
        
        # Save cache once at the end
        self._save_cache()
        
        logger.info(f"Populated mod ID store with {len(entries_to_add)} entries from database")