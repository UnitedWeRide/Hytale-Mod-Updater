# pyi_rth_platform.py
# PyInstaller runtime hook to ensure platform module is properly loaded
# This fixes the AttributeError: module 'platform' has no attribute 'system' error

import sys
import os

def _patch_platform_module():
    """Ensure platform module is properly loaded with all its attributes."""
    try:
        # Force import platform module
        import platform
        
        # Verify platform.system() exists
        if not hasattr(platform, 'system'):
            # Re-import platform module to ensure it's fully loaded
            import importlib
            importlib.reload(platform)
            
            # If still missing, try to import it fresh
            if not hasattr(platform, 'system'):
                # Force re-import by removing from sys.modules
                if 'platform' in sys.modules:
                    del sys.modules['platform']
                import platform
                
    except Exception as e:
        # Log error but don't crash
        sys.stderr.write(f"Warning: Could not patch platform module: {e}\n")

# Apply the patch
_patch_platform_module()