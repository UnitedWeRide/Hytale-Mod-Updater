"""
Backup Manager Module

This module provides functionality for managing backup operations for outdated mods.
"""

import logging
import json
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class BackupManager:
    """Manage backup operations for outdated mods."""
    
    def __init__(self, mod_directory: Path, backup_dir: Path):
        """
        Initialize the backup manager.
        
        Args:
            mod_directory: Directory containing mod files
            backup_dir: Directory to store backup metadata
        """
        self.mod_directory = mod_directory
        self.backup_dir = backup_dir
        self.backup_metadata_file = self.backup_dir / "backup_metadata.json"
        self._backup_metadata: Dict[str, Any] = {}
        self._load_backup_metadata()
    
    def _load_backup_metadata(self):
        """Load backup metadata from file."""
        try:
            if self.backup_metadata_file.exists():
                with open(self.backup_metadata_file, "r") as f:
                    content = f.read().strip()
                    if not content:
                        logger.warning(f"Backup metadata file is empty, starting fresh")
                        self._backup_metadata = {
                            "backups": [],
                            "last_updated": None
                        }
                    else:
                        self._backup_metadata = json.loads(content)
                        logger.info(f"Loaded backup metadata from {self.backup_metadata_file}")
            else:
                self._backup_metadata = {
                    "backups": [],
                    "last_updated": None
                }
                logger.info("No backup metadata file found, starting fresh")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in backup metadata: {e}, starting fresh")
            self._backup_metadata = {
                "backups": [],
                "last_updated": None
            }
        except (OSError, IOError) as e:
            logger.error(f"File system error loading backup metadata: {e}, starting fresh")
            self._backup_metadata = {
                "backups": [],
                "last_updated": None
            }
    
    def _save_backup_metadata(self):
        """Save backup metadata to file."""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self._backup_metadata["last_updated"] = datetime.utcnow().isoformat()
            with open(self.backup_metadata_file, "w") as f:
                json.dump(self._backup_metadata, f, indent=4)
            logger.info(f"Saved backup metadata to {self.backup_metadata_file}")
        except (OSError, IOError) as e:
            logger.error(f"Error saving backup metadata: {e}")
    
    def create_backup(self, file_path: Path) -> Optional[str]:
        """
        Create a backup of a file by moving it to the backup directory with .old suffix.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            New backup path, or None if backup fails
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found for backup: {file_path}")
                return None
            
            # Create backup directory if it doesn't exist
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup path in backup directory with .old suffix
            backup_path = self.backup_dir / (file_path.name + ".old")
            
            # If backup file already exists, delete it first (Windows rename cannot overwrite)
            if backup_path.exists():
                logger.info(f"Existing backup found, removing: {backup_path.name}")
                backup_path.unlink()
            
            # Move the file to backup directory
            file_path.rename(backup_path)
            
            logger.info(f"Created backup: {file_path.name} -> {backup_path}")
            
            # Update metadata - remove any existing entry for this file to avoid duplicates
            self._backup_metadata["backups"] = [
                b for b in self._backup_metadata["backups"]
                if b["original_name"] != file_path.name
            ]
            self._backup_metadata["backups"].append({
                "original_name": file_path.name,
                "backup_name": backup_path.name,
                "backup_path": str(backup_path),
                "timestamp": datetime.utcnow().isoformat()
            })
            self._save_backup_metadata()
            
            return str(backup_path)
            
        except (OSError, IOError, shutil.Error) as e:
            logger.error(f"File system error creating backup for {file_path}: {e}")
            return None
    
    def move_to_recycle_bin(self, file_path: Path) -> bool:
        """
        Move a file to the Recycle Bin (Windows).
        
        Args:
            file_path: Path to the file to move
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import send2trash
            send2trash.send2trash(str(file_path))
            logger.info(f"Moved to Recycle Bin: {file_path.name}")
            return True
            
        except ImportError:
            logger.error("send2trash module not installed. Install with: pip install send2trash")
            return False
        except (OSError, IOError) as e:
            logger.error(f"Error moving {file_path} to Recycle Bin: {e}")
            return False
    
    def permanently_delete(self, file_path: Path) -> bool:
        """
        Permanently delete a file.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Permanently deleted: {file_path.name}")
            return True
            
        except (OSError, IOError) as e:
            logger.error(f"Error permanently deleting {file_path}: {e}")
            return False
    
    def restore_backup(self, backup_path: str) -> Optional[Path]:
        """
        Restore a backup file by copying it from backup directory to mod directory and removing .old suffix.
        Uses copy + delete instead of rename to support cross-drive restoration.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            Restored file path, or None if restore fails
        """
        try:
            
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return None
            
            # Get the original filename (without .old suffix)
            original_filename = backup_file.stem  # e.g., "mod.zip" from "mod.zip.old"
            
            # Construct the original path in the mod directory
            original_path = self.mod_directory / original_filename
            
            # If original file already exists, delete it first
            if original_path.exists():
                logger.info(f"Existing file found during restore, removing: {original_path.name}")
                original_path.unlink()
            
            # Copy back to mod directory (supports cross-drive)
            # Validate backup_file is within backup_dir to prevent path traversal
            backup_file_path = Path(backup_file).resolve()
            if not backup_file_path.is_relative_to(self.backup_dir):
                logger.error(f"Invalid backup path: {backup_file}")
                return None
            shutil.copy2(str(backup_file_path), str(original_path))
            
            # Delete the backup file after successful copy
            backup_file.unlink()
            
            logger.info(f"Restored backup: {backup_path} -> {original_path}")
            return original_path
            
        except (OSError, IOError, shutil.Error) as e:
            logger.error(f"File system error restoring backup {backup_path}: {e}")
            return None
    
    def get_backup_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all backup files.
        
        Returns:
            List of backup file information dictionaries
        """
        backups = []
        
        try:
            # Find all .old files in backup directory
            for old_file in self.backup_dir.glob("*.old"):
                original_name = old_file.stem  # Remove .old suffix
                # Try to find the original extension (before .old)
                # e.g., "mod.zip.old" -> "mod.zip"
                potential_original = old_file.parent / original_name
                
                backups.append({
                    "backup_path": str(old_file),
                    "original_name": original_name,
                    "original_path": str(potential_original),
                    "backup_size": old_file.stat().st_size,
                    "backup_date": datetime.fromtimestamp(old_file.stat().st_mtime).isoformat()
                })
            
            logger.info(f"Found {len(backups)} backup files")
            
        except (OSError, IOError) as e:
            logger.error(f"Error listing backups: {e}")
        
        return backups
    
    def delete_backup(self, backup_path: str) -> bool:
        """
        Delete a specific backup file.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_file = Path(backup_path)
            
            if backup_file.exists():
                backup_file.unlink()
                logger.info(f"Deleted backup: {backup_path}")
                return True
            
            logger.warning(f"Backup file not found: {backup_path}")
            return False
            
        except (OSError, IOError) as e:
            logger.error(f"Error deleting backup {backup_path}: {e}")
            return False