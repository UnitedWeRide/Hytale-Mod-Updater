"""
Core Application (Stripped Version)

This module provides the main application class for the Hytale Mod Updater.
It orchestrates minimal UI components: GUI, Settings, API Key, Keychain.
"""

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Optional, Any
import logging
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile
import shutil

logger = logging.getLogger(__name__)


class HytaleModUpdater:
    """Main application class for the Hytale Mod Updater (Stripped)."""
    
    def __init__(self, root: tk.Tk, settings_manager=None, path_manager=None, theme_manager=None, thread_manager=None):
        """
        Initialize the application.
        
        Args:
            root: Tk root window
            settings_manager: SettingsManager instance
            path_manager: PathManager instance (required)
            theme_manager: ThemeManager instance
            thread_manager: ThreadManager instance
        """
        # Validate required parameters
        if path_manager is None:
            raise ValueError("path_manager is required")
        
        # Type annotations for instance variables
        self.root: tk.Tk = root
        self.settings_manager = settings_manager
        self.path_manager = path_manager  # type: ignore
        self.thread_manager = thread_manager
        self.root = root
        self.root.title("Hytale Mod Updater")
        
        # Set minimum window size and make it resizable
        self.root.minsize(600, 400)
        self.root.geometry("800x500")
        self.root.resizable(True, True)
        
        # Configure grid weights for better resizing behavior
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Inject dependencies
        self.settings_manager = settings_manager
        self.path_manager = path_manager
        self.thread_manager = thread_manager
        
        # Create theme manager if not provided
        if theme_manager is not None:
            self.theme_manager = theme_manager
        else:
            from .theme_manager import ThemeManager
            self.theme_manager = ThemeManager(self.path_manager.resources_path)
        
        # Initialize instance variables
        self.api_key: Optional[str] = None  # Initialize API key
        self.settings: Dict[str, Any] = {}  # Initialize settings
        self.last_loaded_folder: Optional[Path] = None  # Track last loaded folder for update checking
        self._downloads_in_progress = False  # Track if downloads are in progress (for window always-on-top)
        self._automated_update_check_in_progress = False  # Track if automated update check is in progress
        
        # UI components - initialized in _initialize_ui_components and create_ui
        self.app_window: Any  # type: ignore
        self.settings_handlers: Any  # type: ignore
        self.mod_id_store: Any  # type: ignore
        self.mod_database_manager: Any  # type: ignore
        self.theme_manager: Any  # type: ignore
        
        # Load settings from settings manager
        self._load_settings_from_manager()
        
        # Apply theme based on loaded settings
        self.apply_theme()
        
        # Initialize UI components
        self._initialize_ui_components()
        
        # Create the main UI
        self.create_ui()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Check for API key on startup (in background)
        self.root.after(100, self._check_api_key_background)
    
    def _check_api_key_background(self):
        """Check for API key and initialize database in background thread."""
        threading.Thread(target=self._check_api_key_thread, daemon=True).start()
    
    def _check_api_key_thread(self):
        """Thread method to check API key and initialize database."""
        from ..services.keyring_manager import KeyringManager
        
        api_key = KeyringManager.get_api_key()
        if api_key:
            self.api_key = api_key
            logger.info("API key loaded from keyring")
            # Mark first run as complete since API key exists
            self._mark_first_run_complete()
        else:
            logger.info("No API key found in keyring")
            # Show first-run dialog if not already completed
            self._show_first_run_dialog()
        
        # Initialize mod ID store and database manager
        self._init_mod_id_store_thread()
        
        # Restore mods from cache if enabled (after ensuring mod_id_store is initialized)
        self.root.after(100, self._schedule_restore_mods_from_cache)
    
    def _mark_first_run_complete(self):
        """Mark first run as complete by updating settings."""
        if self.settings_manager:
            self.settings_manager.set("first_run", False)
            self.settings_manager.save()
            logger.info("First run marked as complete")
    
    def _show_first_run_dialog(self):
        """Show first-run dialog to get API key from user."""
        def show_dialog():
            try:
                from ..ui.dialogs import APIKeyDialog
                
                # Check if first_run flag exists and is True
                first_run = self.settings.get("first_run", True)
                
                if first_run:
                    logger.info("Showing first-run API key dialog")
                    dialog = APIKeyDialog(self.root, is_first_run=True)
                    api_key = dialog.show()
                    
                    if api_key:
                        # API key was validated and saved
                        self.api_key = api_key
                        logger.info("API key received from first-run dialog")
                        # Mark first run as complete
                        self._mark_first_run_complete()
                    else:
                        logger.info("No API key provided in first-run dialog")
                else:
                    logger.info("First run already completed, skipping dialog")
            except (OSError, IOError, ImportError) as e:
                logger.error(f"Error showing first-run dialog: {e}")
        
        # Run dialog on main thread
        self.root.after(0, show_dialog)
    
    def _init_mod_id_store_thread(self):
        """Thread method to initialize mod ID store and database manager."""
        try:
            from services.mod_id_store import ModIDStore
            
            game_id = self.settings.get("game_id", 70216)
            cache_dir = self.path_manager.data_path
            
            self.mod_id_store = ModIDStore(game_id, cache_dir)
            logger.info(f"Initialized mod ID store for game ID {game_id}")
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Failed to initialize mod ID store: {e}")
            self.mod_id_store = None
        
        # Initialize mod database manager in background
        self._init_mod_database_manager_thread()
    
    def _init_mod_database_manager_thread(self):
        """Thread method to initialize mod database manager."""
        try:
            from services.mod_database_manager import ModDatabaseManager
            
            game_id = self.settings.get("game_id", 70216)
            cache_dir = self.path_manager.data_path
            
            if self.api_key:
                self.mod_database_manager = ModDatabaseManager(game_id, cache_dir, self.api_key, self.settings)
                logger.info(f"Initialized mod database manager for game ID {game_id}")
                
                # Populate mod ID store from database in background
                self._populate_mod_id_store_from_database_thread()
            else:
                self.mod_database_manager = None
                logger.warning("No API key available, database manager not initialized")
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Failed to initialize mod database manager: {e}")
            self.mod_database_manager = None
    
    def _populate_mod_id_store_from_database_thread(self):
        """Thread method to populate mod ID store from database and update mod count display."""
        try:
            if self.mod_id_store and self.mod_database_manager:
                self.mod_id_store.populate_from_database(self.mod_database_manager)
                logger.info("Populated mod ID store from database")
                
                # Update mod count display with database count on app launch
                database_count = self.mod_database_manager.get_mod_count()
                self.app_window.update_mod_count(0, database_count)
                logger.info(f"Updated mod count display: loaded=0, database={database_count}")
                
                # Check if database is up to date by comparing with CurseForge API
                self._check_database_up_to_date()
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Failed to populate mod ID store from database: {e}")
    
    def _check_database_up_to_date(self):
        """Check if the database is up to date by comparing with CurseForge API."""
        if not self.api_key:
            return
        
        # Type narrowing: api_key is guaranteed to be str here
        api_key = self.api_key
        
        def check_thread():
            try:
                from services.curseforge_api import CurseForgeAPI
                api = CurseForgeAPI(api_key, rate_limit_enabled=True)
                
                # Get total mods from CurseForge API
                first_response = api.search_mods_by_game(
                    game_id=self.settings.get("game_id", 70216),
                    index=0,
                    page_size=1
                )
                
                if first_response:
                    pagination = first_response.get("pagination", {})
                    total_mods = pagination.get("totalCount", 0)
                    
                    # Get current database count
                    if self.mod_database_manager:
                        database_count = self.mod_database_manager.get_mod_count()
                        
                        # Update mod count display with both counts
                        self.app_window.update_mod_count(0, database_count, total_mods)
                        
                        # Log whether database is up to date
                        if database_count == total_mods:
                            logger.info(f"Database is up to date: {database_count} mods (CurseForge: {total_mods})")
                        elif database_count > total_mods:
                            logger.warning(f"Database has more mods than CurseForge (some have possibly been removed from curseforge or hidden.): {database_count} mods (CurseForge: {total_mods})")
                        else:
                            logger.warning(f"Database is out of date: {database_count} mods (CurseForge: {total_mods})")
            except (OSError, IOError, ImportError) as e:
                logger.error(f"Failed to check database up to date: {e}")
        
        # Run in background thread
        threading.Thread(target=check_thread, daemon=True).start()
    
    def _initialize_ui_components(self):
        """Initialize UI component handlers."""
        from ui.app_window import AppWindow
        from ui.settings_handlers import SettingsHandlers
        
        self.app_window = AppWindow(self.root, self)
        self.settings_handlers = SettingsHandlers(self)
    
    def _on_close(self):
        """Handle window close event."""
        logger.info("Window close requested")
        
        # Clear automated update check in progress flag on close
        self._automated_update_check_in_progress = False
        logger.info("Automated update check in progress flag cleared on close")
        
        # Clear cache on close to prevent stale data from persisting
        # Preserve folder path for restore on launch
        if self.mod_id_store:
            self.mod_id_store.clear_cache(preserve_folder_path=True)
            logger.info("Cleared mod ID cache on app close (preserved folder path)")
        
        # Check if terminal should be closed on exit
        close_terminal = self.settings.get("close_terminal_on_exit", True)
        if close_terminal:
            logger.info("Closing terminal window...")
            os._exit(0)
        
        self.root.destroy()
    
    def clear_mod_cache(self):
        """Public method to clear the mod ID cache."""
        if self.mod_id_store:
            self.mod_id_store.clear_cache()
            logger.info("Cleared mod ID cache via clear button")
    
    def _load_settings_from_manager(self):
        """Load settings from the settings manager on startup."""
        if self.settings_manager:
            self.settings = {
                "theme": self.settings_manager.get("theme", "forest"),
                "theme_mode": self.settings_manager.get("theme_mode", "auto"),
                "mod_directory": self.settings_manager.get("mod_directory", ""),
                "debug_mode": self.settings_manager.get("debug_mode", False),
                "backup_enabled": self.settings_manager.get("backup_enabled", True),
                "app_mode": self.settings_manager.get("app_mode", "curseforge"),
                "game_id": self.settings_manager.get("game_id", 70216),
                "game_name": self.settings_manager.get("game_name", "Hytale"),
                "only_stable": self.settings_manager.get("only_stable", True),
                "ignore_beta": self.settings_manager.get("ignore_beta", True),
                "close_terminal_on_exit": self.settings_manager.get("close_terminal_on_exit", True),
                "download_rate_limit": self.settings_manager.get("download_rate_limit", 0.5),
                "full_speed_db_pagination": self.settings_manager.get("full_speed_db_pagination", False),
                "automated_update_check": self.settings_manager.get("automated_update_check", False),
                "restore_mods_on_launch": self.settings_manager.get("restore_mods_on_launch", False)
            }
        else:
            self.settings = self.load_settings()
    
    def load_settings(self) -> Dict:
        """Load user settings from the config file."""
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                settings = json.load(f)
                return settings
        else:
            return {
                "theme": "forest",
                "mod_directory": "",
                "debug_mode": False,
                "backup_enabled": True,
                "app_mode": "curseforge",
                "game_id": 70216,
                "game_name": "Hytale"
            }
    
    def save_settings(self):
        """Save user settings to the config file."""
        if self.settings_manager:
            # Use SettingsManager to save settings
            for key, value in self.settings.items():
                self.settings_manager.set(key, value)
            self.settings_manager.save()
            logger.info("Settings saved via SettingsManager")
        else:
            # Fallback to direct file save
            config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
            with open(config_path, "w") as f:
                json.dump(self.settings, f, indent=4)
    
    def apply_theme(self):
        """Apply the selected theme."""
        theme_name = self.settings.get("theme", "forest")
        theme_mode = self.settings.get("theme_mode", "auto")
        
        logger.info(f"Applying theme: {theme_name}, mode: {theme_mode}")
        
        if self.theme_manager:
            self.theme_manager.apply_theme(self.root, theme_name, theme_mode)
    
    def create_ui(self):
        """Create the main user interface."""
        self.app_window.setup_window()
        self.app_window.create_ui()
    
    def open_settings(self):
        """Open the settings panel."""
        self.settings_handlers.open_settings()
    
    def browse_mod_directory(self):
        """Open a file dialog to select the mod directory."""
        directory = filedialog.askdirectory(title="Select Hytale Mod Directory")
        if directory:
            try:
                if hasattr(self.app_window, 'mod_dir_entry'):
                    self.app_window.mod_dir_entry.delete(0, tk.END)
                    self.app_window.mod_dir_entry.insert(0, directory)
                    self.settings["mod_directory"] = directory
                    self.save_settings()
                else:
                    logger.warning("mod_dir_entry not found on app_window")
            except (OSError, IOError) as e:
                logger.error(f"Error handling mod directory browse: {e}")
    
    def browse_and_load_folder(self):
        """Open a folder dialog to select and load all .zip/.jar files from a folder using multi-threading."""
        from ..utils.file_loader import FileLoader
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import os
        
        directory = filedialog.askdirectory(title="Select Folder with .zip/.jar Files")
        if directory:
            try:
                # Start loading in background thread to prevent UI blocking
                threading.Thread(target=lambda: self._load_folder_from_directory_thread(directory), daemon=True).start()
            except (OSError, IOError, ImportError) as e:
                logger.error(f"Error loading folder {directory}: {e}")
    
    def _load_folder_from_directory_thread(self, directory: str):
        """Load all .zip/.jar files from a directory in background thread."""
        from ..utils.file_loader import FileLoader
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import os
        
        # Clear cache to ensure fresh fingerprints are computed
        # This prevents stale mod ID mappings when mods are updated outside the app
        # Preserve folder path for restore on launch
        if self.mod_id_store:
            self.mod_id_store.clear_cache(preserve_folder_path=True)
            logger.info("Cleared mod ID cache before folder load (preserved folder path)")
        
        folder_path = Path(directory)
        zip_files = list(folder_path.glob("*.zip")) + list(folder_path.glob("*.jar"))
        
        if not zip_files:
            logger.warning(f"No .zip or .jar files found in {directory}")
            return
        
        total_files = len(zip_files)
        
        # Auto-scale thread count based on CPU cores
        num_threads = min(os.cpu_count() or 4, total_files)
        logger.info(f"Using {num_threads} threads to load {total_files} files")
        
        all_contents = []
        processed_count = 0
        
        def load_zip_file(zip_file: Path) -> List[tuple]:
            """Load a single zip file and return its contents with fingerprint."""
            nonlocal processed_count
            
            file_loader = FileLoader(self)
            if file_loader.load_file(zip_file):
                contents = file_loader.get_contents()
                # Get the fingerprint from the first content entry (all entries have the same fingerprint)
                fingerprint = contents[0][3] if contents else None
                
                # Match fingerprint to mod ID if available
                mod_id = None
                if self.mod_id_store and self.api_key:
                    mod_id = file_loader.match_fingerprint(zip_file, self.mod_id_store)
                
                # Add file name prefix to distinguish entries from different files
                # Include full path for update checking
                result = [(f"{zip_file.name}/{path}", mod_id, is_dir, fingerprint, zip_file)
                          for path, size, is_dir, fingerprint in contents]
                
                # Add the zip file itself as a top-level entry with fingerprint
                result.insert(0, (zip_file.name, mod_id, False, fingerprint, zip_file))
            
                processed_count += 1
                return result
            return []
        
        # Use ThreadPoolExecutor for multi-threaded loading with batch processing
        # Process files in batches to prevent UI blocking
        BATCH_SIZE = 2  # Process 2 files at a time for more frequent progress updates
        
        # Track progress updates to process in main thread
        progress_updates = []
        
        for batch_start in range(0, len(zip_files), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(zip_files))
            batch_files = zip_files[batch_start:batch_end]
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = {executor.submit(load_zip_file, zip_file): zip_file
                          for zip_file in batch_files}
            
            for future in as_completed(futures):
                zip_file = futures[future]
                try:
                    contents = future.result()
                    all_contents.extend(contents)
                    # Log only filename, fingerprint, and mod ID (not entry count)
                    fingerprint = contents[0][3] if contents else None
                    mod_id = contents[0][1] if contents else None
                    logger.info(f"Processed {zip_file.name}: fingerprint={fingerprint}, mod_id={mod_id}")
                    
                    # Store progress update to be processed in main thread
                    progress_updates.append((zip_file, processed_count, total_files))
                    
                    # Process progress updates in main thread using root.after() for non-blocking UI updates
                    # Create a copy of the list to avoid clearing before the callback executes
                    self._process_progress_updates_async(list(progress_updates))
                    progress_updates.clear()
                except (OSError, IOError, zipfile.BadZipFile) as e:
                    logger.error(f"Error loading {zip_file.name}: {e}")
            
            # Process any remaining progress updates
            if progress_updates:
                self._process_progress_updates_async(list(progress_updates))
                progress_updates.clear()
            
            # Small delay between batches to allow UI to breathe
            self.root.after(10, lambda: None)
        
        # Clear progress after completion (but preserve mod count)
        self.root.after(0, self.app_window.clear_progress_without_mod_count)
        
        # Process any remaining progress updates
        if progress_updates:
            self._process_progress_updates_async(list(progress_updates))
        
        # Populate the treeview with all contents - use root.after() to ensure UI updates happen on main thread
        if hasattr(self, 'app_window') and hasattr(self.app_window, 'populate_file_tree'):
            # Schedule treeview population on main thread
            self.root.after(0, lambda: self._populate_file_tree_async(all_contents, folder_path, total_files))
        else:
            logger.warning("populate_file_tree method not found on app_window")
    
    def _schedule_restore_mods_from_cache(self):
        """Schedule restore_mods_from_cache with retry logic if mod_id_store is not yet initialized."""
        if not self.mod_id_store:
            # mod_id_store not initialized yet, schedule another check
            logger.debug("mod_id_store not initialized, scheduling another check")
            self.root.after(100, self._schedule_restore_mods_from_cache)
            return
        
        # mod_id_store is initialized, proceed with restore
        self.restore_mods_from_cache()
    
    def restore_mods_from_cache(self):
        """Restore the mods folder and treeview from cached data if restore_mods_on_launch is enabled."""
        if not self.settings.get("restore_mods_on_launch", False):
            logger.info("restore_mods_on_launch is disabled, skipping restore")
            return
        
        if not self.mod_id_store:
            logger.warning("mod_id_store not initialized, cannot restore from cache")
            return
        
        # Get stored folder path
        folder_path_str = self.mod_id_store.get_stored_folder_path()
        if not folder_path_str:
            logger.info("No stored folder path found in cache")
            return
        
        folder_path = Path(folder_path_str)
        if not folder_path.exists():
            logger.warning(f"Stored folder path does not exist: {folder_path}")
            self.mod_id_store.clear_stored_folder_path()
            return
        
        logger.info(f"Restoring mods from folder: {folder_path}")
        
        # Scan folder for .zip/.jar files and reload them
        # This ensures that file changes (downloads, backups, etc.) don't break restore
        zip_files = list(folder_path.glob("*.zip")) + list(folder_path.glob("*.jar"))
        
        if not zip_files:
            logger.warning(f"No .zip or .jar files found in {folder_path}")
            return
        
        logger.info(f"Found {len(zip_files)} files to restore from folder")
        
        # Start loading in background thread to prevent UI blocking
        threading.Thread(target=lambda: self._load_folder_from_directory_thread(str(folder_path)), daemon=True).start()
    
    def _process_progress_updates_async(self, progress_updates):
        """Process progress updates in the main thread using root.after() to ensure proper event loop processing."""
        def process_updates():
            for zip_file, processed_count, total_files in progress_updates:
                self.app_window.update_progress(
                    f"Calculating fingerprint of {zip_file.name} ({processed_count}/{total_files})",
                    processed_count,
                    total_files
                )
            # Process pending UI events to ensure progress bar updates are rendered (non-blocking)
            self.root.update_idletasks()
        
        # Schedule the update on the main thread
        self.root.after(0, process_updates)
    
    def _process_progress_updates_sync(self, progress_updates):
        """Process progress updates synchronously - directly update the UI."""
        for zip_file, processed_count, total_files in progress_updates:
            self.app_window.update_progress(
                f"Calculating fingerprint of {zip_file.name} ({processed_count}/{total_files})",
                processed_count,
                total_files
            )
        # Process pending UI events to ensure progress bar updates are rendered
        self.root.update_idletasks()
    
    def _populate_file_tree_async(self, contents: List[tuple], folder_path: Path, total_files: int):
        """Populate the file treeview asynchronously on the main thread."""
        if hasattr(self, 'app_window') and hasattr(self.app_window, 'populate_file_tree'):
            self.app_window.populate_file_tree(contents)
            logger.info(f"Loaded {total_files} files from folder")
            
            # Store the folder path for update checking
            self.last_loaded_folder = folder_path
            logger.info(f"Stored last_loaded_folder: {folder_path}")
            
            # Store folder path in mod ID cache for restore on launch
            # Only the folder path is stored - files are re-scanned on restore
            # This ensures that file changes (downloads, backups, etc.) don't break restore
            if self.mod_id_store:
                self.mod_id_store.set_stored_folder_path(str(folder_path))
                logger.info(f"Stored folder path in cache for restore: {folder_path}")
            
            # Update mod directory entry to show selected path
            if hasattr(self.app_window, 'mod_dir_entry'):
                self.app_window.mod_dir_entry.delete(0, tk.END)
                self.app_window.mod_dir_entry.insert(0, str(folder_path))
                self.settings["mod_directory"] = str(folder_path)
                self.save_settings()
            else:
                logger.warning("mod_dir_entry not found on app_window")
            
            # Count only top-level files (entries without "/" in path - the actual zip/jar files)
            # Handle both 4-tuple and 5-tuple formats
            top_level_file_count = sum(1 for item in contents if '/' not in item[0])
            # Update mod count display
            database_count = self.mod_database_manager.get_mod_count() if self.mod_database_manager else 0
            self.app_window.update_mod_count(top_level_file_count, database_count)
            
            # Check if automated update check is enabled and not already in progress
            if self.settings.get("automated_update_check", False) and not self._automated_update_check_in_progress:
                logger.info("Automated update check is enabled, running update check and download automatically")
                # Mark update check as in progress
                self._automated_update_check_in_progress = True
                # Run update check after a short delay to ensure UI is updated
                self.root.after(100, self._run_automated_update_check)
        else:
            logger.warning("populate_file_tree method not found on app_window")
    
    def toggle_debug_mode(self, enabled: bool):
        """Toggle debug mode and update logging configuration."""
        from utils.logging import setup_logging
        if enabled:
            setup_logging(debug_mode=True, log_path=self.path_manager.log_path)
            logger.info("Debug mode enabled from settings")
        else:
            setup_logging(debug_mode=False, log_path=self.path_manager.log_path)
            logger.info("Debug mode disabled from settings")
    
    def toggle_backup(self):
        """Toggle backup setting."""
        enabled = getattr(self, 'backup_enabled_var', False)
        self.settings["backup_enabled"] = enabled
        self.save_settings()
        logger.info(f"Backup setting changed to: {enabled}")
    
    def save_theme_settings(self, theme: str, mode: str, debug_mode: bool, window: tk.Toplevel):
        """Save the selected theme, mode, and debug mode."""
        self.settings["theme"] = theme
        self.settings["theme_mode"] = mode
        self.settings["debug_mode"] = debug_mode
        self.save_settings()
        self.apply_theme()
        
        if debug_mode:
            messagebox.showinfo(
                "Restart Required",
                "Debug mode changes will take effect after restarting the application.\n\n"
                "The application will now close. Please restart it to enable debug logging."
            )
            self.root.quit()
            return
        
        window.destroy()
    
    def preview_theme(self, theme: str, mode: str):
        """Preview the selected theme and mode without saving."""
        temp_theme = self.settings.get("theme")
        temp_mode = self.settings.get("theme_mode")
        self.settings["theme"] = theme
        self.settings["theme_mode"] = mode
        self.apply_theme()
        self.settings["theme"] = temp_theme
        self.settings["theme_mode"] = temp_mode
    
    def _apply_theme_to_window(self, window: tk.Toplevel):
        """Apply the current theme to a window."""
        theme_name = self.settings.get("theme", "forest")
        theme_mode = self.settings.get("theme_mode", "auto")
        
        if self.theme_manager:
            self.theme_manager.apply_theme(window, theme_name, theme_mode)
    
    def check_for_updates(self):
        """Check for updates for all loaded mod files (non-blocking)."""
        # Run update check in background thread to prevent UI blocking
        threading.Thread(target=self._check_for_updates_thread, daemon=True).start()
    
    def _check_for_updates_thread(self):
        """Background thread method to check for updates."""
        try:
            from services.update_checker import UpdateChecker
            
            if not self.mod_database_manager:
                self.root.after(0, lambda: messagebox.showerror(
                    "Database Not Available",
                    "The mod database is not initialized. Please ensure you have an API key configured."
                ))
                logger.error("Database manager not available")
                return
            
            if not self.mod_id_store:
                self.root.after(0, lambda: messagebox.showerror(
                    "Mod ID Store Not Available",
                    "The mod ID store is not initialized."
                ))
                logger.error("Mod ID store not available")
                return
            
            # Get mod directory from settings
            mod_directory = self.settings.get("mod_directory", "")
            if not mod_directory:
                self.root.after(0, lambda: messagebox.showwarning(
                    "No Mod Directory",
                    "Please set the mod directory in settings first."
                ))
                logger.warning("No mod directory set")
                return
            
            directory_path = Path(mod_directory)
            if not directory_path.exists():
                self.root.after(0, lambda: messagebox.showerror(
                    "Directory Not Found",
                    f"The mod directory does not exist: {mod_directory}"
                ))
                logger.error(f"Mod directory not found: {mod_directory}")
                return
            
            # Get current treeview contents
            contents = []
            if hasattr(self.app_window, 'file_tree') and self.app_window.file_tree:
                logger.info(f"check_for_updates: Getting treeview children, count: {len(self.app_window.file_tree.get_children())}")
                for item in self.app_window.file_tree.get_children():
                    item_text = self.app_window.file_tree.item(item, "text")
                    values = self.app_window.file_tree.item(item, "values")
                    logger.info(f"check_for_updates: Item {item}: text={item_text}, values={values}")
                    if values:
                        # Convert formatted strings back to integers
                        mod_id = int(values[0]) if values[0] and values[0] != "N/A" else None
                        fingerprint = int(values[1]) if values[1] and values[1] != "N/A" else None
                        # Handle both 4-tuple and 5-tuple formats
                        if len(values) >= 4:
                            # 5-tuple format: (mod_id, fingerprint, is_dir, fingerprint, file_path)
                            file_path = values[4] if len(values) > 4 else None
                            contents.append((item_text, mod_id, False, fingerprint, file_path))
                        else:
                            # 4-tuple format: (mod_id, fingerprint)
                            contents.append((item_text, mod_id, False, fingerprint))
                        logger.info(f"check_for_updates: Added to contents: (item_text={item_text}, mod_id={mod_id}, fingerprint={fingerprint})")
            
            # Create update checker
            update_checker = UpdateChecker(self.mod_database_manager, self.mod_id_store)
            
            # Check for updates using treeview contents (which already have mod_id and fingerprint)
            # Use last_loaded_folder if available, otherwise use mod_directory from settings
            check_directory = self.last_loaded_folder or directory_path
            logger.info(f"check_for_updates: Using directory {check_directory} for update checking")
            
            # Define progress callback to update UI (thread-safe)
            def progress_callback(current, total, filename):
                # Use root.after to schedule UI updates on the main thread
                def update_ui():
                    progress_text = f"Checking {filename} ({current}/{total})"
                    self.app_window.update_progress(progress_text, current, total)
                    # Process pending UI events to ensure progress bar updates are rendered
                    self.root.update_idletasks()
                
                # Schedule UI update on main thread
                self.root.after(0, update_ui)
            
            outdated_mods = update_checker.check_from_treeview(contents, check_directory, progress_callback)
            
            # Clear progress after update check (without resetting mod count)
            self.root.after(0, self.app_window.clear_progress_without_mod_count)
            
            # Debug: Log outdated_mods to see what it contains
            logger.info(f"outdated_mods type: {type(outdated_mods)}, length: {len(outdated_mods)}")
            if outdated_mods:
                logger.info(f"First outdated_mod: {outdated_mods[0]}, type: {type(outdated_mods[0])}")
            
            # Populate treeview with update status
            logger.info(f"outdated_mod_ids comprehension: type(outdated_mods)={type(outdated_mods)}, len={len(outdated_mods)}")
            if outdated_mods:
                logger.info(f"First item for comprehension: type={type(outdated_mods[0])}, value={outdated_mods[0]}")
            outdated_mod_ids = {mod["mod_id"] for mod in outdated_mods}
            logger.info(f"outdated_mod_ids: {outdated_mod_ids}")
            logger.info("Calling populate_file_tree_with_updates...")
            
            # Update UI on main thread
            self.root.after(0, lambda: self._populate_treeview_with_updates_thread(contents, outdated_mod_ids, outdated_mods))
            
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Error checking for updates: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Update Check Error",
                f"An error occurred while checking for updates:\n\n{str(e)}"
            ))
    
    def _populate_treeview_with_updates_thread(self, contents, outdated_mod_ids, outdated_mods=None):
        """Background thread method to populate treeview with updates."""
        try:
            self.app_window.populate_file_tree_with_updates(contents, outdated_mod_ids)
            logger.info("populate_file_tree_with_updates completed")
            
            # Show results
            if outdated_mods:
                from services.update_checker import UpdateChecker
                update_checker = UpdateChecker(self.mod_database_manager, self.mod_id_store)
                summary = update_checker.get_update_summary(outdated_mods)
                mod_count = summary["outdated_count"]
                
                logger.info(f"Summary: {summary}")
                logger.info(f"Summary mods type: {type(summary.get('mods'))}")
                if summary.get('mods'):
                    logger.info(f"First mod: {summary['mods'][0]}")
                
                # Show updates dialog with scrollable content
                self.root.after(0, lambda: self._show_updates_dialog(summary["mods"]))
                
                logger.info(f"Found {mod_count} outdated mods")
            else:
                self.root.after(0, lambda: messagebox.showinfo("No Updates", "All mods are up to date!"))
                logger.info("All mods are up to date")
                
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Error populating treeview with updates: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Update Check Error",
                f"An error occurred while checking for updates:\n\n{str(e)}"
            ))
    
    def _show_updates_dialog(self, mods):
        """Show the updates dialog on the main thread."""
        from ui.dialogs import UpdatesDialog
        updates_dialog = UpdatesDialog(self.root, self, mods)
        updates_dialog.show()
    
    def _run_automated_update_check(self):
        """Run automated update check and download after loading mods."""
        try:
            logger.info("Starting automated update check process")
            
            # Step 1: Check for updates (same as check_for_updates but without showing dialog)
            threading.Thread(target=self._automated_update_check_thread, daemon=True).start()
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Error in automated update check: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Automated Update Error",
                f"An error occurred during automated update check:\n\n{str(e)}"
            ))
    
    def _automated_update_check_thread(self):
        """Background thread method to run automated update check and download."""
        try:
            from services.update_checker import UpdateChecker
            
            if not self.mod_database_manager:
                self.root.after(0, lambda: messagebox.showerror(
                    "Database Not Available",
                    "The mod database is not initialized. Please ensure you have an API key configured."
                ))
                logger.error("Database manager not available")
                return
            
            if not self.mod_id_store:
                self.root.after(0, lambda: messagebox.showerror(
                    "Mod ID Store Not Available",
                    "The mod ID store is not initialized."
                ))
                logger.error("Mod ID store not available")
                return
            
            # Use last_loaded_folder if available, otherwise use mod_directory from settings
            mod_directory = self.last_loaded_folder or self.settings.get("mod_directory", "")
            if not mod_directory:
                self.root.after(0, lambda: messagebox.showwarning(
                    "No Mod Directory",
                    "Please set the mod directory in settings or load a folder first."
                ))
                logger.warning("No mod directory set")
                return
            
            directory_path = Path(mod_directory)
            if not directory_path.exists():
                self.root.after(0, lambda: messagebox.showerror(
                    "Directory Not Found",
                    f"The mod directory does not exist: {mod_directory}"
                ))
                logger.error(f"Mod directory not found: {mod_directory}")
                return
            
            # Get current treeview contents
            contents = []
            if hasattr(self.app_window, 'file_tree') and self.app_window.file_tree:
                for item in self.app_window.file_tree.get_children():
                    item_text = self.app_window.file_tree.item(item, "text")
                    values = self.app_window.file_tree.item(item, "values")
                    if values:
                        mod_id = int(values[0]) if values[0] and values[0] != "N/A" else None
                        fingerprint = int(values[1]) if values[1] and values[1] != "N/A" else None
                        # Handle both 4-tuple and 5-tuple formats
                        if len(values) >= 4:
                            file_path = values[4] if len(values) > 4 else None
                            contents.append((item_text, mod_id, False, fingerprint, file_path))
                        else:
                            contents.append((item_text, mod_id, False, fingerprint))
            
            # Create update checker
            update_checker = UpdateChecker(self.mod_database_manager, self.mod_id_store)
            
            # Check for updates using treeview contents
            check_directory = self.last_loaded_folder or directory_path
            logger.info(f"_automated_update_check_thread: Using directory {check_directory} for update checking")
            
            # Define progress callback to update UI (thread-safe)
            def progress_callback(current, total, filename):
                # Use root.after to schedule UI updates on the main thread
                def update_ui():
                    progress_text = f"Checking {filename} ({current}/{total})"
                    self.app_window.update_progress(progress_text, current, total)
                    self.root.update_idletasks()
                
                self.root.after(0, update_ui)
            
            outdated_mods = update_checker.check_from_treeview(contents, check_directory, progress_callback)
            
            # Clear progress after update check
            self.root.after(0, self.app_window.clear_progress)
            
            logger.info(f"Automated update check found {len(outdated_mods)} outdated mods")
            
            if not outdated_mods:
                self.root.after(0, lambda: messagebox.showinfo("No Updates", "All mods are up to date!"))
                logger.info("No outdated mods found")
                return
            
            # Update treeview with outdated status
            self.root.after(0, lambda: self.app_window.populate_file_tree_with_updates(contents, outdated_mods))
            
            # Show summary of outdated mods
            from services.update_checker import UpdateChecker
            update_checker = UpdateChecker(self.mod_database_manager, self.mod_id_store)
            summary = update_checker.get_update_summary(outdated_mods)
            mod_count = summary["outdated_count"]
            
            # Show a simple message showing how many mods are outdated
            self.root.after(0, lambda: messagebox.showinfo(
                "Update Check Complete",
                f"Found {mod_count} outdated mod(s). Downloading automatically..."
            ))
            
            # Wait a moment for the message to be seen, then start download
            self.root.after(2000, self.download_outdated_mods)
            
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Error in automated update check thread: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Update Check Error",
                f"An error occurred while checking for updates:\n\n{str(e)}"
            ))
    
    def download_outdated_mods(self):
        """Download outdated mods after checking for updates (non-blocking)."""
        # Run download in background thread to prevent UI blocking
        threading.Thread(target=self._download_outdated_mods_thread, daemon=True).start()
    
    def _download_outdated_mods_thread(self):
        """Background thread method to download outdated mods."""
        try:
            self._download_outdated_mods_logic()
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Error in download_outdated_mods: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Download Error",
                f"An error occurred while downloading mods:\n\n{str(e)}"
            ))
    
    def _download_outdated_mods_logic(self):
        """Logic for downloading outdated mods - extracted to reduce try block complexity."""
        from services.update_checker import UpdateChecker
        from services.mod_downloader import ModDownloader
        from utils.fingerprint import compute_fingerprint
        
        if not self.mod_database_manager:
            self.root.after(0, lambda: messagebox.showerror(
                "Database Not Available",
                "The mod database is not initialized. Please ensure you have an API key configured."
            ))
            logger.error("Database manager not available")
            return
        
        if not self.api_key:
            self.root.after(0, lambda: messagebox.showerror(
                "API Key Required",
                "Please configure your CurseForge API key in settings."
            ))
            logger.error("No API key available")
            return
        
        # Use last_loaded_folder if available, otherwise use mod_directory from settings
        mod_directory = self.last_loaded_folder or self.settings.get("mod_directory", "")
        if not mod_directory:
            self.root.after(0, lambda: messagebox.showwarning(
                "No Mod Directory",
                "Please set the mod directory in settings or load a folder first."
            ))
            logger.warning("No mod directory set")
            return
        
        directory_path = Path(mod_directory)
        if not directory_path.exists():
            self.root.after(0, lambda: messagebox.showerror(
                "Directory Not Found",
                f"The mod directory does not exist: {mod_directory}"
            ))
            logger.error(f"Mod directory not found: {mod_directory}")
            return
        
        # Get current treeview contents
        contents = []
        if hasattr(self.app_window, 'file_tree') and self.app_window.file_tree:
            for item in self.app_window.file_tree.get_children():
                item_text = self.app_window.file_tree.item(item, "text")
                values = self.app_window.file_tree.item(item, "values")
                if values:
                    mod_id = int(values[0]) if values[0] and values[0] != "N/A" else None
                    fingerprint = int(values[1]) if values[1] and values[1] != "N/A" else None
                    # Handle both 4-tuple and 5-tuple formats
                    if len(values) >= 4:
                        file_path = values[4] if len(values) > 4 else None
                        contents.append((item_text, mod_id, False, fingerprint, file_path))
                    else:
                        contents.append((item_text, mod_id, False, fingerprint))
        
        # Initialize update_checker for both branches
        update_checker = UpdateChecker(self.mod_database_manager, self.mod_id_store)
        
        # Check if we have outdated mods (check if treeview has outdated status)
        has_outdated = any(
            self.app_window.file_tree.item(item, "tags") and "outdated" in self.app_window.file_tree.item(item, "tags")
            for item in self.app_window.file_tree.get_children()
        )
        
        if not has_outdated:
            # Run update check first
            if not self.mod_id_store:
                self.root.after(0, lambda: messagebox.showerror(
                    "Mod ID Store Not Available",
                    "The mod ID store is not initialized."
                ))
                logger.error("Mod ID store not available")
                return
            
            outdated_mods = update_checker.check_from_treeview(contents, directory_path)
            
            if not outdated_mods:
                self.root.after(0, lambda: messagebox.showinfo("No Updates", "All mods are up to date!"))
                logger.info("No outdated mods found")
                return
            
            # Update treeview with outdated status
            outdated_mod_ids = {mod["mod_id"] for mod in outdated_mods}
            self.root.after(0, lambda: self.app_window.populate_file_tree_with_updates(contents, outdated_mod_ids))
        else:
            # Extract outdated mods from treeview
            outdated_mods = []
            for item in self.app_window.file_tree.get_children():
                tags = self.app_window.file_tree.item(item, "tags")
                if tags and "outdated" in tags:
                    item_text = self.app_window.file_tree.item(item, "text")
                    values = self.app_window.file_tree.item(item, "values")
                    mod_id = int(values[0]) if values[0] and values[0] != "N/A" else None
                    
                    if mod_id is None:
                        continue
                    
                    # Get latest file info from database
                    mod_info = self.mod_database_manager.get_mod_info(mod_id)
                    if mod_info:
                        outdated_mods.append({
                            "file_path": directory_path / item_text,
                            "mod_id": mod_id,
                            "latest_file_id": mod_info.get("latest_file_id"),
                            "latest_fingerprint": mod_info.get("latest_file_fingerprint"),
                            "author": mod_info.get("author"),
                            "project_name": mod_info.get("name")
                        })
        
        if not outdated_mods:
            self.root.after(0, lambda: messagebox.showinfo("No Updates", "All mods are up to date!"))
            return
        
        # Show backup options dialog
        self.root.after(0, lambda: self._show_backup_dialog(outdated_mods, directory_path))
    
    def _show_backup_dialog(self, outdated_mods, directory_path):
        """Show backup options dialog and handle download."""
        from ui.dialogs import BackupOptionsDialog
        from services.mod_downloader import ModDownloader
        
        backup_dialog = BackupOptionsDialog(self.root, outdated_mods)
        backup_choice = backup_dialog.show()
        
        if not backup_choice:
            logger.info("No backup option selected, cancelling download")
            return
        
        # Initialize backup manager for later use
        from services.backup_manager import BackupManager
        # Store backups in the executable directory, not the mod directory
        backup_dir = Path(self.path_manager.base_path) / "backups"
        backup_manager = BackupManager(directory_path, backup_dir)
        
        # Phase 1: Backup/Recycle/Delete with progress
        self.app_window.update_progress(f"Processing {len(outdated_mods)} mod(s)...", 0, len(outdated_mods))
        
        if backup_choice == "backup":
            for i, outdated_mod in enumerate(outdated_mods):
                old_file_path = outdated_mod["file_path"]
                if old_file_path.exists():
                    backup_manager.create_backup(old_file_path)
                    self.app_window.update_progress(
                        f"Backing up {old_file_path.name}", i + 1, len(outdated_mods)
                    )
                    # Process pending UI events to ensure progress bar updates are rendered
                    self.root.update_idletasks()
        elif backup_choice == "recycle":
            for i, outdated_mod in enumerate(outdated_mods):
                old_file_path = outdated_mod["file_path"]
                if old_file_path.exists():
                    backup_manager.move_to_recycle_bin(old_file_path)
                    self.app_window.update_progress(
                        f"Moving to Recycle Bin: {old_file_path.name}", i + 1, len(outdated_mods)
                    )
                    # Process pending UI events to ensure progress bar updates are rendered
                    self.root.update_idletasks()
        elif backup_choice == "delete":
            for i, outdated_mod in enumerate(outdated_mods):
                old_file_path = outdated_mod["file_path"]
                if old_file_path.exists():
                    backup_manager.permanently_delete(old_file_path)
                    self.app_window.update_progress(
                        f"Deleting {old_file_path.name}", i + 1, len(outdated_mods)
                    )
                    # Process pending UI events to ensure progress bar updates are rendered
                    self.root.update_idletasks()
        
        # Clear progress after backup operations
        self.app_window.clear_progress()
        
        # Start downloads - set window always-on-top to stay on top of Playwright browsers
        self._start_downloads()
        
        # Set indeterminate progress mode for downloads
        # Progress bar will show continuous animation (spinning) during downloads
        self.app_window.set_indeterminate_progress("Downloading outdated mods...")
        
        # Run downloads in a separate thread to keep UI responsive
        def download_thread():
            try:
                rate_limit_delay = self.settings.get("download_rate_limit", 0.5)
                api_key = self.api_key
                assert api_key is not None
                downloader = ModDownloader(api_key, directory_path, rate_limit_delay)
                
                # No progress callback - downloads run in background with indeterminate progress
                download_results = downloader.download_mods(outdated_mods, progress_callback=None, max_workers=3)
                
                # Schedule result handling on main thread
                self.root.after(0, lambda: self._handle_download_results(download_results, backup_manager, backup_dir, directory_path))
            except Exception as e:
                logger.error(f"Error in download thread: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Download Error",
                    f"An error occurred while downloading mods:\n\n{str(e)}"
                ))
            finally:
                # End downloads - disable always-on-top
                self._end_downloads()
        
        # Start the download thread
        threading.Thread(target=download_thread, daemon=True).start()
        return  # Exit early - results handled in _handle_download_results
    
    def _handle_download_results(self, download_results, backup_manager, backup_dir, directory_path):
        """Handle download results on the main thread."""
        # Clear indeterminate progress before showing results
        self.app_window.clear_progress()
        
        # Show download results
        success_count = len(download_results["success"])
        failed_count = len(download_results["failed"])
        
        # Phase 3: Restore backups for failed downloads with progress
        if failed_count > 0:
            self.app_window.update_progress(
                f"Restoring {failed_count} failed download(s)...", 0, failed_count
            )
            
            for i, failed_mod in enumerate(download_results["failed"]):
                failed_filename = failed_mod["filename"]
                failed_file_path = directory_path / failed_filename
                if not failed_file_path.exists():
                    # Try to restore from backup directory
                    backup_file_path = backup_dir / (failed_filename + ".old")
                    if backup_file_path.exists():
                        restored_path = backup_manager.restore_backup(str(backup_file_path))
                        if restored_path:
                            logger.info(f"Restored backup for failed download: {failed_filename}")
                        else:
                            logger.error(f"Failed to restore backup for: {failed_filename}")
                    else:
                        logger.warning(f"No backup found for failed download: {failed_filename}")
                
                self.app_window.update_progress(
                    f"Restoring {failed_filename}", i + 1, failed_count
                )
            
            self.app_window.clear_progress()
        
        # Update mod count display after download/restore
        # Re-count loaded files from directory
        zip_files = list(directory_path.glob("*.zip")) + list(directory_path.glob("*.jar"))
        top_level_file_count = len(zip_files)
        database_count = self.mod_database_manager.get_mod_count() if self.mod_database_manager else 0
        self.app_window.update_mod_count(top_level_file_count, database_count)
        
        # Refresh treeview after downloads to show updated files
        if success_count > 0:
            logger.info("Refreshing treeview after downloads...")
            self.root.after(0, lambda: self._refresh_treeview_after_download(directory_path))
        
        if success_count > 0 or failed_count > 0:
            # Get list of failed mod info with download URLs
            failed_mods = download_results["failed"]
            
            # Separate API failures from Playwright successes/failures
            api_failed_mods = []
            playwright_success = []
            playwright_failed = []
            
            for failed_mod in failed_mods:
                # Check if this is a Playwright fallback attempt
                if failed_mod.get("playwright_attempted"):
                    if failed_mod.get("playwright_success"):
                        playwright_success.append(failed_mod)
                    else:
                        playwright_failed.append(failed_mod)
                else:
                    api_failed_mods.append(failed_mod)
            
            # Get error message from download results
            error_message = download_results.get("error_message", "")
            
            # Show appropriate dialog based on Playwright results
            if playwright_success or playwright_failed:
                self.root.after(0, lambda: self._show_playwright_dialog(api_failed_mods, playwright_success, playwright_failed))
            else:
                self.root.after(0, lambda: self._show_download_complete_dialog(failed_mods, error_message, success_count, directory_path))
    
    def _show_playwright_dialog(self, api_failed_mods, playwright_success, playwright_failed):
        """Show Playwright download result dialog on main thread."""
        from ui.dialogs import PlaywrightDownloadResultDialog
        playwright_dialog = PlaywrightDownloadResultDialog(
            self.root, self,
            api_failed_mods,
            playwright_success,
            playwright_failed
        )
        playwright_dialog.show()
    
    def _show_download_complete_dialog(self, failed_mods, error_message, success_count=0, directory_path=None):
        """Show download complete dialog on main thread."""
        from ui.dialogs import DownloadCompleteDialog
        download_dialog = DownloadCompleteDialog(self.root, self, success_count, len(failed_mods), failed_mods, error_message, directory_path)
        download_dialog.show()
    
    def refresh_database(self):
        """Refresh the mod database from CurseForge in a background thread."""
        try:
            if not self.mod_database_manager:
                messagebox.showerror(
                    "Database Not Available",
                    "The mod database is not initialized."
                )
                logger.error("Database manager not available")
                return
            
            if not self.api_key:
                messagebox.showerror(
                    "API Key Required",
                    "Please configure your CurseForge API key in settings."
                )
                logger.error("No API key available")
                return
            
            # Initialize database in background thread to prevent UI freeze
            import threading
            thread = threading.Thread(
                target=self._refresh_database_thread,
                args=(self.api_key,),
                daemon=True
            )
            thread.start()
            logger.info("Database refresh started in background thread")
            
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Error starting database refresh: {e}")
            self.app_window.clear_progress()
            messagebox.showerror(
                "Database Refresh Error",
                f"An error occurred while starting the database refresh:\n\n{str(e)}"
            )
    
    def _refresh_database_thread(self, api_key):
        """Background thread method for refreshing the database."""
        try:
            # Initialize database (fetches all mods)
            from services.curseforge_api import CurseForgeAPI
            # Enable full-speed mode if setting is enabled (disables rate limiting)
            rate_limit_enabled = not self.settings.get("full_speed_db_pagination", False)
            api = CurseForgeAPI(api_key, rate_limit_enabled=rate_limit_enabled)
            
            # Define progress callback to update UI (thread-safe)
            def progress_callback(stage, value, max_value):
                # Use root.after to schedule UI updates on the main thread
                def update_ui():
                    if stage == "fetching":
                        # Fetching stage: show page progress
                        page_num = value
                        total_pages = max_value
                        progress_pct = (page_num / total_pages) * 100 if total_pages > 0 else 0
                        self.app_window.update_progress(f"Fetching page {page_num}/{total_pages}...", progress_pct, 100)
                    elif stage == "processing":
                        # Processing stage: show mod processing progress
                        mod_num = value
                        total_mods = max_value
                        progress_pct = (mod_num / total_mods) * 100 if total_mods > 0 else 0
                        self.app_window.update_progress(f"Processing mod {mod_num}/{total_mods}...", progress_pct, 100)
                
                # Schedule UI update on main thread
                self.root.after(0, update_ui)
            
            # Type narrowing: mod_database_manager is guaranteed to be non-None here
            mod_db_manager = self.mod_database_manager
            assert mod_db_manager is not None
            success = mod_db_manager.initialize_database(api, progress_callback)
            
            # Schedule result handling on main thread
            def handle_result():
                if success:
                    mod_count = mod_db_manager.get_mod_count()
                    # Preserve the current loaded count when refreshing database
                    loaded_count = len(self.app_window.file_tree.get_children()) if hasattr(self.app_window, 'file_tree') and self.app_window.file_tree else 0
                    self.app_window.update_mod_count(loaded_count, mod_count)
                    from ui.dialogs import DatabaseRefreshedDialog
                    DatabaseRefreshedDialog(self.root, self, mod_count).show()
                    logger.info(f"Database refreshed with {mod_count} mods")
                else:
                    self.app_window.clear_progress()
                    messagebox.showerror(
                        "Database Refresh Failed",
                        "Failed to refresh the mod database. Check logs for details."
                    )
                    logger.error("Database refresh failed")
            
            self.root.after(0, handle_result)
            
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Error refreshing database: {e}")
            # Schedule error handling on main thread
            def handle_error():
                self.app_window.clear_progress()
                messagebox.showerror(
                    "Database Refresh Error",
                    f"An error occurred while refreshing the database:\n\n{str(e)}"
                )
            self.root.after(0, handle_error)
    
    def populate_file_tree_with_updates(self, contents, outdated_mods):
        """
        Populate the file treeview with contents and update status.
        
        Args:
            contents: List of tuples (path, mod_id, is_dir, fingerprint)
            outdated_mods: List of outdated mod info dictionaries
        """
        # Create a set of outdated mod IDs for quick lookup
        outdated_mod_ids = {mod["mod_id"] for mod in outdated_mods}
        
        # Update the treeview with outdated status
        if hasattr(self, 'app_window') and hasattr(self.app_window, 'populate_file_tree_with_updates'):
            self.app_window.populate_file_tree_with_updates(contents, outdated_mod_ids)
        else:
            # Fallback to regular populate if method not available
            self.app_window.populate_file_tree(contents)
    
    def _refresh_treeview_after_download(self, directory_path: Path):
        """
        Refresh the treeview after downloads by re-loading files from directory.
        
        Args:
            directory_path: Path to the mod directory
        """
        try:
            from utils.file_loader import FileLoader
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import os
            
            # Get all zip/jar files in the directory
            zip_files = list(directory_path.glob("*.zip")) + list(directory_path.glob("*.jar"))
            
            if not zip_files:
                logger.warning(f"No .zip or .jar files found in {directory_path}")
                return
            
            total_files = len(zip_files)
            
            # Clear cache before re-loading to ensure fresh fingerprints
            # Preserve folder path for restore on launch
            if self.mod_id_store:
                self.mod_id_store.clear_cache(preserve_folder_path=True)
                logger.info("Cleared mod ID cache before re-loading files after download (preserved folder path)")
            
            # Auto-scale thread count based on CPU cores
            num_threads = min(os.cpu_count() or 4, total_files)
            logger.info(f"Using {num_threads} threads to re-load {total_files} files after download")
            
            all_contents = []
            processed_count = 0
            
            def load_zip_file(zip_file: Path) -> tuple:
                """Load a single zip file and return its contents with fingerprint and processed count."""
                nonlocal processed_count
                
                file_loader = FileLoader(self)
                if file_loader.load_file(zip_file):
                    contents = file_loader.get_contents()
                    # Get the fingerprint from the first content entry (all entries have the same fingerprint)
                    fingerprint = contents[0][3] if contents else None
                    
                    # Match fingerprint to mod ID if available
                    mod_id = None
                    if self.mod_id_store and self.api_key:
                        mod_id = file_loader.match_fingerprint(zip_file)
                    
                    # Add file name prefix to distinguish entries from different files
                    result = [(f"{zip_file.name}/{path}", mod_id, is_dir, fingerprint)
                              for path, size, is_dir, fingerprint in contents]
                    
                    # Add the zip file itself as a top-level entry with fingerprint
                    result.insert(0, (zip_file.name, mod_id, False, fingerprint))
                
                    processed_count += 1
                    return (result, processed_count)
                return ([], processed_count)
            
            # Use ThreadPoolExecutor for multi-threaded loading with batch processing
            # Process files in batches to prevent UI blocking
            BATCH_SIZE = 50  # Process 50 files at a time
            
            for batch_start in range(0, len(zip_files), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(zip_files))
                batch_files = zip_files[batch_start:batch_end]
                
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = {executor.submit(load_zip_file, zip_file): zip_file
                              for zip_file in batch_files}
                
                for future in as_completed(futures):
                    zip_file = futures[future]
                    try:
                        result = future.result()
                        contents = result[0] if isinstance(result, tuple) else result
                        processed_count = result[1] if isinstance(result, tuple) else processed_count
                        all_contents.extend(contents)
                        logger.info(f"Re-loaded {len(contents)} entries from {zip_file.name}")
                        
                        # Schedule progress update on main thread with the captured processed_count
                        self.root.after(0, lambda zf=zip_file, pc=processed_count, tf=total_files: self.app_window.update_progress(
                            f"Calculating fingerprint of {zf.name} ({pc}/{tf})",
                            pc,
                            tf
                        ))
                    except (OSError, IOError, zipfile.BadZipFile) as e:
                        logger.error(f"Error re-loading {zip_file.name}: {e}")
                
                # Small delay between batches to allow UI to breathe
                self.root.after(10, lambda: None)
            
            # Clear progress after completion (but preserve mod count)
            self.root.after(0, self.app_window.clear_progress_without_mod_count)
            
            # Populate the treeview with all contents - use root.after() to ensure UI updates happen on main thread
            if hasattr(self, 'app_window') and hasattr(self.app_window, 'populate_file_tree'):
                # Schedule treeview population on main thread
                self.root.after(0, lambda: self._populate_file_tree_async(all_contents, directory_path, total_files))
            else:
                logger.warning("populate_file_tree method not found on app_window")
                
        except (OSError, IOError, zipfile.BadZipFile) as e:
            logger.error(f"Error refreshing treeview after download: {e}")
    
    def _set_window_always_on_top(self, value: bool):
        """
        Set the window always-on-top behavior during downloads.
        
        Args:
            value: True to enable always-on-top, False to disable
        """
        try:
            # Use Windows-specific topmost flag
            if value:
                self.root.attributes("-topmost", True)
                logger.debug("Enabled window always-on-top during downloads")
            else:
                self.root.attributes("-topmost", False)
                logger.debug("Disabled window always-on-top after downloads")
        except (OSError, IOError) as e:
            logger.error(f"Failed to set window always-on-top: {e}")
    
    def _start_downloads(self):
        """
        Prepare for downloads by enabling always-on-top and keeping window focused.
        """
        if not self._downloads_in_progress:
            self._downloads_in_progress = True
            self._set_window_always_on_top(True)
            # Bring window to front
            self.root.lift()
            self.root.focus_force()
            logger.info("Downloads started - window set to always-on-top")
    
    def _end_downloads(self):
        """
        Clean up after downloads by disabling always-on-top.
        """
        if self._downloads_in_progress:
            self._downloads_in_progress = False
            self._set_window_always_on_top(False)
            logger.info("Downloads ended - window always-on-top disabled")
    
    def restore_backups(self):
        """Restore outdated mod backups."""
        try:
            from services.backup_manager import BackupManager
            from ui.dialogs import RestoreBackupsDialog
            
            if not self.api_key:
                messagebox.showerror(
                    "API Key Required",
                    "Please configure your CurseForge API key in settings."
                )
                logger.error("No API key available")
                return
            
            # Get mod directory from settings
            mod_directory = self.settings.get("mod_directory", "")
            if not mod_directory:
                messagebox.showwarning(
                    "No Mod Directory",
                    "Please set the mod directory in settings first."
                )
                logger.warning("No mod directory set")
                return
            
            directory_path = Path(mod_directory)
            if not directory_path.exists():
                messagebox.showerror(
                    "Directory Not Found",
                    f"The mod directory does not exist: {mod_directory}"
                )
                logger.error(f"Mod directory not found: {mod_directory}")
                return
            
            # Initialize backup manager
            # Use the same backup directory as download_outdated_mods
            # Type narrowing: path_manager is guaranteed to be non-None here
            path_manager = self.path_manager
            assert path_manager is not None
            backup_dir = Path(path_manager.base_path) / "backups"
            backup_manager = BackupManager(directory_path, backup_dir)
            
            # Get list of backup files
            backup_list = backup_manager.get_backup_list()
            
            if not backup_list:
                messagebox.showinfo("No Backups", "No backup files found.")
                logger.info("No backup files found")
                return
            
            # Show restore backups dialog
            restore_dialog = RestoreBackupsDialog(self.root, backup_list)
            selected_backups = restore_dialog.show()
            
            if not selected_backups:
                logger.info("No backups selected for restore")
                return
            
            # Restore selected backups
            restored_count = 0
            for backup_path in selected_backups:
                restored_path = backup_manager.restore_backup(backup_path)
                if restored_path:
                    restored_count += 1
            
            if restored_count > 0:
                messagebox.showinfo(
                    "Restore Complete",
                    f"Successfully restored {restored_count} backup(s)."
                )
                
                # Refresh the file tree to show restored files
                self.browse_and_load_folder()
            else:
                messagebox.showwarning(
                    "Restore Failed",
                    "Failed to restore any backups. Check logs for details."
                )
            
        except (OSError, IOError, shutil.Error) as e:
            logger.error(f"Error restoring backups: {e}")
            messagebox.showerror(
                "Restore Error",
                f"An error occurred while restoring backups:\n\n{str(e)}"
            )