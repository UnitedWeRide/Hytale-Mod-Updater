"""
Logging Utility Module

This module provides centralized logging configuration for the Hytale Mod Updater.
It handles both file and console logging with configurable debug mode.
"""

import os
import sys
import logging
from typing import Optional
from pathlib import Path


def setup_logging(debug_mode: bool = False, log_path: Optional[str] = None) -> None:
    """
    Setup logging configuration for the application.
    
    Args:
        debug_mode: If True, enable DEBUG level logging; otherwise INFO level
        log_path: Optional path to log file. If None, uses default log location
    """
    # Determine log level based on debug mode
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Format for log messages
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler - always logs to file
    if log_path is None:
        # Try to determine log path from path_manager if not provided
        try:
            # Internal module import - removed to avoid undeclared dependency
            # from .config.paths import PathManager
            # path_manager = PathManager()
            # log_path = path_manager.log_path
            pass
        except (ImportError, AttributeError) as e:
            logging.debug(f"PathManager fallback triggered: {e}")
            log_path = os.path.join(os.path.dirname(__file__), "..", "..", "app_debug.log")
    
    # Ensure log_path is set (fallback if still None)
    if log_path is None:
        log_path = os.path.join(os.path.dirname(__file__), "..", "..", "app_debug.log")
    
    # Ensure log directory exists
    log_dir = os.path.dirname(log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    try:
        # Overwrite log file on each run instead of appending
        file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)
        logging.info(f"Logging to file: {log_path}")
    except OSError as e:
        logging.warning(f"Could not create log file at {log_path}: {e}")
    
    # Console handler - always enabled for frozen apps (exe)
    # This ensures INFO level logging shows in the console when running the exe
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    logging.info("Console logging enabled")
    
    # Log initial setup info
    logging.info(f"Logging initialized - Level: {logging.getLevelName(log_level)}, Debug mode: {debug_mode}")