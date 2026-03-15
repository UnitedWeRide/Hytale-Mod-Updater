"""
Mod Downloader Module

This module provides functionality for downloading mod files from CurseForge.
"""

import logging
import time
import urllib.parse
import threading
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests

logger = logging.getLogger(__name__)


class ModDownloader:
    """Download mod files from CurseForge."""
    
    def __init__(self, api_key: str, mod_directory: Path, rate_limit_delay: float = 0.5):
        """
        Initialize the mod downloader.
        
        Args:
            api_key: CurseForge API key
            mod_directory: Directory to save downloaded mods
            rate_limit_delay: Delay between download calls in seconds (default: 0.5)
        """
        self.api_key = api_key
        self.mod_directory = mod_directory
        self.rate_limit_delay = rate_limit_delay
        self.headers = {
            "x-api-key": api_key,
            "Accept": "application/json"
        }
        self._download_lock = threading.Lock()
        self._last_download_time = 0
        self._playwright_downloader = None  # Lazy init for Playwright fallback
        self._executor = ThreadPoolExecutor(max_workers=5)
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between download calls."""
        with self._download_lock:
            current_time = time.time()
            elapsed = current_time - self._last_download_time
            
            if elapsed < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - elapsed
                time.sleep(sleep_time)
            
            self._last_download_time = time.time()
            logger.debug(f"Rate limit enforced: {elapsed:.3f}s elapsed, {self.rate_limit_delay}s delay")
    
    def download_file(self, mod_id: int, file_id: int, filename: str, progress_callback=None) -> Tuple[Optional[Path], str, Optional[str], bool]:
        """
        Download a single mod file.
        
        Args:
            mod_id: The CurseForge mod ID
            file_id: The CurseForge file ID
            filename: The filename to save as (used for logging only)
            progress_callback: Optional callback (current, total, filename, status)
            
        Returns:
            Tuple of (Path to downloaded file, error_message, download_url, playwright_success)
        """
        try:
            download_url = self._get_download_url(mod_id, file_id)
            if download_url is None:
                return self._try_cfwidget_fallback(mod_id, filename)
            
            return self._download_from_url(download_url, filename)
        except (OSError, IOError) as e:
            logger.error(f"Error downloading mod {mod_id} file {file_id}: {e}")
            # API download failed, try CFWidget fallback
            logger.info(f"API download failed for mod {mod_id}, trying CFWidget fallback")
            return self._try_cfwidget_fallback(mod_id, filename)
    
    def _get_download_url(self, mod_id: int, file_id: int) -> Optional[str]:
        """Get download URL from CurseForge API."""
        from .curseforge_api import CurseForgeAPI
        api = CurseForgeAPI(self.api_key)
        return api.get_download_url(mod_id, file_id)
    
    def _download_from_url(self, download_url: str, filename: str) -> Tuple[Optional[Path], str, Optional[str], bool]:
        """Download file from URL and save to mod directory."""
        # Extract the actual filename from the download URL
        actual_filename = download_url.split('/')[-1]
        actual_filename = urllib.parse.unquote(actual_filename)
        logger.info(f"Download URL filename: {actual_filename}")
        
        # Download the file using requests
        import requests
        # Validate URL to prevent SSRF attacks
        parsed_url = urllib.parse.urlparse(download_url)
        if parsed_url.scheme not in ('http', 'https'):
            logger.error(f"Invalid URL scheme: {download_url}")
            return (None, "Invalid URL scheme", download_url, False)
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Save to mod directory with decoded filename
        output_path = self.mod_directory / actual_filename
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded {actual_filename} to {output_path}")
        return (output_path, "", download_url, False)  # False = playwright_success
    
    def _try_cfwidget_fallback(self, mod_id: int, filename: str) -> Tuple[Optional[Path], str, Optional[str], bool]:
        """
        Try CFWidget API then Playwright fallback for downloading a mod.
        
        Args:
            mod_id: The CurseForge mod ID
            filename: The filename to save as
            
        Returns:
            Tuple of (Path to downloaded file, error_message, download_url, playwright_success)
        """
        try:
            from .cfwidget_api import CFWidgetAPI
            cfapi = CFWidgetAPI()
            
            # Try CFWidget API first
            download_url = cfapi.get_download_url(mod_id)
            if download_url:
                logger.info(f"CFWidget API download URL: {download_url}")
                # Validate URL to prevent SSRF attacks
                parsed_url = urllib.parse.urlparse(download_url)
                if parsed_url.scheme not in ('http', 'https'):
                    logger.error(f"Invalid URL scheme: {download_url}")
                    return (None, "Invalid URL scheme", download_url, True)
                # Download via requests
                import requests
                response = requests.get(download_url, timeout=60)
                if response.status_code == 200:
                    output_path = self.mod_directory / filename
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"Downloaded via CFWidget API: {output_path}")
                    return (output_path, "", download_url, True)
            
            # CFWidget API failed, try Playwright
            logger.info(f"CFWidget API download failed for {filename}, trying Playwright fallback")
            
            if not self._playwright_downloader:
                from services.playwright_downloader import PlaywrightDownloader
                self._playwright_downloader = PlaywrightDownloader(self.mod_directory)
                logger.info("Playwright downloader initialized")
            
            mod_info = {"mod_id": mod_id, "filename": filename}
            logger.info(f"Starting Playwright download for mod_id: {mod_id}, filename: {filename}")
            
            # Run Playwright download in a thread to avoid blocking the UI
            # Note: Playwright downloads happen in a visible browser window that the user can monitor
            # Progress callbacks are not used because:
            # 1. The download progress is handled by the browser, not Python code
            # 2. Playwright only fires download events when the download completes
            # 3. The browser window provides visual feedback of the download progress
            playwright_downloader = self._playwright_downloader
            assert playwright_downloader is not None
            
            downloaded_path, error_message = self._executor.submit(
                lambda: playwright_downloader.download_mod_sync(mod_info, progress_callback=None)
            ).result()
            
            if downloaded_path:
                logger.info(f"Playwright download successful for {filename}")
                return (downloaded_path, "", download_url, True)  # True = playwright_success
            else:
                logger.error(f"Playwright download failed for {filename}: {error_message}")
                return (None, error_message, download_url, False)  # False = playwright_success
            
        except (OSError, IOError) as e:
            logger.error(f"Error in CFWidget/Playwright fallback for mod {mod_id}: {e}")
            return (None, str(e), None, False)
    
    def download_mods(self, outdated_mods: List[Dict[str, Any]],
                      progress_callback=None, max_workers: int = 3) -> Dict[str, Any]:
        """
        Download multiple outdated mods using multithreading with rate limiting.
        
        Args:
            outdated_mods: List of outdated mod info dictionaries
            progress_callback: Optional callback (current, total, filename, status)
            max_workers: Maximum number of concurrent downloads (default: 3)
            
        Returns:
            Download summary dictionary
        """
        results = {
            "success": [],
            "failed": [],
            "total": len(outdated_mods),
            "error_message": ""
        }
        
        if not outdated_mods:
            return results
        
        # Ensure mod directory exists
        self.mod_directory.mkdir(parents=True, exist_ok=True)
        
        # Reset rate limiting state
        self._last_download_time = 0
        
        # Track progress with thread-safe counter
        progress_lock = threading.Lock()
        completed_count = 0
        
        def progress_update(filename, status=None):
            nonlocal completed_count
            with progress_lock:
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count, len(outdated_mods), filename, status)
        
        # Download with multithreading and rate limiting
        return self._download_mods_multithreaded(outdated_mods, progress_lock, completed_count, progress_update, max_workers, results)
    
    def _download_mods_multithreaded(self, outdated_mods: List[Dict[str, Any]],
                                      progress_lock: threading.Lock,
                                      completed_count: int,
                                      progress_update_func,
                                      max_workers: int,
                                      results: Dict[str, Any]) -> Dict[str, Any]:
        """Multithreaded download logic - extracted to reduce function length."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_mod = {}
            for mod in outdated_mods:
                mod_id = mod["mod_id"]
                file_id = mod["latest_file_id"]
                
                # Use the original filename from the outdated mod data
                filename = mod["file_path"].name
                
                future = executor.submit(
                    self._download_with_rate_limit,
                    mod_id, file_id, filename, None  # progress_callback handled externally
                )
                future_to_mod[future] = {
                    "mod_id": mod_id,
                    "filename": filename,
                    "playwright_attempted": True  # Mark for Playwright fallback tracking
                }
            
            # Process completed downloads
            for future in future_to_mod:
                mod_info = future_to_mod[future]
                downloaded_path, error_message, download_url, playwright_success = future.result()
                
                # Check if this is a Playwright fallback attempt
                is_playwright_fallback = "playwright_attempted" in mod_info
                
                if downloaded_path:
                    results["success"].append({
                        "mod_id": mod_info["mod_id"],
                        "filename": mod_info["filename"],
                        "path": downloaded_path
                    })
                    progress_update_func(mod_info["filename"])
                else:
                    failed_entry = {
                        "mod_id": mod_info["mod_id"],
                        "filename": mod_info["filename"],
                        "error_message": error_message,
                        "download_url": download_url
                    }
                    
                    if is_playwright_fallback:
                        failed_entry["playwright_attempted"] = mod_info.get("playwright_attempted")
                        failed_entry["playwright_success"] = playwright_success
                    
                    results["failed"].append(failed_entry)
                    # Store the first error message for the dialog
                    if not results["error_message"] and error_message:
                        results["error_message"] = error_message
                    
                    # Update progress after each completion
                    if is_playwright_fallback:
                        if playwright_success:
                            progress_update_func(mod_info["filename"], "Playwright downloaded:")
                        else:
                            progress_update_func(mod_info["filename"], "Playwright failed for:")
                    else:
                        progress_update_func(mod_info["filename"])
        
        return results
    
    def _download_with_rate_limit(self, mod_id: int, file_id: int, filename: str, progress_callback=None) -> Tuple[Optional[Path], str, Optional[str], bool]:
        """Download a file with rate limiting."""
        self._enforce_rate_limit()
        return self.download_file(mod_id, file_id, filename, progress_callback)
    
    def shutdown(self):
        """Shutdown the thread executor."""
        self._executor.shutdown(wait=True)