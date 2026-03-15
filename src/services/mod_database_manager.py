"""
Mod Database Manager Module

This module provides functionality for managing a centralized database of all Hytale mods
from CurseForge, storing mod IDs and their latest file fingerprints for update detection.
"""

import os
import json
import logging
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class ModDatabaseManager:
    """Manage the centralized database of Hytale mods from CurseForge.
    
    This class provides thread-safe database operations using a threading.Lock
    to prevent race conditions during concurrent writes. The database construction
    uses ThreadPoolExecutor for parallel fetching and processing of mods.
    """
    
    def __init__(self, game_id: int, cache_dir: str, api_key: str, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize the mod database manager.
        
        Args:
            game_id: The game ID (e.g., 70216 for Hytale)
            cache_dir: Directory to store database files
            api_key: CurseForge API key for fetching mod data
            settings: Optional settings dictionary for configuration
        """
        self.game_id = game_id
        self.cache_dir = Path(cache_dir)
        self.api_key = api_key
        self.settings = settings or {}
        self.database_file = self.cache_dir / f"{game_id}_mod_database.json"
        self.metadata_file = self.cache_dir / f"{game_id}_database_metadata.json"
        self._database: Dict[str, Dict[str, Any]] = {}
        self._metadata: Dict[str, Any] = {}
        self._db_lock = threading.Lock()  # Thread lock for database operations
        self._load_database()
        self._load_metadata()
    
    def _load_database(self):
        """Load database from file."""
        try:
            if self.database_file.exists():
                with open(self.database_file, "r", encoding="utf-8") as f:
                    try:
                        self._database = json.load(f)
                        logger.info(f"Loaded mod database from {self.database_file}")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error in database: {e}, starting fresh")
                        self._database = {}
            else:
                self._database = {}
                logger.info(f"No database file found, starting fresh")
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading database: {e}, starting fresh")
            self._database = {}
    
    def _save_database(self):
        """Save database to file using atomic write to prevent corruption."""
        import tempfile
        with self._db_lock:  # Thread-safe access to database
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                # Write to temp file first, then rename for atomic operation
                fd, temp_path = tempfile.mkstemp(dir=self.cache_dir, suffix='.tmp')
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(self._database, f, indent=4)
                    # Atomic rename
                    os.replace(temp_path, self.database_file)
                    logger.info(f"Saved mod database to {self.database_file}")
                except (OSError, IOError) as e:
                    # Clean up temp file if something goes wrong
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise
            except (OSError, IOError) as e:
                logger.error(f"Error saving database: {e}")
    
    def _load_metadata(self):
        """Load database metadata from file."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    try:
                        self._metadata = json.load(f)
                        logger.info(f"Loaded database metadata from {self.metadata_file}")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error in metadata: {e}, starting fresh")
                        self._metadata = {
                            "game_id": self.game_id,
                            "database_version": "1.0",
                            "last_sync": None,
                            "mod_count": 0,
                            "total_mods_on_curseforge": 0
                        }
            else:
                self._metadata = {
                    "game_id": self.game_id,
                    "database_version": "1.0",
                    "last_sync": None,
                    "mod_count": 0,
                    "total_mods_on_curseforge": 0
                }
                logger.info(f"No metadata file found, starting fresh")
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading metadata: {e}, starting fresh")
            self._metadata = {
                "game_id": self.game_id,
                "database_version": "1.0",
                "last_sync": None,
                "mod_count": 0,
                "total_mods_on_curseforge": 0
            }
    
    def _save_metadata(self):
        """Save database metadata to file using atomic write to prevent corruption."""
        import tempfile
        with self._db_lock:  # Thread-safe access to metadata
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                # Write to temp file first, then rename for atomic operation
                fd, temp_path = tempfile.mkstemp(dir=self.cache_dir, suffix='.tmp')
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(self._metadata, f, indent=4)
                    # Atomic rename
                    os.replace(temp_path, self.metadata_file)
                    logger.info(f"Saved database metadata to {self.metadata_file}")
                except (OSError, IOError) as e:
                    # Clean up temp file if something goes wrong
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise
            except (OSError, IOError) as e:
                logger.error(f"Error saving metadata: {e}")
    
    def get_mod_info(self, mod_id: int) -> Optional[Dict[str, Any]]:
        """
        Get mod information by mod ID.
        
        Args:
            mod_id: The CurseForge mod ID
            
        Returns:
            Mod info dictionary, or None if not found
        """
        mod_id_str = str(mod_id)
        return self._database.get(mod_id_str)
    
    def get_latest_fingerprint(self, mod_id: int) -> Optional[int]:
        """
        Get the latest fingerprint for a mod.
        
        Args:
            mod_id: The CurseForge mod ID
            
        Returns:
            Latest fingerprint, or None if not found
        """
        mod_info = self.get_mod_info(mod_id)
        if mod_info:
            return mod_info.get("latest_file_fingerprint")
        return None
    
    def add_or_update_mod(self, mod_id: int, fingerprint: int, latest_file_id: Optional[int] = None, author: Optional[str] = None) -> bool:
        """
        Add or update a mod entry in the database.
        
        Args:
            mod_id: The CurseForge mod ID
            fingerprint: The latest file fingerprint
            latest_file_id: The latest file ID (optional)
            author: The mod author name (optional)
            
        Returns:
            True if successful, False otherwise
        """
        mod_id_str = str(mod_id)
        
        entry = {
            "mod_id": mod_id,
            "latest_file_fingerprint": fingerprint,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        if latest_file_id is not None:
            entry["latest_file_id"] = latest_file_id
        
        # Include author if provided
        if author is not None:
            entry["author"] = author
        
        self._database[mod_id_str] = entry
        
        self._save_database()
        self._metadata["mod_count"] = len(self._database)
        self._save_metadata()
        
        logger.info(f"Added/updated mod {mod_id} with fingerprint {fingerprint}, file_id {latest_file_id}")
        return True
    
    def bulk_add_or_update_mods(self, mods_data: List[Dict[str, Any]], async_save: bool = True) -> int:
        """
        Add or update multiple mods at once (without saving after each).
        
        Args:
            mods_data: List of mod data dictionaries with keys:
                - mod_id: int
                - fingerprint: int
                - latest_file_id: int (optional)
            async_save: If True, save database asynchronously to prevent blocking
            
        Returns:
            Number of mods added/updated
        """
        success_count = 0
        
        for mod_data in mods_data:
            # Skip entries with action='skip' (incremental update optimization)
            if mod_data.get("action") == "skip":
                continue
            
            mod_id = mod_data.get("mod_id")
            fingerprint = mod_data.get("fingerprint")
            latest_file_id = mod_data.get("latest_file_id")
            
            if not all([mod_id, fingerprint]):
                continue
            
            mod_id_str = str(mod_id)
            
            entry = {
                "mod_id": mod_id,
                "latest_file_fingerprint": fingerprint,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            if latest_file_id is not None:
                entry["latest_file_id"] = latest_file_id
            
            # Include author if provided
            author = mod_data.get("author")
            if author is not None:
                entry["author"] = author
            
            self._database[mod_id_str] = entry
            success_count += 1
        
        # Update metadata
        self._metadata["mod_count"] = len(self._database)
        
        # Save database asynchronously to prevent blocking
        if async_save:
            import threading
            save_thread = threading.Thread(
                target=self._save_database_async,
                daemon=True
            )
            save_thread.start()
            logger.info(f"Bulk added/updated {success_count} mods (async save)")
        else:
            self._save_database()
            self._save_metadata()
            logger.info(f"Bulk added/updated {success_count} mods (sync save)")
        
        return success_count
    
    def _save_database_async(self):
        """Save database and metadata asynchronously."""
        try:
            self._save_database()
            self._save_metadata()
            logger.info("Async database save completed")
        except (OSError, IOError) as e:
            logger.error(f"Error in async database save: {e}")
    
    def _save_metadata_async(self):
        """Save metadata asynchronously."""
        try:
            self._save_metadata()
            logger.info("Async metadata save completed")
        except (OSError, IOError) as e:
            logger.error(f"Error in async metadata save: {e}")
    
    def remove_mod(self, mod_id: int) -> bool:
        """
        Remove a mod entry from the database.
        
        Args:
            mod_id: The CurseForge mod ID
            
        Returns:
            True if successful, False otherwise
        """
        mod_id_str = str(mod_id)
        
        if mod_id_str in self._database:
            del self._database[mod_id_str]
            self._save_database()
            self._metadata["mod_count"] = len(self._database)
            self._save_metadata()
            logger.info(f"Removed mod {mod_id} from database")
            return True
        
        logger.warning(f"Mod {mod_id} not found in database")
        return False
    
    def clear_database(self) -> bool:
        """
        Clear all mod entries from the database.
        
        Returns:
            True if successful, False otherwise
        """
        self._database = {}
        self._metadata["mod_count"] = 0
        self._metadata["last_sync"] = None
        self._metadata["total_mods_on_curseforge"] = 0
        self._save_database()
        self._save_metadata()
        logger.info("Cleared mod database")
        return True
    
    def get_all_mod_ids(self) -> List[int]:
        """
        Get all mod IDs in the database.
        
        Returns:
            List of mod IDs
        """
        return [int(mod_id_str) for mod_id_str in self._database.keys()]
    
    def get_all_mods(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all mod entries.
        
        Returns:
            Dictionary of all mod entries
        """
        return self._database.copy()
    
    def get_mod_count(self) -> int:
        """
        Get the total number of mods in the database.
        
        Returns:
            Number of mods
        """
        return self._metadata.get("mod_count", 0)
    
    def get_total_mods_on_curseforge(self) -> int:
        """
        Get the total number of mods on CurseForge.
        
        Returns:
            Total mod count
        """
        return self._metadata.get("total_mods_on_curseforge", 0)
    
    def get_last_sync(self) -> Optional[str]:
        """
        Get the last sync timestamp.
        
        Returns:
            ISO format timestamp, or None if never synced
        """
        return self._metadata.get("last_sync")
    
    def set_last_sync(self, timestamp: str):
        """
        Set the last sync timestamp.
        
        Args:
            timestamp: ISO format timestamp
        """
        self._metadata["last_sync"] = timestamp
        self._save_metadata()
        logger.info(f"Set last sync to {timestamp}")
    
    def is_database_fresh(self, max_age_hours: int = 24) -> bool:
        """
        Check if the database is fresh (not older than max_age_hours).
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            True if database is fresh, False otherwise
        """
        last_sync = self.get_last_sync()
        if not last_sync:
            return False
        
        try:
            last_sync_dt = datetime.fromisoformat(last_sync)
            now = datetime.utcnow()
            age_hours = (now - last_sync_dt).total_seconds() / 3600
            return age_hours < max_age_hours
        except (OSError, IOError, ValueError) as e:
            logger.error(f"Error checking database freshness: {e}")
            return False
    
    def initialize_database(self, api, progress_callback=None) -> bool:
        """
        Initialize the database by fetching all Hytale mods from CurseForge using pagination.
        Uses multithreading to fetch pages and process mods in parallel for improved performance.
        Implements incremental updates to skip unchanged mods for faster subsequent builds.
        
        Thread Safety:
        - Uses ThreadPoolExecutor for parallel fetching and processing
        - Thread-safe database writes via _db_lock
        - Progress callback is called from worker threads (UI updates should be thread-safe)
        
        Args:
            api: CurseForgeAPI instance
            progress_callback: Optional callback function to report progress (stage, value, max)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Initializing database for game ID {self.game_id}")
        
        # Fetch all mods using pagination
        mods = self._fetch_all_mods_paginated(api, progress_callback)
        if mods is None:
            logger.error("Failed to fetch mods from CurseForge")
            return False
        
        if not mods:
            logger.warning("No mods found for this game")
            return True
        
        logger.info(f"Fetched {len(mods)} mods from CurseForge")
        
        # Use multithreading to process mods in parallel with incremental update detection
        # Use smaller thread count to prevent UI blocking and API overload
        mods_data = []
        skipped_count = 0
        updated_count = 0
        total_mods = len(mods)
        
        # Determine optimal thread count based on CPU cores
        # Use fewer threads to prevent UI blocking with large mod counts
        import concurrent.futures
        cpu_count = os.cpu_count() or 1
        
        # Check if full-speed mode is enabled
        full_speed_mode = self.settings.get("full_speed_db_pagination", False)
        
        if full_speed_mode:
            # Use all available CPU threads for maximum processing speed
            thread_count = cpu_count
            logger.info(f"Full-speed mode: using all {thread_count} CPU threads for processing")
        else:
            # Cap at 8 threads for processing to prevent UI blocking with ~4000 mods
            thread_count = min(cpu_count, 8)
            logger.info(f"Using {thread_count} threads for processing (rate-limited mode)")
        
        # Process mods in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit all mod processing tasks
            future_to_mod = {}
            # Use a shared list for tracking last progress update (for throttling)
            last_progress = [0]
            for idx, mod in enumerate(mods):
                future = executor.submit(self._process_mod_incremental, mod, idx, total_mods, progress_callback, last_progress)
                future_to_mod[future] = mod
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_mod):
                result = future.result()
                if result is not None:
                    if result.get("action") == "skip":
                        skipped_count += 1
                    else:
                        mods_data.append(result)
                        updated_count += 1
        
        # Bulk add all mods at once (async save to prevent blocking)
        if mods_data:
            self.bulk_add_or_update_mods(mods_data, async_save=True)
        
        # Update metadata with total count from pagination (async)
        self._metadata["mod_count"] = len(self._database)
        self._metadata["last_sync"] = datetime.utcnow().isoformat()
        import threading
        save_thread = threading.Thread(
            target=self._save_metadata_async,
            daemon=True
        )
        save_thread.start()
        
        logger.info(f"Database initialized: {updated_count} updated, {skipped_count} unchanged, {thread_count} threads")
        return True
    
    def _process_mod(self, mod, idx: int, total_mods: int, progress_callback=None, last_progress=None) -> Optional[Dict[str, Any]]:
        """
        Process a single mod entry for database insertion.
        
        Args:
            mod: Mod dictionary from CurseForge API
            idx: Current index for progress reporting
            total_mods: Total number of mods to process
            progress_callback: Optional callback function
            last_progress: List containing last progress update index (for throttling)
            
        Returns:
            Mod data dictionary or None if processing failed
        """
        mod_id = mod.get("id")
        if not mod_id:
            return None
        
        # Get latest file info from mod object
        latest_files = mod.get("latestFiles", [])
        if not latest_files:
            return None
        
        latest_file = latest_files[0]
        file_id = latest_file.get("id")
        fingerprint = latest_file.get("fileFingerprint")
        file_date = latest_file.get("fileDate")
        
        if not fingerprint:
            return None
        
        mod_data = {
            "mod_id": mod_id,
            "fingerprint": fingerprint,
            "latest_file_id": file_id,
            "author": mod.get("authors", [{}])[0].get("name")
        }
        
        # Report processing progress (thread-safe, throttled to avoid UI spam)
        if progress_callback and last_progress is not None:
            # Only update progress every 100 mods to avoid UI spam
            if (idx + 1) % 100 == 0 or (idx + 1) == total_mods:
                progress_callback("processing", idx + 1, total_mods)
                last_progress[0] = idx + 1
        
        return mod_data
    
    def _process_mod_incremental(self, mod, idx: int, total_mods: int, progress_callback=None, last_progress=None) -> Optional[Dict[str, Any]]:
        """
        Process a single mod entry for database insertion with incremental update detection.
        Compares existing mod fingerprint with new one - skips write if unchanged.
        
        Args:
            mod: Mod dictionary from CurseForge API
            idx: Current index for progress reporting
            total_mods: Total number of mods to process
            progress_callback: Optional callback function
            last_progress: List containing last progress update index (for throttling)
            
        Returns:
            Mod data dictionary with action='update' or 'skip', or None if processing failed
        """
        mod_id = mod.get("id")
        if not mod_id:
            return None
        
        # Get latest file info from mod object
        latest_files = mod.get("latestFiles", [])
        if not latest_files:
            return None
        
        latest_file = latest_files[0]
        file_id = latest_file.get("id")
        fingerprint = latest_file.get("fileFingerprint")
        file_date = latest_file.get("fileDate")
        
        if not fingerprint:
            return None
        
        # Check if mod exists in database with same fingerprint (incremental update)
        existing_mod = self._database.get(str(mod_id))
        if existing_mod and existing_mod.get("latest_file_fingerprint") == fingerprint:
            # Mod hasn't changed - skip write
            logger.debug(f"Mod {mod_id} unchanged, skipping write")
            return {"action": "skip", "mod_id": mod_id, "fingerprint": fingerprint}
        
        # Mod has changed or is new - prepare for update
        mod_data = {
            "mod_id": mod_id,
            "fingerprint": fingerprint,
            "latest_file_id": file_id,
            "author": mod.get("authors", [{}])[0].get("name"),
            "action": "update"
        }
        
        # Report processing progress (thread-safe, throttled to avoid UI spam)
        if progress_callback and last_progress is not None:
            # Only update progress every 100 mods to avoid UI spam
            if (idx + 1) % 100 == 0 or (idx + 1) == total_mods:
                progress_callback("processing", idx + 1, total_mods)
                last_progress[0] = idx + 1
        
        return mod_data
    
    def _fetch_all_mods_paginated(self, api, progress_callback=None) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch all mods for the game from CurseForge using pagination.
        Uses multithreading to fetch pages in parallel for improved performance.
        
        Args:
            api: CurseForgeAPI instance
            progress_callback: Optional callback function to report progress (stage, value, max)
            
        Returns:
            List of mod dictionaries, or None if request fails
        """
        # First, get the total count by fetching the first page
        first_response = api.search_mods_by_game(
            game_id=self.game_id,
            index=0,
            page_size=50
        )
        
        if not first_response:
            logger.error("Failed to fetch first page to get total count")
            return None
        
        pagination = first_response.get("pagination", {})
        total_count = pagination.get("totalCount", 0)
        
        if total_count == 0:
            logger.info("No mods found for this game")
            return []
        
        # Calculate total pages
        page_size = 50
        total_pages = (total_count // page_size) + 1 if total_count > 0 else 1
        
        logger.info(f"Total mods: {total_count}, Total pages: {total_pages}")
        
        # Determine optimal thread count based on CPU cores
        # Use fewer threads for fetching to avoid API rate limiting bottleneck
        # The API has a 0.5s rate limit, so more threads just cause more waiting
        import concurrent.futures
        cpu_count = os.cpu_count() or 1
        
        # Check if full-speed mode is enabled
        full_speed_mode = self.settings.get("full_speed_db_pagination", False)
        
        if full_speed_mode:
            # Use all available CPU threads for maximum speed
            thread_count = cpu_count
            logger.info(f"Full-speed database pagination enabled: using all {thread_count} CPU threads")
        else:
            # Use 4-6 threads for fetching - enough for parallelism but not overwhelming
            thread_count = min(max(cpu_count, 4), 6)  # Cap between 4-6 threads for fetching
            logger.info(f"Using {thread_count} threads for fetching (rate-limited mode)")
        
        # Create a list of all page indices to fetch
        page_indices = list(range(0, total_count, page_size))
        
        # Fetch pages in parallel using ThreadPoolExecutor
        all_mods = []
        fetch_lock = threading.Lock()  # Lock for thread-safe list extension
        last_progress_page = 0  # Track last progress update for throttling
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit all page fetching tasks
            future_to_index = {}
            for index in page_indices:
                future = executor.submit(self._fetch_page, api, index, page_size)
                future_to_index[future] = index
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                mods_response = future.result()
                
                if mods_response:
                    page_data = mods_response.get("data", [])
                    with fetch_lock:
                        all_mods.extend(page_data)
                    
                    logger.info(f"Fetched {len(page_data)} mods (index={index}, total so far={len(all_mods)})")
                    
                    # Report fetching progress (thread-safe, throttled to avoid UI spam)
                    if progress_callback:
                        page_num = (index // page_size) + 1
                        # Only update progress every 5 pages to avoid UI spam
                        if page_num - last_progress_page >= 5 or page_num == total_pages:
                            progress_callback("fetching", page_num, total_pages)
                            last_progress_page = page_num
                else:
                    logger.error(f"Failed to fetch mods at index {index}")
        
        # Update metadata with total count
        self._metadata["total_mods_on_curseforge"] = total_count
        
        logger.info(f"Finished fetching all {len(all_mods)} mods")
        return all_mods
    
    def _fetch_page(self, api, index: int, page_size: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single page of mods from CurseForge API.
        
        Args:
            api: CurseForgeAPI instance
            index: Zero-based index of first item to include
            page_size: Number of items to include
            
        Returns:
            Response with data and pagination info, or None if request fails
        """
        return api.search_mods_by_game(
            game_id=self.game_id,
            index=index,
            page_size=page_size
        )