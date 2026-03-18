"""
Platform Detection Module
Centralized OS detection for cross-platform compatibility.
"""

import sys
from pathlib import Path


class PlatformDetector:
    """Detect and provide platform-specific information."""
    
    PLATFORM_WINDOWS = "windows"
    PLATFORM_LINUX = "linux"
    PLATFORM_MAC = "mac"
    
    def __init__(self):
        self._platform = self._detect_platform()
    
    def _detect_platform(self) -> str:
        """Detect the current platform."""
        if sys.platform == "win32":
            return self.PLATFORM_WINDOWS
        elif sys.platform == "linux":
            return self.PLATFORM_LINUX
        elif sys.platform == "darwin":
            return self.PLATFORM_MAC
        else:
            raise NotImplementedError(f"Unsupported platform: {sys.platform}")
    
    @property
    def platform(self) -> str:
        """Get current platform."""
        return self._platform
    
    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self._platform == self.PLATFORM_WINDOWS
    
    @property
    def is_linux(self) -> bool:
        """Check if running on Linux."""
        return self._platform == self.PLATFORM_LINUX
    
    @property
    def is_mac(self) -> bool:
        """Check if running on macOS."""
        return self._platform == self.PLATFORM_MAC
    
    def get_browser_executable_path(self, browsers_base_path: Path) -> Path:
        """
        Get platform-specific browser executable path.
        
        Args:
            browsers_base_path: Base path to browser binaries
            
        Returns:
            Path to browser executable
        """
        browsers_path = Path(browsers_base_path)
        if self.is_windows:
            return browsers_path / "chromium-1208" / "chrome-win64" / "chrome.exe"
        elif self.is_linux:
            return browsers_path / "chromium-1208" / "chrome-linux64" / "chrome"
        else:
            raise NotImplementedError(f"Browser not supported on {self._platform}")
    
    def get_browser_directory_name(self) -> str:
        """Get the browser directory name for current platform."""
        if self.is_windows:
            return "chrome-win64"
        elif self.is_linux:
            return "chrome-linux64"
        else:
            raise NotImplementedError(f"Browser not supported on {self._platform}")