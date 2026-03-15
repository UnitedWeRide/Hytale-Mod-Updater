"""
Main Application Window (Stripped Version)

This module handles the main application window setup and UI creation
for the Hytale Mod Updater.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Dict, Any, Optional
from pathlib import Path

import logging

logger = logging.getLogger(__name__)


class AppWindow:
    """Main application window setup and UI creation (Stripped)."""
    
    def __init__(self, root: tk.Tk, app_instance):
        """
        Initialize the application window.
        
        Args:
            root: Tk root window
            app_instance: The main application instance
        """
        self.root = root
        self.app = app_instance
        self.main_frame: Optional[ttk.Frame] = None
        self.file_loader_frame: Optional[ttk.LabelFrame] = None
        self.file_tree: Optional[ttk.Treeview] = None
        self.file_scrollbar: Optional[ttk.Scrollbar] = None
        self.clear_button: Optional[ttk.Button] = None
        self.progress_frame: Optional[ttk.Frame] = None
        self.progress_label: Optional[ttk.Label] = None
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.mod_count_label: Optional[ttk.Label] = None
        self.kofi_button_frame: Optional[tk.Frame] = None
        self.kofi_button_image: Optional[tk.PhotoImage] = None
        self.kofi_button: Optional[tk.Button] = None
        
    def setup_window(self):
        """Configure the main window properties."""
        self.root.title("Hytale Mod Updater")
        self.root.minsize(600, 400)
        self.root.geometry("800x500")
        self.root.resizable(True, True)
        
        # Configure grid weights for better resizing behavior
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
    def create_ui(self):
        """Create the main user interface."""
        # Main frame with grid layout
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.main_frame.grid_rowconfigure(0, weight=0)  # Header
        self.main_frame.grid_rowconfigure(1, weight=0)  # Mod directory
        self.main_frame.grid_rowconfigure(2, weight=0)  # Load file buttons
        self.main_frame.grid_rowconfigure(3, weight=0)  # Progress section
        self.main_frame.grid_rowconfigure(4, weight=1)  # File browser (expandable)
        self.main_frame.grid_rowconfigure(5, weight=0)  # Update buttons
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Create UI sections - header, mod directory, file browser, progress, and update buttons
        self._create_header()
        self._create_mod_directory_section()
        self._create_file_browser_section()
        self._create_progress_section()
        self._create_update_buttons_section()
        self._create_kofi_button()
        
    def _create_header(self):
        """Create the header section with title and settings button."""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(header_frame, text="Hytale Mod Updater", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)
        
        settings_button = ttk.Button(header_frame, text="Settings", command=self.app.open_settings)
        settings_button.pack(side=tk.RIGHT)
        
    def _create_mod_directory_section(self):
        """Create the mod directory selection section."""
        dir_frame = ttk.Frame(self.main_frame)
        dir_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(dir_frame, text="Mod Directory:").pack(side=tk.LEFT)
        
        self.mod_dir_entry = ttk.Entry(dir_frame, width=60)
        self.mod_dir_entry.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        self.mod_dir_entry.insert(0, self.app.settings.get("mod_directory", ""))
        
        # Browse Folder button - moved here from row 2
        self.load_folder_button = ttk.Button(
            dir_frame,
            text="Browse Folder (.zip/.jar)",
            command=self.app.browse_and_load_folder
        )
        self.load_folder_button.pack(side=tk.LEFT, padx=(5, 0))
    
    def _create_file_browser_section(self):
        """Create the file browser section with treeview for .zip/.jar files."""
        # File browser frame
        self.file_loader_frame = ttk.LabelFrame(self.main_frame, text="File Browser (.zip/.jar)")
        self.file_loader_frame.grid(row=4, column=0, sticky="nsew", pady=(10, 0))
        
        # Configure grid weights for file browser frame
        self.file_loader_frame.grid_rowconfigure(0, weight=1)
        self.file_loader_frame.grid_columnconfigure(0, weight=1)
        
        # Create treeview with scrollbar
        self.file_scrollbar = ttk.Scrollbar(self.file_loader_frame)
        self.file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_tree = ttk.Treeview(
            self.file_loader_frame,
            columns=("mod_id", "fingerprint"),
            show="tree",
            yscrollcommand=self.file_scrollbar.set
        )
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        self.file_scrollbar.config(command=self.file_tree.yview)
        
        # Configure tree columns
        self.file_tree.column("#0", width=200, minwidth=100)
        self.file_tree.column("mod_id", width=80, minwidth=50, anchor=tk.E)
        self.file_tree.column("fingerprint", width=100, minwidth=80, anchor=tk.E)
        
        # Configure heading
        self.file_tree.heading("#0", text="Name", anchor=tk.W)
        self.file_tree.heading("mod_id", text="Mod ID", anchor=tk.E)
        self.file_tree.heading("fingerprint", text="Fingerprint", anchor=tk.E)
        
        # Bind selection event
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_select)
        
        # Clear button - moved to row 2
        clear_button_frame = ttk.Frame(self.main_frame)
        clear_button_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        
        self.clear_button = ttk.Button(
            clear_button_frame,
            text="Clear",
            command=self.clear_file_tree
        )
        self.clear_button.pack(side=tk.LEFT)
    
    def _create_update_buttons_section(self):
        """Create the update detection buttons section."""
        # Update detection buttons
        update_button_frame = ttk.Frame(self.main_frame)
        update_button_frame.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        
        self.check_updates_button = ttk.Button(
            update_button_frame,
            text="Check for Updates",
            command=self.app.check_for_updates
        )
        self.check_updates_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.download_button = ttk.Button(
            update_button_frame,
            text="Download Outdated Mods",
            command=self.app.download_outdated_mods
        )
        self.download_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.restore_backups_button = ttk.Button(
            update_button_frame,
            text="Restore Backups",
            command=self.app.restore_backups
        )
        self.restore_backups_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.refresh_db_button = ttk.Button(
            update_button_frame,
            text="Refresh Database",
            command=self.app.refresh_database
        )
        self.refresh_db_button.pack(side=tk.LEFT, padx=(0, 5))
    
    def _create_kofi_button(self):
        """Create the Ko-fi button in the bottom right corner."""
        # Create a frame for the Ko-fi button (absolute positioning)
        self.kofi_button_frame = tk.Frame(self.root)
        self.kofi_button_frame.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)
        
        # Load the Ko-fi button image
        kofi_image_path = self.app.path_manager.resolve_resource_path("kofi_button.png")
        original_image = tk.PhotoImage(file=kofi_image_path)
        
        # Resize the image to fit better with other buttons.
        # Use subsample to reduce image size (larger factor = smaller result)
        x_factor = max(1, int(original_image.width() / 148))
        y_factor = max(1, int(original_image.height() / 30))
        resized_image = original_image.subsample(int(x_factor or 1), int(y_factor or 1))  # type: ignore[arg-type]
        
        # Create the Ko-fi button with the resized image
        self.kofi_button_image = resized_image
        self.kofi_button = tk.Button(
            self.kofi_button_frame,
            image=self.kofi_button_image,
            command=self._open_kofi_link,
            bd=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2"
        )
        self.kofi_button.pack()
    
    def _open_kofi_link(self):
        """Open the Ko-fi link in the default browser."""
        import webbrowser
        webbrowser.open("https://ko-fi.com/unitedweride")
    
    def _create_progress_section(self):
        """Create the progress section for displaying loading progress."""
        self.progress_frame = ttk.Frame(self.main_frame)
        self.progress_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        
        # Configure grid weights
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress label
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode="determinate",
            maximum=100
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        
        # Mod count label (shows loaded count and database count)
        self.mod_count_label = ttk.Label(self.progress_frame, text="Loaded: 0 | Database: 0")
        self.mod_count_label.grid(row=2, column=0, sticky="w", pady=(5, 0))
    
    def update_progress(self, text: str, value: float, maximum: float = 100):
        """
        Update the progress bar display.
        
        Args:
            text: Progress text to display
            value: Current progress value
            maximum: Maximum progress value (default 100)
        """
        # Ensure UI updates happen on the main thread
        def update_ui():
            if self.progress_label:
                self.progress_label.config(text=text)
            if self.progress_bar:
                self.progress_bar.config(maximum=maximum)
                self.progress_bar.config(value=value)
                logger.debug(f"Progress updated: {text} (value={value}, max={maximum})")
                self.progress_bar.update_idletasks()
        
        # Use root.after to marshal UI updates to the main thread
        if hasattr(self, 'root') and self.root:
            self.root.after(0, update_ui)
        else:
            # Fallback: call directly if root is not available
            update_ui()
    
    def clear_progress(self):
        """Clear the progress bar display."""
        def clear_ui():
            if self.progress_label:
                self.progress_label.config(text="")
            if self.progress_bar:
                # Stop indeterminate animation if running
                self.progress_bar.stop()
                # Reset to determinate mode
                self.progress_bar.config(mode="determinate")
                self.progress_bar.config(value=0)
                self.progress_bar.update_idletasks()
            if self.mod_count_label:
                self.mod_count_label.config(text="Loaded: 0 | Database: 0")
        
        # Use root.after to marshal UI updates to the main thread
        if hasattr(self, 'root') and self.root:
            self.root.after(0, clear_ui)
        else:
            # Fallback: call directly if root is not available
            clear_ui()
    
    def set_indeterminate_progress(self, text: str = "Downloading updates..."):
        """
        Set the progress bar to indeterminate mode (spinning) for long-running operations.
        
        Args:
            text: Progress text to display (default: "Downloading updates...")
        """
        def set_ui():
            if self.progress_label:
                self.progress_label.config(text=text)
            if self.progress_bar:
                # Switch to indeterminate mode for continuous animation
                self.progress_bar.config(mode="indeterminate")
                self.progress_bar.start(200)  # Start animation with 200ms interval
                self.progress_bar.update_idletasks()
        
        # Use root.after to marshal UI updates to the main thread
        if hasattr(self, 'root') and self.root:
            self.root.after(0, set_ui)
        else:
            # Fallback: call directly if root is not available
            set_ui()
    
    def clear_progress_without_mod_count(self):
        """Clear the progress bar display without resetting mod count."""
        def clear_ui():
            if self.progress_label:
                self.progress_label.config(text="")
            if self.progress_bar:
                self.progress_bar.config(value=0)
                self.progress_bar.update_idletasks()
        
        # Use root.after to marshal UI updates to the main thread
        if hasattr(self, 'root') and self.root:
            self.root.after(0, clear_ui)
        else:
            # Fallback: call directly if root is not available
            clear_ui()
    
    def update_mod_count(self, loaded_count: int, database_count: int, curseforge_total: Optional[int] = None):
        """
        Update the mod count display.
        
        Args:
            loaded_count: Number of mods currently loaded in file tree
            database_count: Number of mods in the database
            curseforge_total: Optional total mods count from CurseForge API
        """
        if self.mod_count_label:
            if curseforge_total is not None:
                self.mod_count_label.config(text=f"Loaded: {loaded_count} | Database: {database_count} | CurseForge: {curseforge_total}")
            else:
                self.mod_count_label.config(text=f"Loaded: {loaded_count} | Database: {database_count}")
    
    def _on_file_select(self, _event):
        """Handle file treeview selection event."""
        if not self.file_tree:
            return
        selection = self.file_tree.selection()
        if selection:
            item = selection[0]
            values = self.file_tree.item(item, "values")
            logger.debug(f"Selected file item: {item}, values: {values}")
    
    def clear_file_tree(self):
        """Clear all items from the file treeview and clear the mod ID cache."""
        logger.info("clear_file_tree: Starting")
        if self.file_tree:
            children = self.file_tree.get_children()
            logger.info(f"clear_file_tree: children type: {type(children)}, length: {len(children)}")
            for item in children:
                logger.info(f"clear_file_tree: Deleting item: {item}, type: {type(item)}")
                self.file_tree.delete(item)
        
        # Reset mod count display
        database_count = 0
        if hasattr(self, 'app') and self.app and hasattr(self.app, 'mod_database_manager') and self.app.mod_database_manager:
            database_count = self.app.mod_database_manager.get_mod_count()
        self.update_mod_count(0, database_count)
        
        logger.info("clear_file_tree: Completed")
    
    def populate_file_tree(self, contents):
        """
        Populate the file treeview with contents.
        
        Args:
            contents: List of tuples (path, mod_id, is_dir, fingerprint) or (path, mod_id, is_dir, fingerprint, file_path)
        """
        if not self.file_tree:
            return
        
        # Clear existing items
        self.clear_file_tree()
        
        # Group items by directory structure
        items_by_path = {}
        
        for item in contents:
            # Handle both 4-tuple and 5-tuple formats
            if len(item) == 5:
                path, mod_id, is_dir, fingerprint, _ = item
            else:
                path, mod_id, is_dir, fingerprint = item
            # Split path into components
            parts = path.split('/')
            
            # Build hierarchical structure
            current_path = ""
            parent_id = ""
            
            for i, part in enumerate(parts):
                if not part:  # Skip empty parts
                    continue
                
                current_path = f"{current_path}/{part}" if current_path else part
                
                # Check if this item already exists
                if current_path in items_by_path:
                    parent_id = items_by_path[current_path]
                else:
                    # Determine if this is the last part (the actual file)
                    is_leaf = (i == len(parts) - 1)
                    
                    # Create the item
                    if is_leaf and not is_dir:
                        # File item - format mod_id
                        formatted_mod_id = self._format_mod_id(mod_id)
                        
                        # Only show fingerprint for the top-level zip/jar file itself
                        # The path format is "zipname/entry1", "zipname/entry2", etc.
                        # We only show fingerprint when there's exactly one part (the zip file)
                        if len(parts) == 1:
                            formatted_fingerprint = self._format_fingerprint(fingerprint)
                        else:
                            formatted_fingerprint = ""
                        
                        item_id = self.file_tree.insert(
                            parent_id,
                            tk.END,
                            text=part,
                            values=(formatted_mod_id, formatted_fingerprint),
                            tags=("file",)
                        )
                    else:
                        # Directory item
                        item_id = self.file_tree.insert(
                            parent_id,
                            tk.END,
                            text=part,
                            values=(),
                            tags=("directory",)
                        )
                    
                    items_by_path[current_path] = item_id
                    parent_id = item_id
    
    def _format_optional_int(self, value: Optional[int]) -> str:
        """
        Format an optional integer for display.
        
        Args:
            value: The integer value
            
        Returns:
            Formatted string (e.g., "123456") or "N/A" if None
        """
        if value is None:
            return "N/A"
        return str(value)
    
    def _format_mod_id(self, mod_id: Optional[int]) -> str:
        """
        Format the mod ID for display.
        
        Args:
            mod_id: The mod ID integer
            
        Returns:
            Formatted mod ID string (e.g., "123456") or "N/A" if None
        """
        return self._format_optional_int(mod_id)
    
    def _format_fingerprint(self, fingerprint: Optional[int]) -> str:
        """
        Format the fingerprint as a decimal string for display.
        
        Args:
            fingerprint: The 32-bit fingerprint integer
            
        Returns:
            Formatted decimal string (e.g., "865597533") or "N/A" if None
        """
        return self._format_optional_int(fingerprint)
    
    def populate_file_tree_with_updates(self, contents, outdated_mod_ids):
        """
        Populate the file treeview with contents and update status.
        
        Args:
            contents: List of tuples (path, mod_id, is_dir, fingerprint)
            outdated_mod_ids: Set of outdated mod IDs
        """
        logger.info("populate_file_tree_with_updates: Entry")
        if not self.file_tree:
            logger.info("populate_file_tree_with_updates: file_tree is None, returning")
            return
        logger.info("populate_file_tree_with_updates: file_tree is valid")
        
        # Clear existing items
        self.clear_file_tree()
        
        # Configure tags for outdated mods (red background)
        self.file_tree.tag_configure("outdated", background="lightcoral")
        
        # Group items by directory structure
        items_by_path = {}
        
        logger.info(f"populate_file_tree_with_updates: contents type: {type(contents)}, length: {len(contents)}")
        if contents:
            logger.info(f"populate_file_tree_with_updates: First item type: {type(contents[0])}, value: {contents[0]}")
        
        for item in contents:
            # Handle both 4-tuple and 5-tuple formats
            if len(item) == 5:
                path, mod_id, is_dir, fingerprint, _ = item
            else:
                path, mod_id, is_dir, fingerprint = item
            # Split path into components
            parts = path.split('/')
            
            # Build hierarchical structure
            current_path = ""
            parent_id = ""
            
            for i, part in enumerate(parts):
                if not part:  # Skip empty parts
                    continue
                
                current_path = f"{current_path}/{part}" if current_path else part
                
                # Check if this item already exists
                if current_path in items_by_path:
                    parent_id = items_by_path[current_path]
                else:
                    # Determine if this is the last part (the actual file)
                    is_leaf = (i == len(parts) - 1)
                    
                    # Create the item
                    if is_leaf and not is_dir:
                        # File item - format mod_id
                        formatted_mod_id = self._format_mod_id(mod_id)
                        
                        # Only show fingerprint for the top-level zip/jar file itself
                        if len(parts) == 1:
                            formatted_fingerprint = self._format_fingerprint(fingerprint)
                        else:
                            formatted_fingerprint = ""
                        
                        # Determine if this mod is outdated
                        tags = ["file"]
                        if mod_id in outdated_mod_ids:
                            tags.append("outdated")
                        
                        item_id = self.file_tree.insert(
                            parent_id,
                            tk.END,
                            text=part,
                            values=(formatted_mod_id, formatted_fingerprint),
                            tags=tags
                        )
                    else:
                        # Directory item
                        item_id = self.file_tree.insert(
                            parent_id,
                            tk.END,
                            text=part,
                            values=(),
                            tags=("directory",)
                        )
                    
                    items_by_path[current_path] = item_id
                    parent_id = item_id
        
        # Update mod count display after repopulating
        # Count only top-level files (entries without "/" in path - the actual zip/jar files)
        top_level_file_count = sum(1 for item in contents if '/' not in item[0])
        database_count = 0
        if hasattr(self, 'app') and self.app and hasattr(self.app, 'mod_database_manager') and self.app.mod_database_manager:
            database_count = self.app.mod_database_manager.get_mod_count()
        self.update_mod_count(top_level_file_count, database_count)