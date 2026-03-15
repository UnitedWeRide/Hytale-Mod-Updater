"""
Keyring Manager - Secure API Key Storage

This module handles secure storage and retrieval of the CurseForge API key
using the system's keyring service.
"""

import keyring  # type: ignore  # keyring is installed via requirements.txt
import logging

logger = logging.getLogger(__name__)


class KeyringManager:
    """Manage API key storage in system keyring."""
    
    SERVICE_NAME = "HytaleModUpdater"
    KEY_NAME = "curseforge_api_key"
    
    @staticmethod
    def get_api_key() -> str | None:
        """
        Retrieve API key from system keyring.
        
        Returns:
            str | None: The API key if found, None otherwise
        """
        try:
            key = keyring.get_password(KeyringManager.SERVICE_NAME, KeyringManager.KEY_NAME)
            if key:
                logger.info("API key retrieved from keyring")
            else:
                logger.info("No API key found in keyring")
            return key
        except (OSError, IOError, keyring.errors.KeyringError) as e:
            logger.error(f"Failed to retrieve API key from keyring: {e}")
            return None
    
    @staticmethod
    def set_api_key(api_key: str) -> bool:
        """
        Store API key in system keyring.
        
        Args:
            api_key: The API key to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            keyring.set_password(KeyringManager.SERVICE_NAME, KeyringManager.KEY_NAME, api_key)
            logger.info("API key stored in keyring")
            return True
        except (OSError, IOError, keyring.errors.KeyringError) as e:
            logger.error(f"Failed to store API key in keyring: {e}")
            return False
    
    @staticmethod
    def delete_api_key() -> bool:
        """
        Remove API key from system keyring.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            keyring.delete_password(KeyringManager.SERVICE_NAME, KeyringManager.KEY_NAME)
            logger.info("API key deleted from keyring")
            return True
        except (OSError, IOError, keyring.errors.KeyringError) as e:
            logger.error(f"Failed to delete API key from keyring: {e}")
            return False
