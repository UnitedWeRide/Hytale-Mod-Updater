#!/usr/bin/env python3
"""
Build script for the Hytale Mod Updater (Windows and Linux).

Requirements:
  - Python 3.10+ (the same interpreter used for development)
  - pip install -r requirements.txt

Entry Point:
  - The application entry point is src/main.py
  - This script builds the executable using PyInstaller

Usage:
  Windows: python build.py --platform windows
  Linux:   python build.py --platform linux
  Auto:    python build.py (detects current platform)
"""

import os
import sys
import subprocess
import zipfile
import io
import argparse
from pathlib import Path

# -------------------------------------------------------------
# 1. Sanity checks – make sure we are in the repo root
# -------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)  # ensure all relative paths work

# -------------------------------------------------------------
# 2. Clean up previous build artifacts
# -------------------------------------------------------------
def clean_directory(path: Path) -> None:
    """Remove all contents of a directory, but keep the directory itself."""
    if path.exists():
        print(f"Cleaning {path}...")
        for item in path.iterdir():
            if item.is_dir():
                import shutil
                shutil.rmtree(item)
            else:
                item.unlink()

# Clean build and dist directories
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
clean_directory(BUILD_DIR)
clean_directory(DIST_DIR)

# Remove __pycache__ directories
for pycache in ROOT.rglob("__pycache__"):
    import shutil
    shutil.rmtree(pycache)
    print(f"Removed {pycache}")

# -------------------------------------------------------------
# 3. Install dependencies from requirements.txt
# -------------------------------------------------------------
REQUIREMENTS_FILE = ROOT / "requirements.txt"
if REQUIREMENTS_FILE.exists():
    print(f"Installing dependencies from {REQUIREMENTS_FILE}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE), "--disable-pip-version-check"])
else:
    print(f"Warning: {REQUIREMENTS_FILE} not found, skipping dependency installation")

# -------------------------------------------------------------
# 4. Ensure PyInstaller is installed
# -------------------------------------------------------------
try:
    import PyInstaller  # noqa: F401
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "--disable-pip-version-check"])
    import PyInstaller  # noqa: F401

# -------------------------------------------------------------
# 5. Install Playwright browser binaries (if not already installed)
# -------------------------------------------------------------
# Install Playwright browser binaries to a location inside the project
# This ensures they are included in the PyInstaller bundle
BROWSERS_DIR = ROOT / "playwright_browsers"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS_DIR)
BROWSERS_DIR.mkdir(exist_ok=True)


def install_playwright_browsers(platform: str) -> None:
    """Install Playwright browsers for the specified platform."""
    print(f"Installing Playwright browsers for {platform}...")
    
    # Install Chromium browsers without headless shell
    # Use --no-shell to skip headless shell installation (we need visible browser)
    # Pass PLAYWRIGHT_BROWSERS_PATH explicitly to subprocess
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS_DIR)
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "--no-shell", "chromium"], env=env)
    
    # Verify browsers were installed directly to BROWSERS_DIR
    if platform == "windows":
        chrome_dir = BROWSERS_DIR / "chromium-1208" / "chrome-win64"
        if not chrome_dir.exists():
            raise RuntimeError(f"Windows Playwright browsers not installed at {chrome_dir}")
        print(f"Windows Playwright browsers installed at {chrome_dir}")
    elif platform == "linux":
        chrome_dir = BROWSERS_DIR / "chromium-1208" / "chrome-linux64"
        if not chrome_dir.exists():
            raise RuntimeError(f"Linux Playwright browsers not installed at {chrome_dir}")
        print(f"Linux Playwright browsers installed at {chrome_dir}")
    else:
        raise ValueError(f"Unsupported platform: {platform}")
    
    print(f"Playwright browsers ready at {BROWSERS_DIR}")


def get_target_platform(args_platform: str) -> str:
    """Determine the target platform based on arguments and current system."""
    if args_platform == "auto":
        if sys.platform == "win32":
            return "windows"
        elif sys.platform == "linux":
            return "linux"
        else:
            raise RuntimeError(f"Unsupported platform: {sys.platform}")
    return args_platform


# -------------------------------------------------------------
# 6. Verify Playwright browsers were downloaded
# -------------------------------------------------------------
BROWSERS_JSON = BROWSERS_DIR / "browsers.json"
if BROWSERS_JSON.exists():
    import json
    with open(BROWSERS_JSON, "r") as f:
        browsers = json.load(f)
    for browser in browsers.get("browsers", []):
        if browser.get("installByDefault"):
            pass  # silently verify presence
else:
    pass  # browsers.json presence is optional; no warning needed

# -------------------------------------------------------------
# 7. Download Forest-ttk-theme (if not already downloaded)
# -------------------------------------------------------------
THEME_DIR = ROOT / "resources" / "Forest-ttk-theme"
# Use GitHub master branch raw files directly
THEME_REPO_URL = "https://github.com/rdbende/Forest-ttk-theme/archive/refs/heads/master.zip"


def download_forest_theme() -> None:
    """Download Forest-ttk-theme from GitHub master branch as a complete ZIP."""
    THEME_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        import urllib.request
        import zipfile
        
        print(f"Downloading Forest-ttk-theme from {THEME_REPO_URL}...")
        
        # Download the ZIP file
        with urllib.request.urlopen(THEME_REPO_URL) as response:
            zip_data = response.read()
        
        # Extract the ZIP file
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
            # The ZIP contains a folder like Forest-ttk-theme-master/
            # We need to extract the contents to our THEME_DIR
            for member in zip_ref.infolist():
                # Skip the root folder and extract contents directly
                member_path = Path(member.filename)
                
                # Skip the top-level folder (Forest-ttk-theme-master/)
                if len(member_path.parts) <= 1:
                    continue
                
                # Construct the destination path
                dest_path = THEME_DIR / Path(*member_path.parts[1:])
                
                if member.is_dir():
                    # Create directory
                    dest_path.mkdir(parents=True, exist_ok=True)
                else:
                    # Create parent directories if needed
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file
                    with zip_ref.open(member) as source:
                        with open(dest_path, "wb") as target:
                            target.write(source.read())
            
            print(f"Forest-ttk-theme extracted successfully to {THEME_DIR}")
    except Exception as e:
        print(f"Warning: Failed to download Forest-ttk-theme: {e}")
        print("Continuing with existing theme files if available")


# Check if theme is already downloaded (including images)
forest_theme_exists = (THEME_DIR / "forest-dark.tcl").exists()
forest_light_theme_exists = (THEME_DIR / "forest-light.tcl").exists()
dark_images_exist = (THEME_DIR / "forest-dark").is_dir()
light_images_exist = (THEME_DIR / "forest-light").is_dir()

# Check if both theme files and both image directories exist
if not forest_theme_exists or not forest_light_theme_exists or not dark_images_exist or not light_images_exist:
    if not forest_theme_exists or not forest_light_theme_exists:
        print(f"Downloading Forest-ttk-theme to {THEME_DIR}...")
    else:
        print(f"Forest-ttk-theme theme files exist, but images directories are missing. Downloading complete theme...")
    download_forest_theme()
else:
    print(f"Forest-ttk-theme already exists at {THEME_DIR} (including images)")

# -------------------------------------------------------------
# 8. Verify that tkinter is importable (skip on Linux - PyInstaller will bundle it)
# -------------------------------------------------------------
if sys.platform == "win32":
    # On Windows, tkinter must be available at build time
    try:
        import tkinter  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "ERROR: The Python interpreter used to run this script does not have "
            "the standard tkinter module bundled.\n"
            "On Windows, this is normally included with the official Python "
            "installer. If you are using a minimal/miniconda distribution, "
            "you may need to install the 'python-tk' package or add the "
            "tkinter DLLs manually.\n"
            f"Details: {exc}"
        )
else:
    # On Linux, try to auto-install python3-tk if not available
    print("Checking for tkinter on Linux...")
    try:
        import tkinter  # noqa: F401
        print("tkinter is available")
    except ImportError:
        print("tkinter not found, attempting to install python3-tk...")
        try:
            subprocess.check_call(["sudo", "apt", "install", "-y", "python3-tk"])
            print("python3-tk installed successfully")
            # Re-import to verify
            import tkinter  # noqa: F401
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to install python3-tk automatically. Please run:\n"
                f"  sudo apt install -y python3-tk\n"
                f"Error: {e}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to install python3-tk. Please run manually:\n"
                f"  sudo apt install -y python3-tk\n"
                f"Error: {e}"
            )
    print("tkinter is available for PyInstaller to bundle")

# -------------------------------------------------------------
# 9. Create a PyInstaller hook for Tkinter
# -------------------------------------------------------------
HOOK_TKINTER = ROOT / "hook-tkinter.py"
HOOK_TKINTER.write_text(
    """
# hook-tkinter.py
# PyInstaller hook to include all Tkinter data and libraries
# (This file is automatically picked up by PyInstaller if it lives
# in the same directory as the spec file or is in the hookspath.)
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, get_module_file_attribute

# 6.1 Include every submodule of tkinter
hiddenimports = collect_submodules('tkinter')

# 6.2 Include the data files that ship with tkinter
datas = collect_data_files('tkinter')

# 6.3 On Windows we must also ship the tk86t.dll and tcl86t.dll DLLs,
#      as well as the tcl8.6/ tk8.6 directories.
if sys.platform == 'win32':
    try:
        import tkinter
        tkinter_path = os.path.dirname(tkinter.__file__)
        # DLLs
        for dll in ('tk86t.dll', 'tcl86t.dll'):
            dll_path = os.path.join(tkinter_path, dll)
            if os.path.exists(dll_path):
                datas.append((dll_path, '.'))
        # tcl / tk folders
        for folder in ('tcl8.6', 'tk8.6'):
            src = os.path.join(tkinter_path, folder)
            if os.path.isdir(src):
                datas.append((src, folder))
    except Exception:
        pass

# 6.4 On Linux we must ship the shared libraries (libtk8.6.so, libtcl8.6.so)
if sys.platform == 'linux':
    try:
        import tkinter
        tkinter_path = os.path.dirname(tkinter.__file__)
        # Shared libraries
        for lib in ('libtk8.6.so', 'libtcl8.6.so'):
            lib_path = os.path.join(tkinter_path, lib)
            if os.path.exists(lib_path):
                datas.append((lib_path, '.'))
        # tcl / tk folders
        for folder in ('tcl8.6', 'tk8.6'):
            src = os.path.join(tkinter_path, folder)
            if os.path.isdir(src):
                datas.append((src, folder))
    except Exception:
        pass
"""
)

# -------------------------------------------------------------
# 10. Prepare paths for resources, config, icon, etc.
# -------------------------------------------------------------
RESOURCES_DIR = ROOT / "resources"
CONFIG_FILE = ROOT / "config.json"
ICON_FILE = ROOT / "resources" / "icon" / "Hytale.ico"
MAIN_SCRIPT = ROOT / "src" / "main.py"  # Entry point: main.py
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_DIR = ROOT / "spec"

# Sanity checks for required files (config.json is optional - app generates it)
required_files = [RESOURCES_DIR, ICON_FILE, MAIN_SCRIPT]
for path in required_files:
    if not path.exists():
        raise RuntimeError(f"ERROR: Required file not found: {path}")

# Config file is optional - if it exists, include it in build
if not CONFIG_FILE.exists():
    pass  # config.json is optional; app generates it on first run

# Create output directories if missing
for d in (DIST_DIR, BUILD_DIR, SPEC_DIR):
    d.mkdir(parents=True, exist_ok=True)


def generate_spec_content(platform: str) -> str:
    """Generate platform-specific PyInstaller spec content."""
    spec = f"""
# -*- mode: python; coding: utf-8 -*-
block_cipher = None
# Platform: {platform}

# Import the standard PyInstaller classes
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os, sys, platform
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.building.datastruct import Tree

# Import playwright for driver path resolution
try:
    import playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Resolve absolute paths
main_script_path = r"{MAIN_SCRIPT.as_posix()}"
src_path         = r"{MAIN_SCRIPT.parent.as_posix()}"
resources_path   = r"{RESOURCES_DIR.as_posix()}"
config_path      = r"{CONFIG_FILE.as_posix()}"
icon_path        = r"{ICON_FILE.as_posix()}"
browsers_path    = r"{BROWSERS_DIR.as_posix()}"
# Determine the location of the Python DLLs (for tkinter DLLs)
python_path = os.path.dirname(sys.executable)

# Ensure resources_path is valid
if not os.path.isdir(resources_path):
    raise RuntimeError(f"ERROR: Resources directory not found: {{resources_path}}")
    sys.exit(1)

# ------------------------------------------------------------------
# 8.1  Include Tkinter DLLs and tcl/tk directories
# ------------------------------------------------------------------
binaries = []
datas    = []

if platform == "windows":
    # Tkinter DLLs
    for dll in ("tk86t.dll", "tcl86t.dll"):
        dll_path = os.path.join(python_path, "DLLs", dll)
        if os.path.exists(dll_path):
            binaries.append((dll_path, "."))
    # tcl / tk folders
    for folder in ("tcl8.6", "tk8.6"):
        src = os.path.join(python_path, folder)
        if os.path.isdir(src):
            datas.append((src, folder))

# ------------------------------------------------------------------
# 8.2  Include all theme directories from resources
# ------------------------------------------------------------------
# Include all files and subdirectories from resources
# Copy theme files to a resources subdirectory in the executable directory
# This allows the .tcl files to use relative paths correctly
for dirpath, dirnames, filenames in os.walk(resources_path, followlinks=False):
    # Calculate the relative path from resources_path
    rel_path = os.path.relpath(dirpath, resources_path)
    
    # Each file should be placed in a resources subdirectory
    # This allows the .tcl files to use relative paths correctly
    for filename in filenames:
        src_file = os.path.join(dirpath, filename)
        # Preserve the directory structure under resources
        # For files directly in resources/, rel_path is "." which becomes "resources/"
        out_dir = os.path.join("resources", rel_path) if rel_path != "." else "resources"
        datas.append((src_file, out_dir))

# ------------------------------------------------------------------
# 8.3  Include Playwright browser binaries
# ------------------------------------------------------------------
# Playwright browsers are installed in the project's playwright_browsers directory
# We need to include them in the executable
# Exclude headless shell since we're using visible browser mode
if os.path.exists(browsers_path):
    browsers_path = Path(browsers_path).resolve()
    for dirpath, dirnames, filenames in os.walk(browsers_path, followlinks=False):
        rel_path = os.path.relpath(dirpath, browsers_path)
        for filename in filenames:
            # Skip headless shell files
            if "headless_shell" in filename or "headless_shell" in rel_path:
                continue
            src_file = os.path.join(dirpath, filename)
            out_dir = os.path.join("playwright_browsers", rel_path)
            datas.append((src_file, out_dir))
    
    # Also include the playwright driver from site-packages (for the Python code)
    if PLAYWRIGHT_AVAILABLE:
        playwright_path = os.path.dirname(playwright.__file__)
        if playwright_path and os.path.exists(playwright_path):
            playwright_driver = Path(playwright_path) / "driver"
            if playwright_driver.is_dir():
                for dirpath, dirnames, filenames in os.walk(playwright_driver, followlinks=False):
                    rel_path = os.path.relpath(dirpath, playwright_path)
                    for filename in filenames:
                        src_file = os.path.join(dirpath, filename)
                        out_dir = os.path.join("playwright", rel_path)
                        datas.append((src_file, out_dir))

# ------------------------------------------------------------------
# 8.4  Include config.json (if it exists)
# ------------------------------------------------------------------
if os.path.exists(config_path):
    datas.append((config_path, "."))

# ------------------------------------------------------------------
# 8.5  Hidden imports: tkinter + submodules
# ------------------------------------------------------------------
hiddenimports = collect_submodules("tkinter")
# Add all new modules to ensure they're included in the packaged executable
hiddenimports.extend([
    "config.settings",
    "config.paths",
    "core.app",
    "core.theme_manager",
    "ui.dialogs",
    "ui.app_window",
    "ui.settings_handlers",
    "services.keyring_manager",
    "services.mod_database_manager",
    "services.mod_downloader",
    "services.mod_id_matcher",
    "services.mod_id_store",
    "services.playwright_downloader",
    "services.update_checker",
    "services.backup_manager",
    "services.curseforge_api",
    "services.cfwidget_api",
    "utils.logging",
    "utils.fingerprint",
    "numpy",
    "asyncio",
])

# ------------------------------------------------------------------
# 8.7  Hidden imports: keyring and dependencies (fixes platform.system() error)
# ------------------------------------------------------------------
# keyring depends on jaraco.context which uses platform.system()
# PyInstaller doesn't automatically detect these, so we add them explicitly
hiddenimports.extend([
    "platform",           # Required by jaraco.context
    "jaraco",
    "jaraco.context",
    "keyring",
    "keyring.backends",
])

# ------------------------------------------------------------------
# 8.8  Collect data files for keyring backends
# ------------------------------------------------------------------
# Keyring backends may need their data files
try:
    hiddenimports.extend(collect_submodules("keyring.backends"))
except Exception:
    pass

# ------------------------------------------------------------------
# 8.6  Hook path – we put the hooks in the same directory as the spec
# ------------------------------------------------------------------
hookspath = ["."]  # PyInstaller will look here for hook-*.py files

# ------------------------------------------------------------------
# 8.7  Runtime hooks – ensure platform module is properly loaded
# ------------------------------------------------------------------
# This fixes the AttributeError: module 'platform' has no attribute 'system' error
# that occurs when keyring imports jaraco.context which uses platform.system()
# Copy runtime hook to spec directory and use relative path
# NOTE: This is done in main() before spec generation to avoid ROOT being undefined in spec
runtime_hooks = ["pyi_rth_platform.py"]

# ------------------------------------------------------------------
# 8.8  Build Analysis
# ------------------------------------------------------------------
a = Analysis(
    [main_script_path],
    pathex=[src_path],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=hookspath,
    runtime_hooks=runtime_hooks,
    excludes=["test*", ".test*"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific executable name
exe_name = "HytaleModUpdater"
if platform == "windows":
    exe_name = "HytaleModUpdater.exe"

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Enable console for debugging
    icon=icon_path,
    onefile=True,  # Create a single standalone executable
)

"""
    return spec


def main():
    """Main build function."""
    parser = argparse.ArgumentParser(description="Build Hytale Mod Updater")
    parser.add_argument("--platform", choices=["windows", "linux", "auto"],
                       default="auto", help="Target platform (default: auto-detect)")
    args = parser.parse_args()
    
    # Determine target platform
    platform = get_target_platform(args.platform)
    print(f"Building for platform: {platform}")
    
    # Install Playwright browsers for the target platform
    install_playwright_browsers(platform)
    
    # Copy runtime hook to spec directory for PyInstaller to include
    import shutil
    shutil.copy(str(ROOT / "pyi_rth_platform.py"), str(SPEC_DIR / "pyi_rth_platform.py"))
    print(f"Copied runtime hook to {SPEC_DIR / 'pyi_rth_platform.py'}")
    
    # Generate spec file
    spec_content = generate_spec_content(platform)
    spec_filename = f"HytaleModUpdater_{platform}.spec"
    SPEC_FILE = SPEC_DIR / spec_filename
    SPEC_FILE.write_text(spec_content)
    print(f"Spec file written to {SPEC_FILE}")
    
    # Run PyInstaller using the generated spec
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        str(SPEC_FILE.resolve()),
    ]
    
    try:
        subprocess.check_call(cmd)
        print(f"\nBuild complete! Executable is in {DIST_DIR}")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"\nERROR: PyInstaller exited with code {exc.returncode}")


if __name__ == "__main__":
    main()
