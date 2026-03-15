"""
CFWidget API Service Module

This module provides functionality for interacting with the CFWidget API
to retrieve CurseForge project details and download URLs.
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class CFWidgetAPI:
    """Service for interacting with the CFWidget API."""
    
    BASE_URL = "https://api.cfwidget.com"
    
    def __init__(self):
        """
        Initialize the CFWidget API service.
        """
        self.headers = {
            "Accept": "application/json"
        }
    
    def get_project_details(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Get project details from CFWidget API.
        
        Args:
            project_id: The CurseForge project ID
            
        Returns:
            Project details dictionary, or None if request fails
        """
        try:
            url = f"{self.BASE_URL}/{project_id}"
            # Validate URL to prevent SSRF attacks
            if not url.startswith(self.BASE_URL):
                logger.error(f"Invalid URL: {url}")
                return None
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Project {project_id} not found in CFWidget database")
                return None
            else:
                logger.error(f"CFWidget API request failed with status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching project details from CFWidget API: {e}")
            return None
    
    def get_download_url(self, project_id: int) -> Optional[str]:
        """
        Get direct download URL for the latest release from CFWidget API.
        
        Args:
            project_id: The CurseForge project ID
            
        Returns:
            Download URL string, or None if not available
        """
        project_details = self.get_project_details(project_id)
        
        if project_details and "download" in project_details:
            download_url = project_details["download"].get("url", "")
            if download_url:
                # Convert /files/ to /download/ for direct download
                download_url = self.convert_cfwidget_files_to_download_url(download_url)
                return download_url
        
        return None
    
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