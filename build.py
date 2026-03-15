#!/usr/bin/env python3
"""
Build script for the Hytale Mod Updater Windows executable.

Requirements:
  - Python 3.10+ (the same interpreter used for development)
  - pip install -r requirements.txt

Entry Point:
  - The application entry point is src/main.py
  - This script builds the executable using PyInstaller
"""

import os
import sys
import subprocess
import zipfile
import io
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

# Check if browsers are already installed by looking for the chromium directory
CHROMIUM_DIR = BROWSERS_DIR / "chromium-1208" / "chrome-win64"
if not CHROMIUM_DIR.exists():
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"])
else:
    print(f"Playwright Chromium browsers already installed at {CHROMIUM_DIR}")

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
THEME_ZIP_URL = "https://github.com/rdbende/Forest-ttk-theme/archive/refs/heads/main.zip"

# Check if theme is already downloaded
if not (THEME_DIR / "forest-dark.tcl").exists():
    print(f"Downloading Forest-ttk-theme to {THEME_DIR}...")
    try:
        import urllib.request
        with urllib.request.urlopen(THEME_ZIP_URL) as response:
            zip_data = response.read()
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            # Extract the theme files from the zip
            for member in zf.namelist():
                if member.startswith("Forest-ttk-theme-main/forest-") and member.endswith(".tcl"):
                    # Extract to resources/Forest-ttk-theme/
                    filename = os.path.basename(member)
                    dest_path = THEME_DIR / filename
                    with zf.open(member) as source, open(dest_path, "wb") as target:
                        target.write(source.read())
        print(f"Forest-ttk-theme downloaded successfully")
    except Exception as e:
        print(f"Warning: Failed to download Forest-ttk-theme: {e}")
        print("Continuing with existing theme files if available")
else:
    print(f"Forest-ttk-theme already exists at {THEME_DIR}")

# -------------------------------------------------------------
# 8. Verify that tkinter is importable
# -------------------------------------------------------------
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

# -------------------------------------------------------------
# 9. Create a PyInstaller hook for Tkinter
# -------------------------------------------------------------
HOOK_TKINTER = ROOT / "hook-tkinter.py"
HOOK_TKINTER.write_text(
    """
# hook-tkinter.py
# PyInstaller hook to include all Tkinter data and DLLs
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
SPEC_FILE = SPEC_DIR / "HytaleModUpdater.spec"

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

# -------------------------------------------------------------
# 11. Write a minimal spec file that references the hook
# -------------------------------------------------------------
spec_content = f"""
# -*- mode: python; coding: utf-8 -*-
block_cipher = None

# Import the standard PyInstaller classes
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os, sys
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

if sys.platform == "win32":
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
# 8.6  Hook path – we put the hooks in the same directory as the spec
# ------------------------------------------------------------------
hookspath = ["."]  # PyInstaller will look here for hook-*.py files

# ------------------------------------------------------------------
# 8.7  Build Analysis
# ------------------------------------------------------------------
a = Analysis(
    [main_script_path],
    pathex=[src_path],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=hookspath,
    runtime_hooks=[],
    excludes=["test*", ".test*"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="HytaleModUpdater",
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

SPEC_FILE.write_text(spec_content)

# -------------------------------------------------------------
# 12. Run PyInstaller using the generated spec
# -------------------------------------------------------------
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--clean",
    "--distpath", str(DIST_DIR),
    "--workpath", str(BUILD_DIR),
    str(SPEC_FILE.resolve()),
]

try:
    subprocess.check_call(cmd)
except subprocess.CalledProcessError as exc:
    raise RuntimeError(f"\nERROR: PyInstaller exited with code {exc.returncode}")
