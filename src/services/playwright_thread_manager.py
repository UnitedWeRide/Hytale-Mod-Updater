"""
Playwright Thread Manager Module

This module provides a dedicated thread for Playwright operations with its own
event loop, allowing concurrent downloads without blocking the UI.
"""

import asyncio
import logging
import queue
import threading
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PlaywrightThreadManager:
    """
    Manages a dedicated thread for Playwright operations with its own event loop.
    
    This allows Playwright downloads to run concurrently without blocking the UI
    or each other, while ensuring all Playwright operations happen on a single thread.
    """
    
    def __init__(self, mod_directory: Path):
        """
        Initialize the Playwright thread manager.
        
        Args:
            mod_directory: Directory to save downloaded mods
        """
        self.mod_directory = mod_directory
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: queue.Queue = queue.Queue()
        self._running: bool = False
        self._shutdown_event: threading.Event = threading.Event()
        self._download_callbacks: Dict[int, Any] = {}  # Track callbacks by mod_id
        self._lock = threading.Lock()
    
    def start(self) -> None:
        """Start the Playwright thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Playwright thread already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="PlaywrightThread")
        self._thread.start()
        logger.info("Playwright thread started")
    
    def _run_loop(self) -> None:
        """Run the event loop in this thread."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._process_queue())
        except Exception as e:
            logger.error(f"Error in Playwright thread: {e}")
        finally:
            if self._loop is not None:
                self._loop.close()
                self._loop = None
            logger.info("Playwright thread stopped")
    
    async def _process_queue(self) -> None:
        """Process download requests from the queue."""
        if self._loop is None:
            logger.error("Event loop not initialized")
            return
        
        while not self._shutdown_event.is_set():
            try:
                task = await asyncio.wait_for(
                    self._loop.run_in_executor(None, self._queue.get),
                    timeout=1.0
                )
                if task is None:
                    break
                mod_info, callback = task
                await self._execute_download(mod_info, callback)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
    
    async def _execute_download(self, mod_info: Dict[str, Any], callback: Any) -> None:
        """Execute a single download in the Playwright thread."""
        try:
            from .playwright_downloader import PlaywrightDownloader
            
            downloader = PlaywrightDownloader(self.mod_directory)
            downloaded_path, error_message = await self._loop.run_in_executor(
                None,
                lambda: downloader.download_mod_sync(mod_info)
            )
            
            # Report progress via callback
            if callback:
                if downloaded_path:
                    callback(mod_info, True, str(downloaded_path), "")
                else:
                    callback(mod_info, False, "", error_message or "Unknown error")
        except Exception as e:
            logger.error(f"Error executing download: {e}")
            if callback:
                callback(mod_info, False, "", str(e))
    
    def submit_download(self, mod_info: Dict[str, Any], callback: Any) -> None:
        """
        Submit a download task to the Playwright thread.
        
        Args:
            mod_info: Dict with mod_id, filename
            callback: Callback function(mod_info, success, path, error)
        """
        if not self._running or self._thread is None:
            logger.warning("Playwright thread not running, starting it")
            self.start()
        
        try:
            self._queue.put((mod_info, callback), block=False)
            logger.debug(f"Download submitted for mod_id: {mod_info.get('mod_id')}")
        except queue.Full:
            logger.error("Playwright queue is full")
            if callback:
                callback(mod_info, False, "", "Queue full")
    
    def shutdown(self) -> None:
        """Shutdown the Playwright thread."""
        self._running = False
        self._shutdown_event.set()
        self._queue.put(None)  # Signal shutdown
        
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("Playwright thread did not stop gracefully")
            else:
                logger.info("Playwright thread stopped")
    
    def is_running(self) -> bool:
        """Check if the Playwright thread is running."""
        return self._running and self._thread is not None and self._thread.is_alive()
