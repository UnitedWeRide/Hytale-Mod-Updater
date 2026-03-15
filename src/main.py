#!/usr/bin/env python3
"""
Hytale Mod Updater - Main Application Entry Point (Stripped Version)
  
This script is the main entry point for the Hytale Mod Updater application.
It initializes the application with minimal components: GUI, Settings, API Key, Keychain.
"""

import sys
import logging
import asyncio

import tkinter as tk

from src.config.settings import SettingsManager
from src.config.paths import PathManager
from src.utils.logging import setup_logging
from src.core.app import HytaleModUpdater


async def async_main():
    """Main async entry point for the application."""
    # Initialize path manager first (needed for config path)
    path_manager = PathManager()
    path_manager.ensure_directories()
    
    # Initialize settings manager to get debug mode setting
    settings_manager = SettingsManager(config_path=path_manager.config_path)
    debug_mode = settings_manager.get("debug_mode", False)
    
    # Setup logging with debug mode from settings using centralized logging
    setup_logging(debug_mode=debug_mode, log_path=path_manager.log_path)
    
    logger = logging.getLogger(__name__)
    logger.info("=== Hytale Mod Updater Starting (Stripped) ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logger.info(f"Debug mode: {debug_mode}")
    
    logger.info(f"Base path: {path_manager.base_path}")
    logger.info(f"Resources path: {path_manager.resources_path}")
    
    # Create main window
    root = tk.Tk()
    
    # Create application instance
    app = HytaleModUpdater(
        root=root,
        settings_manager=settings_manager,
        path_manager=path_manager
    )
    
    # Schedule async tasks to run periodically
    def schedule_async_tasks():
        """Schedule async tasks to run in the Tkinter event loop."""
        # Run any pending async tasks
        try:
            loop = asyncio.get_event_loop()
            # Process any pending callbacks
            root.after(10, schedule_async_tasks)
        except (OSError, IOError, asyncio.CancelledError) as e:
            logger.error(f"Error scheduling async tasks: {e}")
            root.after(10, schedule_async_tasks)
    
    # Start the async task scheduler
    root.after(10, schedule_async_tasks)
    
    # Run main loop
    root.mainloop()
    
    logger.info("=== Hytale Mod Updater Closed ===")


def main():
    """Main entry point for the application."""
    # Run the async main function
    asyncio.run(async_main())


if __name__ == "__main__":
    main()