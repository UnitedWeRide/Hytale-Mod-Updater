"""
UI Dialogs (Stripped Version)

This module provides dialog windows for the Hytale Mod Updater.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, List, Optional
from pathlib import Path

import logging

logger = logging.getLogger(__name__)


class APIKeyDialog:
    """Modal dialog for API key input and saving (Stripped)."""
    
    def __init__(self, parent: tk.Tk, is_first_run: bool = False):
        """
        Initialize the API key dialog.
        
        Args:
            parent: Parent window
            is_first_run: If True, shows enhanced first-run instructions
        """
        self.parent = parent
        self.is_first_run = is_first_run
        self.api_key: Optional[str] = None
        self.dialog: Optional[tk.Toplevel] = None
        self.validated: bool = False
    
    def show(self) -> Optional[str]:
        """Show the API key dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("CurseForge API Key")
        self.dialog.minsize(400, 200)
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Create UI
        self._create_ui()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.api_key if self.validated else None
    
    def _create_ui(self):
        """Create dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="CurseForge API Key",
            font=("Helvetica", 14, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Instructions
        if self.is_first_run:
            instructions_text = (
                "Welcome to Hytale Mod Updater!\n\n"
                "To access the CurseForge mod database, you need an API key.\n"
                "This is free and easy to obtain from the CurseForge for Studios console.\n\n"
                "1. Visit https://console.curseforge.com/\n"
                "2. Sign in with your CurseForge account\n"
                "3. Click \"Create New API Key\"\n"
                "4. Copy the key and paste it below\n\n"
                "The key will be saved securely to your system keyring and never shared."
            )
        else:
            instructions_text = (
                "Please enter your CurseForge API key.\n"
                "You can get one from the CurseForge for Studios console.\n"
                "The key will be saved securely to your system keyring."
            )
        
        instructions = ttk.Label(
            main_frame,
            text=instructions_text,
            wraplength=400,
            justify=tk.CENTER
        )
        instructions.pack(pady=(0, 15))
        
        # API Key Entry
        entry_frame = ttk.Frame(main_frame)
        entry_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(entry_frame, text="API Key:").pack(side=tk.LEFT)
        
        self.api_key_entry = ttk.Entry(entry_frame, width=40, show="*")
        self.api_key_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Show/Hide toggle
        self.show_var = tk.BooleanVar(value=False)
        show_check = ttk.Checkbutton(
            entry_frame,
            text="Show",
            variable=self.show_var,
            command=self._toggle_visibility
        )
        show_check.pack(side=tk.LEFT, padx=(5, 0))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="", foreground="#ff6b6b")
        self.status_label.pack(pady=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self._save_and_close
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=lambda: self.dialog.destroy() if self.dialog else None
        ).pack(side=tk.LEFT)
        
        # Link to CurseForge
        link_label = ttk.Label(
            main_frame,
            text="Get API Key from CurseForge",
            foreground="#6b8cff",
            cursor="hand2"
        )
        link_label.pack(pady=(15, 0))
        link_label.bind("<Button-1>", lambda e: self._open_curseforge_console())
        
        # Focus on entry
        self.api_key_entry.focus_set()
    
    def _toggle_visibility(self):
        """Toggle password visibility."""
        show = self.show_var.get()
        self.api_key_entry.config(show="" if show else "*")
    
    def _open_curseforge_console(self):
        """Open CurseForge console in browser."""
        import webbrowser
        webbrowser.open("https://console.curseforge.com/")
    
    def _save_and_close(self):
        """Save API key to keyring and close dialog."""
        api_key = self.api_key_entry.get().strip()
        
        if not api_key:
            self.status_label.config(text="API key cannot be empty", foreground="#ff6b6b")
            return
        
        # Validate API key format (basic check - should be 32+ hex characters)
        if len(api_key) < 32:
            self.status_label.config(
                text="Invalid API key format. Expected at least 32 characters.",
                foreground="#ff6b6b"
            )
            return
        
        # Try to validate with CurseForge API
        self.status_label.config(text="Validating API key...", foreground="#6b8cff")
        if self.dialog:
            self.dialog.update_idletasks()  # type: ignore  # Update UI to show validation message
        
        try:
            from services.curseforge_api import CurseForgeAPI
            api = CurseForgeAPI(api_key, rate_limit_enabled=True)
            
            # Try a simple API call to validate the key
            result = api.search_mods_by_game(
                game_id=70216,  # Hytale
                index=0,
                page_size=1
            )
            
            if result is None:
                self.status_label.config(
                    text="Failed to validate API key. Please check if it's correct.",
                    foreground="#ff6b6b"
                )
                return
            
            # Save to keyring
            from services.keyring_manager import KeyringManager
            if KeyringManager.set_api_key(api_key):
                self.api_key = api_key
                self.validated = True
                if self.dialog:
                    self.dialog.destroy()  # type: ignore
            else:
                self.status_label.config(text="Failed to save API key", foreground="#ff6b6b")
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            self.status_label.config(
                text=f"Validation failed: {str(e)}",
                foreground="#ff6b6b"
            )


class UpdatesDialog:
    """Modal dialog for displaying available updates with scrollable content."""
    
    def __init__(self, parent: tk.Tk, app_instance, outdated_mods: List[Dict[str, Any]]):
        """
        Initialize the updates dialog.
        
        Args:
            parent: Parent window
            app_instance: The main application instance (for theme access)
            outdated_mods: List of outdated mod dictionaries
        """
        self.parent = parent
        self.app = app_instance
        self.outdated_mods = outdated_mods
        self.dialog: Optional[tk.Toplevel] = None
    
    def show(self):
        """Show the updates dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Updates Available")
        self.dialog.minsize(500, 300)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Apply theme if available
        if hasattr(self.app, 'theme_manager') and self.app.theme_manager:
            try:
                self.app.theme_manager.apply_theme(self.dialog, theme_mode="auto")
            except Exception as e:
                logger.warning(f"Failed to apply theme to updates dialog: {e}")
        
        # Create UI first to get actual content size
        self._create_ui()
        
        # Update to get actual dialog size after UI is created
        self.dialog.update_idletasks()
        
        # Center the dialog
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def _create_ui(self):
        """Create dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="Updates Available",
            font=("Helvetica", 14, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Subtitle
        subtitle = ttk.Label(
            main_frame,
            text=f"Found {len(self.outdated_mods)} mod(s) with available updates",
            foreground="#666"
        )
        subtitle.pack(pady=(0, 15))
        
        # Scrollable text frame
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create text widget with scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget = tk.Text(
            text_frame,
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            padx=10,
            pady=10,
            state=tk.DISABLED
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_widget.yview)
        
        # Populate text widget with update information
        self._populate_text()
        
        # Buttons - use grid for better layout control
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        close_button = ttk.Button(
            button_frame,
            text="Close",
            command=lambda: self.dialog.destroy() if self.dialog else None
        )
        close_button.pack(side=tk.RIGHT)
    
    def _populate_text(self):
        """Populate the text widget with update information."""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        
        for mod in self.outdated_mods:
            # Safely access mod properties with type checking
            if isinstance(mod, dict):
                file_name = mod.get('file_name', 'Unknown')
                mod_id = mod.get('mod_id', 'Unknown')
                local_fingerprint = mod.get('local_fingerprint', 'Unknown')
                latest_fingerprint = mod.get('latest_fingerprint', 'Unknown')
                
                self.text_widget.insert(tk.END, f"- {file_name}\n")
                self.text_widget.insert(tk.END, f"  Mod ID: {mod_id}\n")
                self.text_widget.insert(tk.END, f"  Local fingerprint: {local_fingerprint}\n")
                self.text_widget.insert(tk.END, f"  Latest fingerprint: {latest_fingerprint}\n\n")
            else:
                self.text_widget.insert(tk.END, f"- Unknown mod (type: {type(mod)})\n\n")
        
        self.text_widget.config(state=tk.DISABLED)


class BackupOptionsDialog:
    """Modal dialog for selecting backup options for outdated mods."""
    
    def __init__(self, parent: tk.Tk, outdated_mods: List[Dict[str, Any]]):
        """
        Initialize the backup options dialog.
        
        Args:
            parent: Parent window
            outdated_mods: List of outdated mod dictionaries
        """
        self.parent = parent
        self.outdated_mods = outdated_mods
        self.dialog: Optional[tk.Toplevel] = None
        self.choice: Optional[str] = None  # 'backup', 'recycle', 'delete'
    
    def show(self) -> Optional[str]:
        """Show the backup options dialog and return the user's choice."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Backup Options")
        self.dialog.minsize(400, 300)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Create UI
        self._create_ui()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.choice
    
    def _create_ui(self):
        """Create dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="Backup Options",
            font=("Helvetica", 14, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Subtitle
        subtitle = ttk.Label(
            main_frame,
            text=f"Select an option for {len(self.outdated_mods)} mod(s)",
            foreground="#666"
        )
        subtitle.pack(pady=(0, 20))
        
        # Options
        self.choice_var = tk.StringVar(value="backup")
        
        backup_radio = ttk.Radiobutton(
            main_frame,
            text="Backup to folder",
            variable=self.choice_var,
            value="backup"
        )
        backup_radio.pack(anchor=tk.W, pady=(5, 0))
        
        recycle_radio = ttk.Radiobutton(
            main_frame,
            text="Move to Recycle Bin",
            variable=self.choice_var,
            value="recycle"
        )
        recycle_radio.pack(anchor=tk.W, pady=(5, 0))
        
        delete_radio = ttk.Radiobutton(
            main_frame,
            text="Delete permanently",
            variable=self.choice_var,
            value="delete"
        )
        delete_radio.pack(anchor=tk.W, pady=(5, 0))
        
        # Warning label
        warning_label = ttk.Label(
            main_frame,
            text="Backup is recommended to prevent data loss",
            foreground="#ffa500"
        )
        warning_label.pack(pady=(15, 10))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="Confirm",
            command=self._confirm_choice
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=lambda: self.dialog.destroy() if self.dialog else None
        ).pack(side=tk.LEFT)
    
    def _confirm_choice(self):
        """Confirm the selected backup option."""
        self.choice = self.choice_var.get()
        if self.dialog:
            self.dialog.destroy()  # type: ignore


class GameSelectionDialog:
    """Modal dialog for selecting a different game."""
    
    def __init__(self, parent: tk.Tk, app_instance):
        """
        Initialize the game selection dialog.
        
        Args:
            parent: Parent window
            app_instance: The main application instance
        """
        self.parent = parent
        self.app = app_instance
        self.dialog: Optional[tk.Toplevel] = None
        self.selected_game: Optional[Dict[str, Any]] = None
    
    def show(self) -> Optional[Dict[str, Any]]:
        """Show the game selection dialog and return the selected game."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Select Game")
        self.dialog.minsize(400, 300)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Create UI
        self._create_ui()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.selected_game
    
    def _create_ui(self):
        """Create dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="Select Game",
            font=("Helvetica", 14, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Game list
        games = [
            {"id": 70216, "name": "Hytale"},
            {"id": 433623, "name": "Minecraft: Java Edition"},
            {"id": 306692, "name": "RimWorld"},
            {"id": 251570, "name": "Factorio"},
        ]
        
        self.game_var = tk.StringVar(value=str(self.app.settings.get("game_id", 70216)))
        
        for game in games:
            radio = ttk.Radiobutton(
                main_frame,
                text=f"{game['name']} (ID: {game['id']})",
                variable=self.game_var,
                value=str(game['id'])
            )
            radio.pack(anchor=tk.W, pady=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(
            button_frame,
            text="Select",
            command=self._select_game
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=lambda: self.dialog.destroy() if self.dialog else None
        ).pack(side=tk.LEFT)
    
    def _select_game(self):
        """Confirm the selected game."""
        game_id = int(self.game_var.get())
        games = [
            {"id": 70216, "name": "Hytale"},
            {"id": 433623, "name": "Minecraft: Java Edition"},
            {"id": 251570, "name": "Factorio"},
        ]
        
        for game in games:
            if game['id'] == game_id:
                self.selected_game = game
                break
        
        if self.dialog:
            self.dialog.destroy()  # type: ignore


class RestoreBackupsDialog:
    """Modal dialog for selecting backups to restore."""
    
    def __init__(self, parent: tk.Tk, backup_list: List[Dict[str, Any]]):
        """
        Initialize the restore backups dialog.
        
        Args:
            parent: Parent window
            backup_list: List of backup file information dictionaries
        """
        self.parent = parent
        self.backup_list = backup_list
        self.dialog: Optional[tk.Toplevel] = None
        self.selected_backups: List[str] = []
        self.canvas: Optional[tk.Canvas] = None
        self.dialog_active: bool = True
    
    def show(self) -> List[str]:
        """Show the restore backups dialog and return selected backup paths."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Restore Backups")
        self.dialog.minsize(500, 400)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Create UI
        self._create_ui()
        
        # Bind cleanup on dialog destroy
        self.dialog.bind("<Destroy>", self._cleanup)
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.selected_backups
    
    def _create_ui(self):
        """Create dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="Restore Backups",
            font=("Helvetica", 14, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Subtitle
        subtitle = ttk.Label(
            main_frame,
            text=f"Select backup files to restore ({len(self.backup_list)} found)",
            foreground="#666"
        )
        subtitle.pack(pady=(0, 15))
        
        # Backup list with checkboxes
        self.backup_vars = {}
        scroll_frame = ttk.Frame(main_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        canvas = tk.Canvas(scroll_frame)
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        self.backup_list_frame = ttk.Frame(canvas)
        
        self.backup_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.backup_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Store canvas reference for scroll wheel binding
        self.canvas = canvas
        
        # Bind scroll wheel for scrolling with mouse wheel
        canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        canvas.bind_all("<Button-4>", self._on_mouse_wheel)  # Linux scroll up
        canvas.bind_all("<Button-5>", self._on_mouse_wheel)  # Linux scroll down
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for backup in self.backup_list:
            var = tk.BooleanVar(value=False)
            self.backup_vars[backup["backup_path"]] = var
            
            backup_frame = ttk.Frame(self.backup_list_frame)
            backup_frame.pack(fill=tk.X, pady=(5, 0))
            
            ttk.Checkbutton(
                backup_frame,
                text=f"{backup['original_name']}",
                variable=var,
                command=lambda bp=backup["backup_path"]: self._on_backup_selected(bp)
            ).pack(side=tk.LEFT)
            
            ttk.Label(
                backup_frame,
                text=f"Backup date: {backup['backup_date']}"
            ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="Restore Selected",
            command=self._restore_selected
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=lambda: self.dialog.destroy() if self.dialog else None
        ).pack(side=tk.LEFT)
    
    def _on_backup_selected(self, backup_path: str):
        """Handle backup selection change."""
        if self.backup_vars[backup_path].get():
            if backup_path not in self.selected_backups:
                self.selected_backups.append(backup_path)
        else:
            if backup_path in self.selected_backups:
                self.selected_backups.remove(backup_path)
    
    def _cleanup(self, event: Optional[tk.Event] = None) -> None:
        """Clean up event bindings when dialog is destroyed."""
        # Mark dialog as inactive to prevent scroll events from being processed
        self.dialog_active = False
    
    def _on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling for the canvas."""
        # Check if dialog is still active
        if not getattr(self, 'dialog_active', True):
            return
        
        canvas = getattr(self, 'canvas', None)
        if canvas:
            # Check if canvas widget still exists (not destroyed)
            try:
                # Windows/Mac: event.delta is in multiples of 120
                # Linux: event.num is 4 (up) or 5 (down)
                if event.num == 5 or event.delta < 0:
                    canvas.yview_scroll(1, "units")
                else:
                    canvas.yview_scroll(-1, "units")
            except tk.TclError:
                # Canvas has been destroyed, ignore scroll event
                pass
    
    def _restore_selected(self):
        """Confirm selected backups for restore."""
        if not self.selected_backups:
            messagebox.showwarning("No Selection", "Please select at least one backup to restore.")
            return
        if self.dialog:
            self.dialog.destroy()  # type: ignore


class DownloadCompleteDialog:
    """Modal dialog for displaying download completion status with theme applied."""
    
    def __init__(self, parent: tk.Tk, app_instance, success_count: int, failed_count: int, failed_mods: List[Dict[str, Any]], error_message: str = "", directory_path: Optional[Path] = None):
        """
        Initialize the download complete dialog.
        
        Args:
            parent: Parent window
            app_instance: The main application instance (for theme access)
            success_count: Number of successful downloads
            failed_count: Number of failed downloads
            failed_mods: List of failed mod info dictionaries with keys: mod_id, filename, error_message, download_url
            error_message: Optional error message from API (e.g., "Invalid API key or insufficient permissions")
            directory_path: Optional path to the mod directory for applying actions
        """
        self.parent = parent
        self.app = app_instance
        self.success_count = success_count
        self.failed_count = failed_count
        self.failed_mods = failed_mods
        self.error_message = error_message
        self.dialog: Optional[tk.Toplevel] = None
        self.directory_path = directory_path
        self.selected_options: Dict[str, tk.StringVar] = {}  # filename -> option variable (backup, recycle, delete)
    
    def show(self):
        """Show the download complete dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Download Complete")
        self.dialog.minsize(500, 300)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Apply theme if available
        if hasattr(self.app, 'theme_manager') and self.app.theme_manager:
            try:
                self.app.theme_manager.apply_theme(self.dialog, theme_mode="auto")
            except Exception as e:
                logger.warning(f"Failed to apply theme to download complete dialog: {e}")
        
        # Create UI first to get actual content size
        self._create_ui()
        
        # Update to get actual dialog size after UI is created
        self.dialog.update_idletasks()
        
        # Center the dialog
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def _apply_action_to_failed_file(self, filename: str, option: str, failed_file_path: Path, backup_manager: Any) -> None:
        """Apply a single action to a failed mod file.
        
        Args:
            filename: Name of the file
            option: Action option ("recycle", "delete", or "backup")
            failed_file_path: Path to the failed file
            backup_manager: BackupManager instance
        """
        if option == "recycle":
            backup_manager.move_to_recycle_bin(failed_file_path)
            logger.info(f"Moved failed mod to recycle bin: {filename}")
        elif option == "delete":
            backup_manager.permanently_delete(failed_file_path)
            logger.info(f"Permanently deleted failed mod: {filename}")
        elif option == "backup":
            # Create a new backup of the restored failed file
            if failed_file_path.exists():
                backup_path = backup_manager.create_backup(failed_file_path)
                if backup_path:
                    logger.info(f"Created backup for failed mod: {filename} -> {backup_path}")
                else:
                    logger.error(f"Failed to create backup for failed mod: {filename}")
            else:
                logger.warning(f"File not found for backup: {filename}")
    
    def _create_ui(self):
        """Create dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="Download Complete",
            font=("Helvetica", 14, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Status summary
        if self.success_count > 0:
            success_text = f"Successfully downloaded {self.success_count} mod(s)"
            success_label = ttk.Label(main_frame, text=success_text, foreground="#4caf50")
            success_label.pack(pady=(0, 5))
        
        if self.failed_count > 0:
            failed_text = f"Failed to download {self.failed_count} mod(s)"
            failed_label = ttk.Label(main_frame, text=failed_text, foreground="#f44336")
            failed_label.pack(pady=(0, 5))
            
            # API failure reason message with actual error if available
            if self.error_message:
                reason_label = ttk.Label(
                    main_frame,
                    text=f"API Error: {self.error_message}",
                    foreground="#ff9800",
                    wraplength=450,
                    justify=tk.CENTER
                )
            else:
                reason_label = ttk.Label(
                    main_frame,
                    text="These mods could not be downloaded due to API response errors. "
                         "Please check your API key and try again, or download them manually.",
                    foreground="#ff9800",
                    wraplength=450,
                    justify=tk.CENTER
                )
            reason_label.pack(pady=(5, 10))
            
            # Failed mods list with manual download buttons
            if self.failed_mods:
                failed_frame = ttk.LabelFrame(main_frame, text="Failed Mods")
                failed_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
                
                # Create a canvas with scrollbar for failed mods
                canvas_frame = ttk.Frame(failed_frame)
                canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                canvas = tk.Canvas(canvas_frame, highlightthickness=0)
                scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
                scrollable_frame = ttk.Frame(canvas)
                
                scrollable_frame.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                
                # Bind mouse wheel events to canvas for scrolling
                def _on_mouse_wheel(event):
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                
                canvas.bind("<MouseWheel>", _on_mouse_wheel)
                scrollable_frame.bind("<MouseWheel>", _on_mouse_wheel)
                
                canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Add failed mods with manual download buttons
                for i, mod_info in enumerate(self.failed_mods):
                    mod_frame = ttk.Frame(scrollable_frame)
                    mod_frame.pack(fill=tk.X, pady=5)
                    
                    # Mod filename
                    filename = mod_info.get("filename", "Unknown")
                    filename_label = ttk.Label(mod_frame, text=filename, font=("Helvetica", 10, "bold"))
                    filename_label.pack(anchor=tk.W)
                    
                    # Error message
                    error_message = mod_info.get("error_message", "Unknown error")
                    error_label = ttk.Label(mod_frame, text=f"Error: {error_message}", foreground="#f44336")
                    error_label.pack(anchor=tk.W)
                    
                    # Manual download button
                    download_url = mod_info.get("download_url")
                    if download_url:
                        # Convert /files/ URL to /download/ URL for manual download
                        manual_download_url = download_url.replace("/files/", "/download/")
                        
                        def open_manual_download(url=manual_download_url):
                            """Open the download URL in the default browser."""
                            import webbrowser
                            webbrowser.open(url)
                        
                        manual_button = ttk.Button(
                            mod_frame,
                            text="Manually Download",
                            command=open_manual_download
                        )
                        manual_button.pack(pady=(5, 0))
                    
                    # Options dropdown (backup, recycle, delete)
                    option_var = tk.StringVar(value="recycle")
                    self.selected_options[filename] = option_var
                    
                    options_label = ttk.Label(mod_frame, text="Action for failed file:")
                    options_label.pack(anchor=tk.W, pady=(5, 0))
                    
                    options_combo = ttk.Combobox(
                        mod_frame,
                        textvariable=option_var,
                        values=["backup", "recycle", "delete"],
                        state="readonly",
                        width=20
                    )
                    options_combo.pack(anchor=tk.W)
                    options_combo.current(1)  # Default to "recycle"
                
                # Add action buttons for failed mods
                action_frame = ttk.Frame(scrollable_frame)
                action_frame.pack(fill=tk.X, pady=(10, 0))
                
                def apply_failed_mod_actions():
                    """Apply selected actions to failed mods."""
                    if not self.directory_path:
                        messagebox.showwarning("No Directory", "Mod directory path not available for applying actions.")
                        return
                    
                    from services.backup_manager import BackupManager
                    backup_dir = Path(self.app.path_manager.base_path) / "backups"
                    backup_manager = BackupManager(self.directory_path, backup_dir)
                    
                    for filename, option_var in self.selected_options.items():
                        option = option_var.get()
                        failed_file_path = self.directory_path / filename
                        
                        self._apply_action_to_failed_file(filename, option, failed_file_path, backup_manager)
                    
                    messagebox.showinfo("Actions Applied", f"Applied actions to {len(self.selected_options)} failed mod(s)")
                
                apply_button = ttk.Button(action_frame, text="Apply Actions to Failed Mods", command=apply_failed_mod_actions)
                apply_button.pack(pady=(10, 0))
        
        # Close button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))
        
        close_button = ttk.Button(button_frame, text="Close", command=lambda: self.dialog.destroy() if self.dialog else None)  # type: ignore
        close_button.pack()


class DatabaseRefreshedDialog:
    """Modal dialog for displaying database refresh completion with theme applied."""
    
    def __init__(self, parent: tk.Tk, app_instance, mod_count: int):
        """
        Initialize the database refreshed dialog.
        
        Args:
            parent: Parent window
            app_instance: The main application instance (for theme access)
            mod_count: Number of mods in the refreshed database
        """
        self.parent = parent
        self.app = app_instance
        self.mod_count = mod_count
        self.dialog: Optional[tk.Toplevel] = None
    
    def show(self):
        """Show the database refreshed dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Database Refreshed")
        self.dialog.minsize(400, 200)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Apply theme if available
        if hasattr(self.app, 'theme_manager') and self.app.theme_manager:
            try:
                self.app.theme_manager.apply_theme(self.dialog, theme_mode="auto")
            except Exception as e:
                logger.warning(f"Failed to apply theme to database refreshed dialog: {e}")
        
        # Create UI
        self._create_ui()
        
        # Update to get actual dialog size after UI is created
        self.dialog.update_idletasks()
        
        # Center the dialog
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        """Create dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Success icon (checkmark)
        success_label = ttk.Label(
            main_frame,
            text="✓",
            font=("Helvetica", 48, "bold"),
            foreground="#4CAF50"
        )
        success_label.pack(pady=(0, 15))
        
        # Title
        title = ttk.Label(
            main_frame,
            text="Database Refreshed",
            font=("Helvetica", 16, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Message
        message = ttk.Label(
            main_frame,
            text=f"Successfully refreshed the mod database with {self.mod_count} mods.",
            wraplength=350,
            justify=tk.CENTER
        )
        message.pack(pady=(0, 20))
        
        # Close button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))
        
        close_button = ttk.Button(button_frame, text="Close", command=lambda: self.dialog.destroy() if self.dialog else None)  # type: ignore
        close_button.pack()


class ModSelectionDialog:
    """Modal dialog for selecting a mod from author search results."""
    
    def __init__(self, parent: tk.Tk, author: str, projects: List[Dict[str, Any]]):
        """
        Initialize the mod selection dialog.
        
        Args:
            parent: Parent window
            author: The author name
            projects: List of project dictionaries with 'id' and 'name' keys
        """
        self.parent = parent
        self.author = author
        self.projects = projects
        self.selected_project: Optional[Dict[str, Any]] = None
        self.dialog: Optional[tk.Toplevel] = None
    
    def show(self) -> Optional[Dict[str, Any]]:
        """Show the mod selection dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Select Mod for {self.author}")
        self.dialog.minsize(500, 400)
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Create UI
        self._create_ui()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.selected_project
    
    def _create_ui(self):
        """Create dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame,
            text=f"Select Mod for Author: {self.author}",
            font=("Helvetica", 14, "bold")
        )
        title.pack(pady=(0, 10))
        
        # Instructions
        instructions = ttk.Label(
            main_frame,
            text="Multiple mods found for this author. Please select the correct mod to download.",
            wraplength=450,
            justify=tk.CENTER
        )
        instructions.pack(pady=(0, 15))
        
        # Create a scrollable frame for the project list
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel for scrolling
        canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        
        # Add project buttons
        for project in self.projects:
            project_frame = ttk.Frame(scrollable_frame)
            project_frame.pack(fill=tk.X, pady=5, padx=10)
            
            project_name = project.get("name", "Unknown")
            project_id = project.get("id", "Unknown")
            
            project_button = ttk.Button(
                project_frame,
                text=project_name,
                command=lambda p=project: self._select_project(p)
            )
            project_button.pack(fill=tk.X)
        
        # Cancel button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._cancel_selection)
        cancel_button.pack()
    
    def _on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling."""
        widget = event.widget
        if isinstance(widget, tk.Canvas):
            widget.yview_scroll(-1 * int(event.delta / 120), "units")
    
    def _select_project(self, project: Dict[str, Any]):
        """Select a project and close the dialog."""
        self.selected_project = project
        if self.dialog:
            self.dialog.destroy()
    
    def _cancel_selection(self):
        """Cancel selection and close the dialog."""
        self.selected_project = None
        if self.dialog:
            self.dialog.destroy()


class PlaywrightDownloadResultDialog:
    """Modal dialog for displaying Playwright download results."""
    
    def __init__(self, parent: tk.Tk, app_instance,
                 api_failed_mods: List[Dict[str, Any]],
                 playwright_success: List[Dict[str, Any]],
                 playwright_failed: List[Dict[str, Any]]):
        """
        Initialize the Playwright download result dialog.
        
        Args:
            parent: Parent window
            app_instance: The main application instance (for theme access)
            api_failed_mods: Mods that failed API download
            playwright_success: Mods successfully downloaded via Playwright
            playwright_failed: Mods that failed both API and Playwright
        """
        self.parent = parent
        self.app = app_instance
        self.api_failed_mods = api_failed_mods
        self.playwright_success = playwright_success
        self.playwright_failed = playwright_failed
        self.dialog: Optional[tk.Toplevel] = None
        self.selected_options: Dict[str, tk.StringVar] = {}  # filename -> option variable
    
    def show(self):
        """Show the Playwright download result dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Download Results")
        self.dialog.minsize(500, 300)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Apply theme if available
        if hasattr(self.app, 'theme_manager') and self.app.theme_manager:
            try:
                self.app.theme_manager.apply_theme(self.dialog, theme_mode="auto")
            except Exception as e:
                logger.warning(f"Failed to apply theme to Playwright download result dialog: {e}")
        
        # Create UI first to get actual content size
        self._create_ui()
        
        # Update to get actual dialog size after UI is created
        self.dialog.update_idletasks()
        
        # Center the dialog
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def _apply_action_to_failed_file(self, filename: str, option: str, failed_file_path: Path, backup_manager: Any) -> None:
        """Apply a single action to a failed mod file.
        
        Args:
            filename: Name of the file
            option: Action option ("recycle", "delete", or "backup")
            failed_file_path: Path to the failed file
            backup_manager: BackupManager instance
        """
        if option == "recycle":
            backup_manager.move_to_recycle_bin(failed_file_path)
            logger.info(f"Moved failed mod to recycle bin: {filename}")
        elif option == "delete":
            backup_manager.permanently_delete(failed_file_path)
            logger.info(f"Permanently deleted failed mod: {filename}")
        elif option == "backup":
            # Create a new backup of the restored failed file
            if failed_file_path.exists():
                backup_path = backup_manager.create_backup(failed_file_path)
                if backup_path:
                    logger.info(f"Created backup for failed mod: {filename} -> {backup_path}")
                else:
                    logger.error(f"Failed to create backup for failed mod: {filename}")
            else:
                logger.warning(f"File not found for backup: {filename}")
    
    def _create_ui(self):
        """Create dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame,
            text="Download Results",
            font=("Helvetica", 14, "bold")
        )
        title.pack(pady=(0, 10))
        
        # API download failures
        if self.api_failed_mods:
            api_failed_count = len(self.api_failed_mods)
            api_failed_text = f"API Downloads Failed: {api_failed_count} mod(s)"
            api_failed_label = ttk.Label(main_frame, text=api_failed_text, foreground="#f44336")
            api_failed_label.pack(pady=(0, 5))
            
            # API failure reason message
            reason_label = ttk.Label(
                main_frame,
                text="These mods could not be downloaded via the CurseForge API. "
                     "Playwright has attempted to download them automatically.",
                foreground="#ff9800",
                wraplength=450,
                justify=tk.CENTER
            )
            reason_label.pack(pady=(5, 10))
        
        # Playwright success
        if self.playwright_success:
            playwright_success_count = len(self.playwright_success)
            playwright_success_text = f"Playwright Successfully Downloaded: {playwright_success_count} mod(s)"
            playwright_success_label = ttk.Label(main_frame, text=playwright_success_text, foreground="#4caf50")
            playwright_success_label.pack(pady=(10, 5))
            
            # List successful downloads
            if self.playwright_success:
                success_frame = ttk.LabelFrame(main_frame, text="Successfully Downloaded")
                success_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
                
                for mod_info in self.playwright_success:
                    mod_frame = ttk.Frame(success_frame)
                    mod_frame.pack(fill=tk.X, padx=5, pady=2)
                    
                    filename = mod_info.get("filename", "Unknown")
                    success_label = ttk.Label(mod_frame, text=f"✓ {filename}", foreground="#4caf50")
                    success_label.pack(anchor=tk.W)
        
        # Playwright failed
        if self.playwright_failed:
            playwright_failed_count = len(self.playwright_failed)
            playwright_failed_text = f"Playwright Failed: {playwright_failed_count} mod(s)"
            playwright_failed_label = ttk.Label(main_frame, text=playwright_failed_text, foreground="#f44336")
            playwright_failed_label.pack(pady=(10, 5))
            
            # Failed mods list with options
            if self.playwright_failed:
                failed_frame = ttk.LabelFrame(main_frame, text="Failed Mods - Action Required")
                failed_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
                
                # Create a canvas with scrollbar for failed mods
                canvas_frame = ttk.Frame(failed_frame)
                canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                canvas = tk.Canvas(canvas_frame, highlightthickness=0)
                scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
                scrollable_frame = ttk.Frame(canvas)
                
                scrollable_frame.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                
                # Bind mouse wheel events to canvas for scrolling
                def _on_mouse_wheel(event):
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                
                canvas.bind("<MouseWheel>", _on_mouse_wheel)
                scrollable_frame.bind("<MouseWheel>", _on_mouse_wheel)
                
                canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Add failed mods with options
                for i, mod_info in enumerate(self.playwright_failed):
                    mod_frame = ttk.Frame(scrollable_frame)
                    mod_frame.pack(fill=tk.X, pady=5)
                    
                    # Mod filename
                    filename = mod_info.get("filename", "Unknown")
                    filename_label = ttk.Label(mod_frame, text=filename, font=("Helvetica", 10, "bold"))
                    filename_label.pack(anchor=tk.W)
                    
                    # Error message
                    error_message = mod_info.get("error_message", "Unknown error")
                    error_label = ttk.Label(mod_frame, text=f"Error: {error_message}", foreground="#f44336")
                    error_label.pack(anchor=tk.W)
                    
                    # Options dropdown (backup, recycle, delete)
                    option_var = tk.StringVar(value="recycle")
                    self.selected_options[filename] = option_var
                    
                    options_label = ttk.Label(mod_frame, text="Action for failed file:")
                    options_label.pack(anchor=tk.W, pady=(5, 0))
                    
                    options_combo = ttk.Combobox(
                        mod_frame,
                        textvariable=option_var,
                        values=["backup", "recycle", "delete"],
                        state="readonly",
                        width=20
                    )
                    options_combo.pack(anchor=tk.W)
                    options_combo.current(1)  # Default to "recycle"
                
                # Add action buttons for failed mods
                action_frame = ttk.Frame(scrollable_frame)
                action_frame.pack(fill=tk.X, pady=(10, 0))
                
                def apply_failed_mod_actions():
                    """Apply selected actions to failed mods."""
                    directory_path = self.app.last_loaded_folder or self.app.settings.get("mod_directory", "")
                    if not directory_path:
                        messagebox.showwarning("No Directory", "Mod directory path not available for applying actions.")
                        return
                    
                    directory_path = Path(directory_path)
                    if not directory_path.exists():
                        messagebox.showwarning("Directory Not Found", f"The mod directory does not exist: {directory_path}")
                        return
                    
                    from services.backup_manager import BackupManager
                    backup_dir = Path(self.app.path_manager.base_path) / "backups"
                    backup_manager = BackupManager(directory_path, backup_dir)
                    
                    for filename, option_var in self.selected_options.items():
                        option = option_var.get()
                        failed_file_path = directory_path / filename
                        
                        self._apply_action_to_failed_file(filename, option, failed_file_path, backup_manager)
                    
                    messagebox.showinfo("Actions Applied", f"Applied actions to {len(self.selected_options)} failed mod(s)")
                
                apply_button = ttk.Button(action_frame, text="Apply Actions to Failed Mods", command=apply_failed_mod_actions)
                apply_button.pack(pady=(10, 0))
        
        # Close button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))
        
        close_button = ttk.Button(button_frame, text="Close", command=lambda: self.dialog.destroy() if self.dialog else None)  # type: ignore
        close_button.pack()
