"""
Mod ID Matcher Module

This module provides functionality for matching mod fingerprints to CurseForge Mod IDs.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.services.curseforge_api import CurseForgeAPI
from src.services.mod_id_store import ModIDStore

logger = logging.getLogger(__name__)


class ModIDMatcher:
    """Match mod fingerprints to CurseForge Mod IDs."""
    
    def __init__(self, api: CurseForgeAPI, store: ModIDStore):
        """
        Initialize the mod ID matcher.
        
        Args:
            api: CurseForgeAPI instance
            store: ModIDStore instance
        """
        self.api = api
        self.store = store
    
    def match_single_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Match a single file to a CurseForge mod.
        
        Args:
            file_path: Path to the mod file
            
        Returns:
            Mod entry dictionary, or None if no match found
        """
        from ..utils.fingerprint import compute_fingerprint
        
        # Compute fingerprint
        fingerprint = compute_fingerprint(file_path)
        if fingerprint is None:
            logger.error(f"Failed to compute fingerprint for {file_path}")
            return None
        
        # Check cache first
        cached_entry = self.store.get_entry(fingerprint)
        if cached_entry:
            logger.info(f"Cache hit for fingerprint {fingerprint}")
            return cached_entry
        
        # Try exact match
        exact_match = self._try_exact_match(fingerprint)
        if exact_match:
            return exact_match
        
        # Try fuzzy match
        fuzzy_match = self._try_fuzzy_match(file_path, fingerprint)
        if fuzzy_match:
            return fuzzy_match
        
        logger.warning(f"No match found for fingerprint {fingerprint}")
        return None
    
    def _try_exact_match(self, fingerprint: int) -> Optional[Dict[str, Any]]:
        """
        Try exact fingerprint match via API.
        
        Args:
            fingerprint: The fingerprint to match
            
        Returns:
            Mod entry dictionary, or None if no match
        """
        game_id = self.store.game_id
        
        result = self.api.match_fingerprints(game_id, [fingerprint])
        if not result:
            return None
        
        exact_matches = result.get("exactMatches", [])
        if not exact_matches:
            return None
        
        # Get the first match
        match = exact_matches[0]
        file_info = match.get("file", {})
        
        mod_entry = {
            "fingerprint": fingerprint,
            "curseforge_mod_id": file_info.get("modId"),
            "curseforge_file_id": file_info.get("id"),
            "filename": file_info.get("fileName", ""),
            "game_id": game_id,
            "last_updated": None
        }
        
        # Store the entry
        self.store.add_entry(
            fingerprint=fingerprint,
            mod_id=mod_entry["curseforge_mod_id"],
            file_id=mod_entry["curseforge_file_id"],
            filename=mod_entry["filename"],
            game_id=game_id
        )
        
        logger.info(f"Exact match found: mod_id={mod_entry['curseforge_mod_id']}")
        return mod_entry
    
    def _try_fuzzy_match(self, file_path: Path, fingerprint: int) -> Optional[Dict[str, Any]]:
        """
        Try fuzzy fingerprint match via API.
        
        Args:
            file_path: Path to the mod file
            fingerprint: The fingerprint to match
            
        Returns:
            Mod entry dictionary, or None if no match
        """
        game_id = self.store.game_id
        foldername = file_path.name
        
        fingerprint_query = {
            "foldername": foldername,
            "fingerprints": [fingerprint]
        }
        
        result = self.api.fuzzy_match_fingerprints(game_id, [fingerprint_query])
        if not result:
            return None
        
        fuzzy_matches = result.get("fuzzyMatches", [])
        if not fuzzy_matches:
            return None
        
        # Get the first match
        match = fuzzy_matches[0]
        file_info = match.get("file", {})
        
        mod_entry = {
            "fingerprint": fingerprint,
            "curseforge_mod_id": file_info.get("modId"),
            "curseforge_file_id": file_info.get("id"),
            "filename": file_info.get("fileName", ""),
            "game_id": game_id,
            "last_updated": None
        }
        
        # Store the entry
        self.store.add_entry(
            fingerprint=fingerprint,
            mod_id=mod_entry["curseforge_mod_id"],
            file_id=mod_entry["curseforge_file_id"],
            filename=mod_entry["filename"],
            game_id=game_id
        )
        
        logger.info(f"Fuzzy match found: mod_id={mod_entry['curseforge_mod_id']}")
        return mod_entry
    
    # batch_match is unused - kept for potential future use