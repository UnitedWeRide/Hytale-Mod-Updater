"""
CurseForge API Service Module

This module provides functionality for interacting with the CurseForge API
to match mod fingerprints to CurseForge Mod IDs.
"""

import requests
import logging
import time
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class CurseForgeAPI:
    """Service for interacting with the CurseForge API."""
    
    BASE_URL = "https://api.curseforge.com"
    
    def __init__(self, api_key: str, rate_limit_enabled: bool = True):
        """
        Initialize the CurseForge API service.
        
        Args:
            api_key: The CurseForge API key
            rate_limit_enabled: Whether to enforce rate limiting (default: True)
                               Set to False for full-speed operations
        """
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self._api_lock = threading.Lock()
        self._last_api_time = 0
        self._api_rate_limit_delay = 0.5  # 500ms delay between API calls
        self._rate_limit_enabled = rate_limit_enabled
    
    def _enforce_api_rate_limit(self):
        """Enforce rate limiting between API calls."""
        if not self._rate_limit_enabled:
            return
        
        with self._api_lock:
            current_time = time.time()
            elapsed = current_time - self._last_api_time
            
            if elapsed < self._api_rate_limit_delay:
                sleep_time = self._api_rate_limit_delay - elapsed
                time.sleep(sleep_time)
            
            self._last_api_time = time.time()
    
    def _make_request(self, method: str, endpoint: str,
                      params: Optional[Dict] = None,
                      json_data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a request to the CurseForge API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            
        Returns:
            JSON response as dict, or None if request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        # Enforce rate limit before making request
        self._enforce_api_rate_limit()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("Rate limited by CurseForge API")
                return None
            elif response.status_code == 403:
                logger.error("Invalid API key or insufficient permissions")
                return None
            else:
                logger.error(f"API request failed with status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None
    
    def get_games(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of available games from CurseForge.
        
        Returns:
            List of game dictionaries with id and name, or None if request fails
        """
        response = self._make_request("GET", "/v1/games")
        
        if response and "data" in response:
            return response["data"]
        return None
    
    def get_game_by_id(self, game_id: int) -> Optional[Dict[str, Any]]:
        """
        Get game details by ID.
        
        Args:
            game_id: The game ID
            
        Returns:
            Game dictionary, or None if request fails
        """
        response = self._make_request("GET", f"/v1/games/{game_id}")
        
        if response and "data" in response:
            return response["data"]
        return None
    
    def match_fingerprints(self, game_id: int, fingerprints: List[int]) -> Optional[Dict[str, Any]]:
        """
        Match fingerprints to CurseForge mods.
        
        Args:
            game_id: The game ID
            fingerprints: List of fingerprints to match
            
        Returns:
            Response with exact matches, or None if request fails
        """
        json_data = {
            "fingerprints": fingerprints
        }
        
        response = self._make_request("POST", f"/v1/fingerprints/{game_id}", json_data=json_data)
        
        if response and "data" in response:
            return response["data"]
        return None
    
    def fuzzy_match_fingerprints(self, game_id: int, 
                                  fingerprints: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Fuzzy match fingerprints to CurseForge mods.
        
        Args:
            game_id: The game ID
            fingerprints: List of fingerprint queries with foldername and fingerprints
            
        Returns:
            Response with fuzzy matches, or None if request fails
        """
        json_data = {
            "gameId": game_id,
            "fingerprints": fingerprints
        }
        
        response = self._make_request("POST", "/v1/fingerprints/fuzzy", json_data=json_data)
        
        if response and "data" in response:
            return response["data"]
        return None
    
    def get_mod_details(self, mod_id: int) -> Optional[Dict[str, Any]]:
        """
        Get mod details by ID.
        
        Args:
            mod_id: The mod ID
            
        Returns:
            Mod details dictionary, or None if request fails
        """
        response = self._make_request("GET", f"/v1/mods/{mod_id}")
        
        if response and "data" in response:
            return response["data"]
        return None
    
    def get_mod_files(self, mod_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get all files for a mod.
        
        Args:
            mod_id: The mod ID
            
        Returns:
            List of file dictionaries, or None if request fails
        """
        response = self._make_request("GET", f"/v1/mods/{mod_id}/files")
        
        if response is None:
            return None
        if "data" not in response:
            logger.warning(f"Missing 'data' key in response for get_mod_files (mod_id={mod_id})")
            return None
        return response["data"]
    
    def get_file_details(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get file details by ID.
        
        Args:
            file_id: The file ID
            
        Returns:
            File details dictionary, or None if request fails
        """
        response = self._make_request("GET", f"/v1/mods/files/{file_id}")
        
        if response is None:
            return None
        if "data" not in response:
            logger.warning(f"Missing 'data' key in response for get_file_details (file_id={file_id})")
            return None
        return response["data"]
    
    def search_mods_by_game(self, game_id: int, index: int = 0,
                            page_size: int = 50) -> Optional[Dict[str, Any]]:
        """
        Search for mods by game ID with pagination.
        
        Args:
            game_id: The game ID
            index: Zero-based index of first item to include (default 0)
            page_size: Number of items to include (default 50, max 50)
            
        Returns:
            Response with data and pagination info, or None if request fails
        """
        params = {
            "gameId": game_id,
            "index": index,
            "pageSize": page_size
        }
        
        response = self._make_request("GET", "/v1/mods/search", params=params)
        
        if response and "data" in response:
            return response
        return None
    
    def get_download_url(self, mod_id: int, file_id: int) -> Optional[str]:
        """
        Get direct download URL for a specific mod file.
        
        Args:
            mod_id: The CurseForge mod ID
            file_id: The CurseForge file ID
            
        Returns:
            Direct download URL string, or None if request fails
        """
        response = self._make_request("GET", f"/v1/mods/{mod_id}/files/{file_id}/download-url")
        
        if response and "data" in response:
            return response["data"]
        return None