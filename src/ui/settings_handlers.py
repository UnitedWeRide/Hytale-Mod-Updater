"""
Settings Handlers (Stripped Version)

This module handles settings dialog and API key management for the Hytale Mod Updater.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional

import logging

from src.services.keyring_manager import KeyringManager

logger = logging.getLogger(__name__)


class SettingsHandlers:
    """Handle settings dialog and API key management (Stripped)."""
    
    def __init__(self, app_instance):
        """
        Initialize the settings handlers.
        
        Args:
            app_instance: The main application instance
        """
        self.app = app_instance
        
    def open_settings(self):
        """Open the settings panel."""
        settings_window = tk.Toplevel(self.app.root)
        settings_window.title("Settings")
        
        # Responsive window size based on screen resolution
        screen_width = settings_window.winfo_screenwidth()
        screen_height = settings_window.winfo_screenheight()
        window_width = int(screen_width * 0.4)  # 40% of screen width
        window_height = int(screen_height * 0.8)  # 8% of screen height
        settings_window.geometry(f"{window_width}x{window_height}")
        settings_window.minsize(300, 250)  # Minimum size for usability
        
        # Center the window on screen
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        settings_window.geometry(f"+{x}+{y}")
        
        # Configure grid weights for proper resizing
        settings_window.grid_rowconfigure(0, weight=1)
        settings_window.grid_columnconfigure(0, weight=1)
        
        # Create scrollable frame using canvas
        canvas_frame = ttk.Frame(settings_window)
        canvas_frame.grid(row=0, column=0, sticky="nsew")
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel for scrolling
        canvas.bind_all("<MouseWheel>", self._on_settings_mouse_wheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store canvas reference for cleanup
        self._settings_canvas = canvas
        
        # Main frame with grid layout (inside scrollable frame)
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.pack(fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Row counter for grid layout
        row = 0
        
        # Theme info - dark forest with auto-detection
        theme_frame = ttk.Frame(main_frame)
        theme_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(theme_frame, text="Theme: Dark Forest (Auto)", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(theme_frame, text="The app uses dark forest theme with automatic system detection.").pack(anchor=tk.W, pady=(5, 0))
        
        # Debug mode
        debug_frame = ttk.Frame(main_frame)
        debug_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(debug_frame, text="Debug Mode:").pack(anchor=tk.W)
        
        debug_var = tk.BooleanVar(value=self.app.settings.get("debug_mode", False))
        
        debug_check = ttk.Checkbutton(
            debug_frame,
            text="Enable comprehensive logging (requires restart)",
            variable=debug_var,
            command=lambda: self.toggle_debug_mode(debug_var.get())
        )
        debug_check.pack(anchor=tk.W)
        
        # Close terminal on exit
        terminal_frame = ttk.Frame(main_frame)
        terminal_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(terminal_frame, text="Close Terminal on Exit:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        close_terminal_var = tk.BooleanVar(value=self.app.settings.get("close_terminal_on_exit", True))
        
        close_terminal_check = ttk.Checkbutton(
            terminal_frame,
            text="Close terminal window when app exits",
            variable=close_terminal_var
        )
        close_terminal_check.pack(anchor=tk.W)
        
        # Game selection
        game_frame = ttk.Frame(main_frame)
        game_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(game_frame, text="Game:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        game_id = self.app.settings.get("game_id", 70216)
        game_name = self.app.settings.get("game_name", "Hytale")
        
        game_info = ttk.Label(game_frame, text=f"Current: {game_name} (ID: {game_id})")
        game_info.pack(anchor=tk.W, pady=(5, 0))
        
        change_game_button = ttk.Button(
            game_frame,
            text="Change Game",
            command=lambda: self._change_game(settings_window)
        )
        change_game_button.pack(anchor=tk.W, pady=(5, 0))
        
        # Update rules (only stable, ignore beta)
        update_rules_frame = ttk.Frame(main_frame)
        update_rules_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(update_rules_frame, text="Update Rules:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        only_stable_var = tk.BooleanVar(value=self.app.settings.get("only_stable", True))
        ignore_beta_var = tk.BooleanVar(value=self.app.settings.get("ignore_beta", True))
        
        only_stable_check = ttk.Checkbutton(
            update_rules_frame,
            text="Only update to stable versions",
            variable=only_stable_var
        )
        only_stable_check.pack(anchor=tk.W, pady=(5, 0))
        
        ignore_beta_check = ttk.Checkbutton(
            update_rules_frame,
            text="Ignore beta versions",
            variable=ignore_beta_var
        )
        ignore_beta_check.pack(anchor=tk.W, pady=(5, 0))
        
        api_frame = ttk.Frame(main_frame)
        api_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(api_frame, text="CurseForge API Key:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        if self.app.api_key:
            api_status = "✓ Configured - Using official CurseForge API"
            status_color = "green"
        else:
            api_status = "✗ Not configured - Advanced search disabled"
            status_color = "orange"
        
        status_label = ttk.Label(api_frame, text=api_status, foreground=status_color)
        status_label.pack(anchor=tk.W, pady=(5, 0))
        
        button_frame = ttk.Frame(api_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        if self.app.api_key:
            ttk.Button(
                button_frame,
                text="Change API Key",
                command=lambda: self._change_api_key(settings_window)
            ).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(
                button_frame,
                text="Remove API Key",
                command=lambda: self._remove_api_key(settings_window)
            ).pack(side=tk.LEFT, padx=(0, 5))
        else:
            ttk.Button(
                button_frame,
                text="Add API Key",
                command=lambda: self._add_api_key(settings_window)
            ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Download rate limit
        rate_limit_frame = ttk.Frame(main_frame)
        rate_limit_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(rate_limit_frame, text="Download Rate Limit:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        rate_limit_var = tk.DoubleVar(value=self.app.settings.get("download_rate_limit", 0.5))
        
        rate_limit_slider = ttk.Scale(
            rate_limit_frame,
            from_=0.1,
            to=5.0,
            orient=tk.HORIZONTAL,
            variable=rate_limit_var
        )
        rate_limit_slider.pack(fill=tk.X, pady=(5, 0))
        
        rate_limit_label = ttk.Label(rate_limit_frame, text=f"{rate_limit_var.get():.1f} seconds")
        rate_limit_label.pack(anchor=tk.W, pady=(5, 0))
        
        def update_rate_limit_label():
            rate_limit_label.config(text=f"{rate_limit_var.get():.1f} seconds")
        
        rate_limit_var.trace("w", lambda *args: update_rate_limit_label())
        
        # Full speed database pagination
        full_speed_frame = ttk.Frame(main_frame)
        full_speed_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(full_speed_frame, text="Full Speed Database Pagination:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        full_speed_var = tk.BooleanVar(value=self.app.settings.get("full_speed_db_pagination", False))
        
        full_speed_check = ttk.Checkbutton(
            full_speed_frame,
            text="Enable",
            variable=full_speed_var
        )
        full_speed_check.pack(anchor=tk.W)
        
        # Caption explaining the setting
        ttk.Label(full_speed_frame, text="Uses all CPU threads to paginate the database without rate limiting.", foreground="gray").pack(anchor=tk.W, pady=(2, 0))
        
        # Warning about experimental nature
        warning_label = ttk.Label(full_speed_frame, text="⚠️ Warning: This setting is experimental and may cause the app to become unresponsive for a brief period.", foreground="orange", font=("Helvetica", 9, "italic")).pack(anchor=tk.W, pady=(5, 0))
        
        # Automated update check
        automated_update_frame = ttk.Frame(main_frame)
        automated_update_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(automated_update_frame, text="Automated Update Check:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        automated_update_var = tk.BooleanVar(value=self.app.settings.get("automated_update_check", False))
        
        automated_update_check = ttk.Checkbutton(
            automated_update_frame,
            text="Enable",
            variable=automated_update_var
        )
        automated_update_check.pack(anchor=tk.W)
        
        # Caption explaining the setting
        ttk.Label(automated_update_frame, text="Automatically checks for updates and downloads outdated mods after loading a folder.", foreground="gray").pack(anchor=tk.W, pady=(2, 0))
        
        # Restore mods on launch
        restore_mods_frame = ttk.Frame(main_frame)
        restore_mods_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        
        ttk.Label(restore_mods_frame, text="Restore Mods Folder on Launch:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)
        
        restore_mods_var = tk.BooleanVar(value=self.app.settings.get("restore_mods_on_launch", False))
        
        restore_mods_check = ttk.Checkbutton(
            restore_mods_frame,
            text="Enable",
            variable=restore_mods_var
        )
        restore_mods_check.pack(anchor=tk.W)
        
        # Caption explaining the setting
        ttk.Label(restore_mods_frame, text="Restores the previously loaded mods folder and treeview on app launch.", foreground="gray").pack(anchor=tk.W, pady=(2, 0))
        
        # Save button frame at bottom
        save_button_frame = ttk.Frame(main_frame)
        save_button_frame.grid(row=row, column=0, sticky="ew", pady=(10, 0))
        row += 1
        
        save_button = ttk.Button(
            save_button_frame,
            text="Save Settings",
            command=lambda: self.save_settings(debug_var.get(), settings_window, close_terminal_var.get(), rate_limit_var.get(), only_stable_var.get(), ignore_beta_var.get(), full_speed_var.get(), automated_update_var.get(), restore_mods_var.get())
        )
        save_button.pack(side=tk.RIGHT)
        
        # Cleanup binding when window is destroyed
        settings_window.bind("<Destroy>", lambda e: self._cleanup_settings_canvas())
    
    def _add_api_key(self, parent: tk.Toplevel):
        """Add API key."""
        from src.ui.dialogs import APIKeyDialog
        dialog = APIKeyDialog(self.app.root)
        api_key = dialog.show()
        if api_key:
            self.app.api_key = api_key
            parent.destroy()
            self.open_settings()
    
    def _change_api_key(self, parent: tk.Toplevel):
        """Change API key."""
        KeyringManager.delete_api_key()
        self.app.api_key = None
        parent.destroy()
        self.open_settings()
    
    def _remove_api_key(self, parent: tk.Toplevel):
        """Remove API key."""
        if messagebox.askyesno("Confirm", "Remove API key from keyring?"):
            KeyringManager.delete_api_key()
            self.app.api_key = None
            parent.destroy()
            self.open_settings()
    
    def toggle_debug_mode(self, enabled: bool):
        """Toggle debug mode and update logging configuration."""
        from src.utils.logging import setup_logging
        try:
            setup_logging(debug_mode=enabled, log_path=self.app.path_manager.log_path)
            logger.info("Debug mode enabled from settings" if enabled else "Debug mode disabled from settings")
        except (OSError, IOError, ImportError) as e:
            logger.error(f"Failed to toggle debug mode: {e}")
            messagebox.showerror("Error", f"Failed to toggle debug mode: {e}")
    
    def save_settings(self, debug_mode: bool, window: tk.Toplevel, close_terminal: bool = True, rate_limit: float = 0.5, only_stable: bool = True, ignore_beta: bool = True, full_speed_db_pagination: bool = False, automated_update_check: bool = False, restore_mods_on_launch: bool = False):
        """Save the selected settings."""
        old_debug_mode = self.app.settings.get("debug_mode", False)
        old_full_speed_mode = self.app.settings.get("full_speed_db_pagination", False)
        self.app.settings["debug_mode"] = debug_mode
        self.app.settings["close_terminal_on_exit"] = close_terminal
        self.app.settings["download_rate_limit"] = rate_limit
        self.app.settings["only_stable"] = only_stable
        self.app.settings["ignore_beta"] = ignore_beta
        self.app.settings["full_speed_db_pagination"] = full_speed_db_pagination
        self.app.settings["automated_update_check"] = automated_update_check
        self.app.settings["restore_mods_on_launch"] = restore_mods_on_launch
        self.app.save_settings()
        
        # Re-initialize database manager if full-speed mode changed
        if old_full_speed_mode != full_speed_db_pagination and self.app.mod_database_manager:
            self.app.mod_database_manager.settings = self.app.settings
            logger.info(f"Updated database manager with new settings: full_speed_db_pagination={full_speed_db_pagination}")
        
        if debug_mode != old_debug_mode:
            messagebox.showinfo(
                "Restart Required",
                "Debug mode changes will take effect after restarting the application.\n\n"
                "The application will now close. Please restart it to enable debug logging."
            )
            self.app.root.quit()
            return
        
        window.destroy()
    
    def _change_game(self, parent: tk.Toplevel):
        """Change the selected game."""
        from ui.dialogs import GameSelectionDialog
        dialog = GameSelectionDialog(self.app.root, self.app)
        dialog.show()
        parent.destroy()
        self.open_settings()
    
    def _on_settings_mouse_wheel(self, event):
        """Handle mouse wheel scrolling for settings canvas."""
        canvas = getattr(self, '_settings_canvas', None)
        if canvas:
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
    
    def _cleanup_settings_canvas(self):
        """Clean up settings canvas binding when window is destroyed."""
        if hasattr(self, '_settings_canvas'):
            try:
                self._settings_canvas.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass
            delattr(self, '_settings_canvas')