"""
Playwright Downloader Module

This module provides functionality for downloading mod files from CurseForge
using Playwright browser automation as a fallback when API downloads fail.
"""

import logging
import asyncio
import os
import sys
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_playwright_driver_path() -> str:
    """
    Get the Playwright driver path for the bundled executable.
    
    When running as a PyInstaller executable, the Playwright browser binaries
    are extracted to a temporary directory. This function finds the correct path.
    
    The Playwright driver directory structure is:
        playwright/driver/package/.local-browsers/chromium_headless_shell-XXX/
    
    Returns:
        Path to the Playwright driver directory
    """
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        # Playwright driver is extracted to _MEIPASS/playwright/driver
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path:
            driver_path = os.path.join(base_path, "playwright", "driver")
            if os.path.exists(driver_path):
                return driver_path
    # Running as normal Python script
    import playwright
    playwright_path = os.path.dirname(playwright.__file__)
    driver_path = os.path.join(playwright_path, "driver")
    return driver_path


class PlaywrightDownloader:
    """Download mods using Playwright browser automation."""
    
    def __init__(self, mod_directory: Path, progress_callback=None):
        """
        Initialize the Playwright downloader.
        
        Args:
            mod_directory: Directory to save downloaded mods
            progress_callback: Optional callback(mod_info, success, path, error) called when download completes
        """
        self.mod_directory = mod_directory
        self.browser = None
        self.context = None
        self._playwright = None
        self._progress_callback = progress_callback
    
    async def download_mod(self, mod_info: Dict[str, Any], progress_callback=None) -> Tuple[Optional[Path], str]:
        """
        Download mod using Playwright.
        
        Args:
            mod_info: Dict with mod_id, filename
            progress_callback: Optional callback(mod_info, success, path, error) called when download completes
            
        Returns:
            Tuple of (downloaded_path, error_message)
        """
        try:
            logger.info(f"Playwright download started for mod_id: {mod_info.get('mod_id')}, filename: {mod_info.get('filename')}")
            
            # Set PLAYWRIGHT_BROWSERS_PATH to the bundled browsers location
            if getattr(sys, 'frozen', False):
                base_path = getattr(sys, '_MEIPASS', None)
                if base_path:
                    browsers_path = os.path.join(base_path, "playwright_browsers")
                    if os.path.exists(browsers_path):
                        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
                        logger.debug(f"Playwright browsers path: {browsers_path}")
            
            # Set PLAYWRIGHT_DRIVER_PATH to the bundled driver location
            driver_path = _get_playwright_driver_path()
            logger.debug(f"Playwright driver path: {driver_path}")
            os.environ["PLAYWRIGHT_DRIVER_PATH"] = driver_path
            
            from playwright.async_api import async_playwright
            
            # Ensure mod directory exists
            self.mod_directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Mod directory ensured: {self.mod_directory}")
            
            async with async_playwright() as p:
                logger.info("Launching Playwright Chromium browser (visible window for Cloudflare verification)")
                # Launch browser in visible mode so user can complete Cloudflare verification
                # Using full Chromium instead of headless shell for Cloudflare compatibility
                browser = await p.chromium.launch(
                    headless=False,  # Visible window for user interaction
                    executable_path=os.path.join(
                        os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""),
                        "chromium-1208",
                        "chrome-win64",
                        "chrome.exe"
                    ) if os.environ.get("PLAYWRIGHT_BROWSERS_PATH") else None
                )
                logger.info("Chromium browser launched successfully (visible window)")
                
                context = await browser.new_context()
                logger.debug("Created new browser context")
                
                page = await context.new_page()
                logger.debug("Created new page")
                
                # Set a larger viewport for better visibility
                page.set_viewport_size({"width": 1280, "height": 720})  # type: ignore[misc]
                logger.debug("Set viewport size to 1280x720")
                
                # Set download behavior to auto-download without prompting
                # This tells Playwright to automatically save downloads to the default location
                # We'll handle the filename in the download handler
                page.set_default_navigation_timeout(120000)
                page.set_default_timeout(120000)
                
                # Get project details from CFWidget API
                # Get project details from CFWidget API
                try:
                    from .cfwidget_api import CFWidgetAPI
                except ImportError as e:
                    logger.error(f"CFWidgetAPI module not available: {e}")
                    return (None, "CFWidgetAPI module not available")
                cfapi = CFWidgetAPI()
                cfapi = CFWidgetAPI()
                project_id = mod_info.get("mod_id")
                logger.info(f"Fetching project details from CFWidget API for mod_id: {project_id}")
                
                if not project_id:
                    logger.error("No mod_id provided in mod_info")
                    return (None, "No mod_id provided")
                
                project_details = cfapi.get_project_details(project_id)
                
                if not project_details:
                    logger.error(f"Failed to get project details from CFWidget API for mod_id: {project_id}")
                    return (None, "Failed to get project details from CFWidget API")
                
                logger.info(f"Project details retrieved: {project_details.get('name', 'Unknown')}")
                
                # Get download URL from project details
                if "download" not in project_details:
                    logger.error("No download URL available in project details from CFWidget API")
                    return (None, "No download URL available in project details")
                
                download_url = project_details["download"].get("url", "")
                if not download_url:
                    logger.error("No download URL in project details from CFWidget API")
                    return (None, "No download URL in project details")
                
                logger.info(f"CFWidget download URL: {download_url}")
                
                # Convert /files/ to /download/ for direct download page
                download_url = self.convert_cfwidget_files_to_download_url(download_url)
                logger.info(f"Converted download URL: {download_url}")
                
                # Set up download listener
                download_path = None
                download_event = asyncio.Event()
                
                def handle_download(download):
                    """Handle download event."""
                    async def _handle():
                        nonlocal download_path
                        try:
                            # Use the suggested filename from Playwright - this is the actual downloaded filename
                            # We should NOT try to match against expected_filename because:
                            # 1. The download URL may have changed (new version)
                            # 2. Playwright will abort if the filename doesn't match what was suggested
                            # 3. We want to keep the new filename from the download
                            final_filename = download.suggested_filename
                            logger.debug(f"Download suggested filename: {final_filename}")
                            
                            # Wait for download to complete and save with the suggested filename
                            await download.save_as(self.mod_directory / final_filename)
                            download_path = self.mod_directory / final_filename
                            logger.info(f"Downloaded via Playwright: {download_path}")
                            download_event.set()
                        except Exception as e:
                            logger.error(f"Error saving download: {e}")
                            download_event.set()
                    
                    asyncio.create_task(_handle())
                
                page.on("download", handle_download)
                
                # Set up debugging listeners
                # Log all network requests
                page.on("request", lambda request: logger.debug(f"Network request: {request.method} {request.url}"))
                
                # Log all network responses
                page.on("response", lambda response: logger.debug(f"Network response: {response.status} {response.url}"))
                
                # Log console messages (JavaScript console.log, error, etc.)
                page.on("console", lambda msg: logger.debug(f"Console [{msg.type}]: {msg.text}"))
                
                # Log page errors
                page.on("pageerror", lambda error: logger.error(f"Page error: {error}"))
                
                # Log request failures
                page.on("requestfailed", lambda request: logger.error(f"Request failed: {request.url} - {request.failure}"))
                
                logger.info(f"Navigating to download page: {download_url}")
                logger.debug(f"Waiting for page to load with wait_until='domcontentloaded', timeout=60000ms")
                
                # Navigate to the download page
                try:
                    await page.goto(download_url, wait_until="domcontentloaded", timeout=60000)
                    logger.info(f"Page loaded successfully")
                    logger.debug(f"Page URL after goto: {page.url}")
                    title = await page.title()
                    logger.debug(f"Page title after goto: {title if title else 'N/A'}")
                    
                    # Wait for download to complete (with timeout)
                    # We use a shorter timeout since the download should start quickly
                    try:
                        await asyncio.wait_for(download_event.wait(), timeout=30)
                        logger.info("Download event received")
                    except asyncio.TimeoutError:
                        logger.warning("Download event timeout - download may still be in progress")
                    
                    # Check if download completed
                    if download_path and download_path.exists():
                        logger.info(f"Playwright download completed successfully: {download_path}")
                        await browser.close()
                        # Report progress via callback
                        if progress_callback:
                            progress_callback(mod_info, True, str(download_path), "")
                        return (download_path, "")
                    
                    # Wait for network to be idle
                    try:
                        await page.wait_for_load_state("networkidle", timeout=60000)
                        logger.info(f"Network is idle")
                        logger.debug(f"Page URL after networkidle: {page.url}")
                        title = await page.title()
                        logger.debug(f"Page title after networkidle: {title if title else 'N/A'}")
                    except Exception as e:
                        logger.warning(f"Network idle timeout: {e}")
                    
                    # Wait for download button to appear (handles Cloudflare redirect)
                    try:
                        # Wait for any link that could be a download button
                        await page.wait_for_selector("a", timeout=60000)
                        logger.info(f"Any link found on page")
                        logger.debug(f"Page URL after waiting for link: {page.url}")
                        title = await page.title()
                        logger.debug(f"Page title after waiting for link: {title if title else 'N/A'}")
                        
                        # Get all links on the page
                        links = await page.query_selector_all("a")
                        logger.debug(f"Found {len(links)} links on page")
                        for i, link in enumerate(links[:5]):  # Log first 5 links
                            href = link.get_attribute("href")
                            text = await link.inner_text()
                            logger.debug(f"Link {i+1}: href={href}, text={text[:50]}...")
                        
                        # Try to find download button
                        await page.wait_for_selector("a.btn", timeout=30000)
                        logger.info(f"Download button found")
                    except Exception as e:
                        logger.warning(f"Download button not found: {e}")
                        # Try to find any download link
                        try:
                            await page.wait_for_selector("a[href*='download']", timeout=30000)
                            logger.info(f"Download link found")
                        except Exception as e2:
                            logger.error(f"Download link not found: {e2}")
                            logger.error(f"Page URL: {page.url}")
                            title = await page.title()
                            logger.error(f"Page title: {title if title else 'N/A'}")
                            # Don't close browser yet - user may still be completing verification
                            # Just wait for download to complete
                            logger.info("Waiting for download to complete...")
                except Exception as e:
                    logger.error(f"Error navigating to download page: {e}")
                    logger.error(f"Page URL: {download_url}")
                    title = await page.title() if page else None
                    logger.error(f"Page title: {title if title else 'N/A'}")
                    
                    # Log full HTML content for debugging
                    try:
                        html_content = await page.content()
                        logger.debug(f"Page HTML content (first 1000 chars): {html_content[:1000]}")
                        logger.debug(f"Full page HTML saved to debug_html.txt")
                        with open(self.mod_directory / "debug_html.txt", "w", encoding="utf-8") as f:
                            f.write(html_content)
                    except Exception as html_error:
                        logger.error(f"Could not get page HTML: {html_error}")
                    
                    # Take screenshot for debugging
                    try:
                        screenshot_path = self.mod_directory / "debug_screenshot.png"
                        await page.screenshot(path=str(screenshot_path))
                        logger.info(f"Page screenshot saved to {screenshot_path}")
                    except Exception as screenshot_error:
                        logger.error(f"Could not take screenshot: {screenshot_error}")
                    
                    await browser.close()
                    return (None, f"Failed to navigate to download page: {str(e)}")
                
                # Check if download completed
                if download_path and download_path.exists():
                    logger.info(f"Playwright download completed successfully: {download_path}")
                    await browser.close()
                    # Report progress via callback
                    if progress_callback:
                        progress_callback(mod_info, True, str(download_path), "")
                    return (download_path, "")
                else:
                    logger.error("Download failed - no file created")
                    await browser.close()
                    # Report progress via callback
                    if progress_callback:
                        progress_callback(mod_info, False, "", "Download failed - no file created")
                    return (None, "Download failed - no file created")
                    
        except Exception as e:
            logger.error(f"Error downloading mod via Playwright: {e}")
            # Report progress via callback
            if progress_callback:
                progress_callback(mod_info, False, "", str(e))
            return (None, str(e))
    
    def convert_cfwidget_files_to_download_url(self, url: str) -> str:
        """
        Convert CFWidget files URL to download URL.
        
        CFWidget returns URLs like:
            https://www.curseforge.com/hytale/mods/nick-name-changer/files/7663990
        
        Playwright needs to load:
            https://www.curseforge.com/hytale/mods/nick-name-changer/download/7663990
        
        Args:
            url: The CFWidget URL with /files/ path
            
        Returns:
            URL with /download/ path
        """
        # Replace /files/ with /download/
        return url.replace('/files/', '/download/')
    
    def download_mod_sync(self, mod_info: Dict[str, Any], progress_callback=None) -> Tuple[Optional[Path], str]:
        """
        Synchronous wrapper for download_mod.
        
        Args:
            mod_info: Dict with mod_id, filename
            progress_callback: Optional callback(mod_info, success, path, error) called when download completes
            
        Returns:
            Tuple of (downloaded_path, error_message)
        """
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.download_mod(mod_info, progress_callback))
            return result
        finally:
            loop.close()