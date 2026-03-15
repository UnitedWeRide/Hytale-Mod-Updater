"""
Update Checker Module

This module provides functionality for checking if local mod files are outdated
by comparing their fingerprints against the centralized database.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class UpdateChecker:
    """Check if local mod files are outdated compared to database."""
    
    def __init__(self, database_manager, mod_id_store):
        """
        Initialize the update checker.
        
        Args:
            database_manager: ModDatabaseManager instance
            mod_id_store: ModIDStore instance for mapping fingerprints to mod IDs
        """
        self.database_manager = database_manager
        self.mod_id_store = mod_id_store
    
    def check_file_by_mod_id(self, mod_id: int, local_fingerprint: int, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Check if a file is outdated by comparing its fingerprint to the database entry for the mod_id.
        
        Args:
            mod_id: The CurseForge mod ID
            local_fingerprint: The local file's fingerprint
            file_path: Path to the mod file
            
        Returns:
            Update info dictionary if outdated, None if up to date or error
            {
                "file_path": Path,
                "mod_id": int,
                "local_fingerprint": int,
                "latest_fingerprint": int,
                "latest_file_id": int,
                "is_outdated": bool
            }
        """
        try:
            logger.info(f"check_file_by_mod_id: mod_id={mod_id}, local_fingerprint={local_fingerprint}, file_path={file_path}")
            
            # Get latest fingerprint from database for this mod_id
            latest_fingerprint = self.database_manager.get_latest_fingerprint(mod_id)
            if latest_fingerprint is None:
                logger.warning(f"check_file_by_mod_id: No database entry for mod {mod_id}")
                return None
            
            logger.info(f"check_file_by_mod_id: latest_fingerprint={latest_fingerprint}")
            
            # Compare fingerprints - if they don't match, there's an update
            is_outdated = local_fingerprint != latest_fingerprint
            logger.info(f"check_file_by_mod_id: is_outdated={is_outdated} (local={local_fingerprint} vs latest={latest_fingerprint})")
            
            # Get latest file ID from API (not stored in database)
            latest_file_id = None
            if is_outdated:
                try:
                    from .curseforge_api import CurseForgeAPI
                    api = CurseForgeAPI(self.database_manager.api_key)
                    mod_info = api.get_mod_details(mod_id)
                    if mod_info and "latestFiles" in mod_info:
                        latest_files = mod_info["latestFiles"]
                        if latest_files:
                            latest_file = latest_files[0]
                            latest_file_id = latest_file.get("id")
                            logger.info(f"Got latest file_id {latest_file_id} for mod {mod_id}")
                except (OSError, IOError) as e:
                    logger.error(f"Error getting latest file_id for mod {mod_id}: {e}")
            
            if is_outdated:
                # Get author from database for CFWidget fallback
                mod_info = self.database_manager.get_mod_info(mod_id)
                author = mod_info.get("author") if mod_info else None
                # Get project name from database for CFWidget fallback
                project_name = mod_info.get("name") if mod_info else None
                
                return {
                    "file_path": file_path,
                    "mod_id": mod_id,
                    "local_fingerprint": local_fingerprint,
                    "latest_fingerprint": latest_fingerprint,
                    "latest_file_id": latest_file_id,
                    "author": author,
                    "project_name": project_name,
                    "is_outdated": True
                }
            
            return None
            
        except (OSError, IOError) as e:
            logger.error(f"Error checking file with mod_id {mod_id}: {e}")
            return None
    
    def check_directory(self, directory: Path) -> List[Dict[str, Any]]:
        """
        Check all .zip/.jar files in a directory for updates.
        
        Args:
            directory: Path to the mod directory
            
        Returns:
            List of outdated mod info dictionaries
        """
        outdated_mods = []
        
        # Find all .zip and .jar files
        zip_files = list(directory.glob("*.zip")) + list(directory.glob("*.jar"))
        
        if not zip_files:
            logger.warning(f"No .zip or .jar files found in {directory}")
            return outdated_mods
        
        logger.info(f"Checking {len(zip_files)} files for updates")
        
        # Check each file
        for file_path in zip_files:
            result = self.check_file(file_path)
            if result:
                outdated_mods.append(result)
                logger.info(f"Outdated: {file_path.name} (mod_id={result['mod_id']})")
        
        return outdated_mods
    
    def check_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Check if a single file is outdated.
        
        Args:
            file_path: Path to the mod file
            
        Returns:
            Update info dictionary if outdated, None if up to date or error
            {
                "file_path": Path,
                "mod_id": int,
                "local_fingerprint": int,
                "latest_fingerprint": int,
                "latest_file_id": int,
                "is_outdated": bool
            }
        """
        try:
            from utils.fingerprint import compute_fingerprint
            
            # Compute local fingerprint
            local_fingerprint = compute_fingerprint(file_path)
            if local_fingerprint is None:
                logger.error(f"Failed to compute fingerprint for {file_path}")
                return None
            
            # Get mod ID from fingerprint (from mod_id_store which is populated from database)
            mod_id = self.mod_id_store.get_mod_id_by_fingerprint(local_fingerprint)
            if mod_id is None:
                logger.warning(f"No mod ID found for fingerprint {local_fingerprint}")
                return None
            
            # Get latest fingerprint from database
            latest_fingerprint = self.database_manager.get_latest_fingerprint(mod_id)
            if latest_fingerprint is None:
                logger.warning(f"No database entry for mod {mod_id}")
                return None
            
            # Compare fingerprints - if they don't match, there's an update
            is_outdated = local_fingerprint != latest_fingerprint
            
            # Get latest file ID from database
            mod_info = self.database_manager.get_mod_info(mod_id)
            latest_file_id = mod_info.get("latest_file_id") if mod_info else None
            
            if is_outdated:
                return {
                    "file_path": file_path,
                    "mod_id": mod_id,
                    "local_fingerprint": local_fingerprint,
                    "latest_fingerprint": latest_fingerprint,
                    "latest_file_id": latest_file_id,
                    "is_outdated": True
                }
            
            return None
            
        except (OSError, IOError) as e:
            logger.error(f"Error checking file {file_path}: {e}")
            return None
    
    def check_multiple_files(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Check multiple files for updates.
        
        Args:
            file_paths: List of paths to mod files
            
        Returns:
            List of outdated mod info dictionaries
        """
        outdated_mods = []
        
        for file_path in file_paths:
            result = self.check_file(file_path)
            if result:
                outdated_mods.append(result)
        
        return outdated_mods
    
    def check_from_treeview(self, contents: List[tuple], directory_path: Path, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Check for updates using treeview contents (which already have mod_id and fingerprint).
        
        Args:
            contents: List of tuples (item_id, mod_id, is_dir, fingerprint, [file_path]) from treeview
            directory_path: Path to the mod directory (used if file_path not in contents)
            progress_callback: Optional callback function to report progress (current, total, filename)
            
        Returns:
            List of outdated mod info dictionaries
        """
        outdated_mods = []
        total_files = len(contents)
        
        logger.info(f"check_from_treeview: contents type: {type(contents)}, length: {len(contents)}")
        if contents:
            logger.info(f"check_from_treeview: First item: {contents[0]}")
        
        for idx, item in enumerate(contents):
            # Handle both 4-tuple (item_id, mod_id, is_dir, fingerprint) and 5-tuple (item_id, mod_id, is_dir, fingerprint, file_path)
            if len(item) == 5:
                item_id, mod_id, is_dir, fingerprint, file_path = item
            else:
                item_id, mod_id, is_dir, fingerprint = item
                file_path = directory_path / str(item_id)
            
            logger.info(f"check_from_treeview: Processing item {item_id}: mod_id={mod_id}, is_dir={is_dir}, fingerprint={fingerprint}, file_path={file_path}")
            
            # Skip directory entries
            if is_dir:
                logger.info(f"check_from_treeview: Skipping directory entry {item_id}")
                continue
            
            # Skip entries without mod_id or fingerprint
            if mod_id is None or fingerprint is None:
                logger.warning(f"check_from_treeview: Skipping item {item_id}: mod_id={mod_id}, fingerprint={fingerprint}")
                continue
            
            # Check if file exists
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue
            
            # Check for update using mod_id and local fingerprint
            result = self.check_file_by_mod_id(mod_id, fingerprint, file_path)
            if result:
                outdated_mods.append(result)
                logger.info(f"Outdated: {file_path.name} (mod_id={mod_id})")
            
            # Report progress
            if progress_callback:
                progress_callback(idx + 1, total_files, file_path.name)
        
        return outdated_mods
    
    def get_update_summary(self, outdated_mods: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of update information.
        
        Args:
            outdated_mods: List of outdated mod info dictionaries
            
        Returns:
            Summary dictionary with counts and details
        """
        summary = {
            "total_files": len(outdated_mods),
            "outdated_count": len(outdated_mods),
            "up_to_date_count": 0,
            "mods": []
        }
        
        logger.info(f"get_update_summary: outdated_mods type: {type(outdated_mods)}, length: {len(outdated_mods)}")
        if outdated_mods:
            logger.info(f"get_update_summary: First mod type: {type(outdated_mods[0])}, value: {outdated_mods[0]}")
        
        for mod in outdated_mods:
            logger.info(f"get_update_summary: Processing mod type: {type(mod)}, value: {mod}")
            summary["mods"].append({
                "mod_id": mod["mod_id"],
                "file_name": mod["file_path"].name,
                "local_fingerprint": mod["local_fingerprint"],
                "latest_fingerprint": mod["latest_fingerprint"]
            })
        
        return summary