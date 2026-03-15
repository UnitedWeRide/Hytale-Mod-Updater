# Hytale Mod Updater

[![Skylos Grade](https://img.shields.io/badge/Skylos-A%2B%20%28100%29-brightgreen)](https://github.com/duriantaco/skylos)
![Dead Code Free](https://img.shields.io/badge/Dead_Code-Free-brightgreen?logo=moleculer&logoColor=white)

A desktop application for managing and updating Hytale mods from CurseForge. The application provides a graphical interface for loading mod files, checking for updates, downloading outdated mods, and managing backups.

**Note**: This application is designed to run as a standalone executable. It is NOT designed to run directly from source code, as it does not download or manage Python dependencies at runtime. Dependencies are bundled into the executable during the build process.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Building from Source](#building-from-source)
  - [Running the Executable](#running-the-executable)
- [Configuration](#configuration)
  - [Settings](#settings)
  - [API Key Setup](#api-key-setup)
- [Usage](#usage)
  - [Loading Mods](#loading-mods)
  - [Checking for Updates](#checking-for-updates)
  - [Downloading Updates](#downloading-updates)
  - [Database Management](#database-management)
  - [Backup Management](#backup-management)
- [Workflow](#workflow)
  - [Application Startup](#application-startup)
  - [Mod Loading Process](#mod-loading-process)
  - [Update Detection](#update-detection)
  - [Download Process](#download-process)
- [File Structure](#file-structure)
  - [Source Code](#source-code)
  - [Build Artifacts](#build-artifacts)
  - [Resources](#resources)
- [Dependencies](#dependencies)
  - [Core Dependencies](#core-dependencies)
  - [Build Dependencies](#build-dependencies)
- [Advanced Features](#advanced-features)
  - [Fingerprint Matching](#fingerprint-matching)
  - [Database Pagination](#database-pagination)
  - [Playwright Fallback](#playwright-fallback)
- [Edge Cases and Error Handling](#edge-cases-and-error-handling)
  - [API Failures](#api-failures)
  - [Download Failures](#download-failures)
  - [File System Errors](#file-system-errors)
  - [Database Errors](#database-errors)
- [Build System](#build-system)
  - [Build Script](#build-script)
  - [PyInstaller Configuration](#pyinstaller-configuration)
- [Logging](#logging)
- [Security Considerations](#security-considerations)

## Overview

The Hytale Mod Updater is a desktop application that helps users manage their Hytale mods by:

- Loading and displaying mod files from a specified directory
- Computing file fingerprints for mod identification
- Matching fingerprints to CurseForge mod IDs
- Checking for available updates
- Downloading outdated mods with backup options
- Managing a local database of all Hytale mods from CurseForge

The application uses a centralized database approach where all Hytale mods are fetched from CurseForge and stored locally. This allows for fast update detection without requiring individual API calls for each mod.

## Features

- **Mod Loading**: Load .zip and .jar files from a folder with hierarchical treeview display
- **Fingerprint Computation**: Compute CurseForge-compatible fingerprints for mod identification
- **Mod ID Matching**: Match fingerprints to CurseForge mod IDs via exact or fuzzy matching
- **Update Detection**: Check loaded mods against the local database for available updates
- **Download Management**: Download outdated mods with configurable backup options
- **Database Management**: Refresh the local mod database from CurseForge
- **Backup System**: Create backups before downloading, restore from backups
- **Theme Support**: Dark Forest theme with automatic system detection
- **Settings Management**: Persistent settings for theme, API key, and behavior

## System Requirements

- **Operating System**: Windows 10/11 (64-bit)
- **Python**: 3.8+ (for development)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 500MB for the application, plus space for mods and database

## Installation

### Prerequisites

Before building the application, ensure you have:

1. Python 3.10+ (the same interpreter used for development)
2. A virtual environment (recommended)
3. An active internet connection for API access and downloading dependencies during build

**Important**: This application is designed to run as a standalone executable. It is NOT designed to run directly from source code, as it does not download or manage Python dependencies at runtime. Dependencies are bundled into the executable during the build process.

### Prerequisites for Building

- Python 3.10+ (the same interpreter used for development)
- pip package manager
- Access to CurseForge API (for API key validation)

### Building from Source

1. Clone or navigate to the project directory
2. Activate your virtual environment:
   ```powershell
   .\.venv\scripts\activate
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the build script:
   ```powershell
   python build.py
   ```

The build script will:
- Clean previous build artifacts
- Install dependencies from requirements.txt
- Install PyInstaller if not present
- Download Playwright browser binaries
- Download the Forest-ttk-theme
- Create a PyInstaller spec file
- Build the executable

The executable will be created in the `dist/` directory as `HytaleModUpdater.exe`.

### Running the Executable

1. Navigate to the `dist/` directory
2. Run `HytaleModUpdater.exe`
3. The first time you run the application, you will be prompted to enter a CurseForge API key

**Note**: The executable is self-contained and does not require Python to be installed on the target machine. All dependencies are bundled within the executable.

## Configuration

### Settings

The application stores user settings in `config.json` in the application directory. Settings include:

| Setting | Default | Description |
|---------|---------|-------------|
| `theme` | "forest" | Theme name (only "forest" supported) |
| `theme_mode` | "auto" | Theme mode: "auto", "light", or "dark" |
| `mod_directory` | "" | Default directory for mod files |
| `debug_mode` | false | Enable comprehensive logging |
| `backup_enabled` | true | Enable backup creation before downloads |
| `app_mode` | "curseforge" | Application mode |
| `game_id` | 70216 | Game ID for mod database (70216 = Hytale) |
| `game_name` | "Hytale" | Game name display |
| `only_stable` | true | Only update to stable versions |
| `ignore_beta` | true | Ignore beta versions |
| `close_terminal_on_exit` | true | Close terminal when app exits |
| `download_rate_limit` | 0.5 | Delay between downloads in seconds |
| `full_speed_db_pagination` | false | Use all CPU threads for database pagination |
| `automated_update_check` | false | Automatically check for updates after loading mods |
| `restore_mods_on_launch` | false | Restore mods folder on app launch |

### API Key Setup

The application requires a CurseForge API key to access the mod database. To obtain an API key:

1. Visit [https://console.curseforge.com/](https://console.curseforge.com/)
2. Sign in with your CurseForge account
3. Click "Create New API Key"
4. Copy the generated key

The API key is stored securely in your system's keyring and is never shared with third parties.

## Usage

### Loading Mods

1. Click "Browse Folder (.zip/.jar)" to select a folder containing mod files
2. The application will:
   - Scan the folder for .zip and .jar files
   - Compute fingerprints for each file
   - Match fingerprints to CurseForge mod IDs
   - Display files in a hierarchical treeview

The treeview shows:
- **Name**: File name or directory structure
- **Mod ID**: CurseForge mod ID (if matched)
- **Fingerprint**: 32-bit file fingerprint

### Checking for Updates

1. Click "Check for Updates" to scan loaded mods for available updates
2. The application will:
   - Compare local fingerprints against the database
   - Identify outdated mods
   - Display results in a dialog

Outdated mods are highlighted in red in the treeview.

### Downloading Updates

1. Click "Download Outdated Mods" to download all outdated mods
2. The application will:
   - Prompt for backup options (backup, recycle bin, or delete)
   - Process backups
   - Download outdated mods
   - Show download results

### Database Management

1. Click "Refresh Database" to update the local mod database
2. The application will:
   - Fetch all Hytale mods from CurseForge
   - Update the local database
   - Show completion status

### Backup Management

1. Click "Restore Backups" to restore previous versions of mods
2. Select backup files to restore
3. The application will restore selected backups to the mod directory

## Workflow

### Application Startup

1. Path manager resolves base paths (executable directory or workspace)
2. Settings manager loads configuration from `config.json`
3. Logging is initialized based on debug mode setting
4. API key is retrieved from system keyring
5. Mod ID store is initialized
6. Mod database manager is initialized (if API key available)
7. Theme is applied based on settings
8. Main window is created and displayed

### Mod Loading Process

1. User selects a folder with mod files
2. Files are scanned for .zip and .jar extensions
3. Each file is processed in parallel threads:
   - Zip file is opened and contents are listed
   - Fingerprint is computed for the file
   - Fingerprint is matched to mod ID (if available)
4. Treeview is populated with file contents
5. Mod count is updated in status bar

### Update Detection

1. User clicks "Check for Updates"
2. For each loaded mod:
   - Mod ID is retrieved from treeview
   - Latest fingerprint is fetched from database
   - Local fingerprint is compared to latest
3. Outdated mods are identified
4. Results are displayed in dialog
5. Treeview is updated with outdated status

### Download Process

1. User clicks "Download Outdated Mods"
2. Backup options are presented:
   - **Backup**: Create .old backup in backup directory
   - **Recycle Bin**: Move to Windows Recycle Bin
   - **Delete**: Permanently delete the file
3. Backups are created based on user selection
4. Downloads are performed in parallel:
   - API download is attempted first
   - If API fails, CFWidget API is tried
   - If CFWidget fails, Playwright browser automation is used
5. Download results are displayed
6. Failed downloads can be handled manually

## File Structure

### Source Code

```
src/
├── main.py                 # Application entry point
├── config/                 # Configuration modules
│   ├── __init__.py
│   ├── paths.py           # Path resolution
│   └── settings.py        # Settings management
├── core/                   # Core application logic
│   ├── __init__.py
│   ├── app.py             # Main application class
│   └── theme_manager.py   # Theme management
├── services/               # Service modules
│   ├── __init__.py
│   ├── backup_manager.py       # Backup operations
│   ├── curseforge_api.py       # CurseForge API client
│   ├── cfwidget_api.py         # CFWidget API client
│   ├── keyring_manager.py      # API key storage
│   ├── mod_database_manager.py # Database management
│   ├── mod_downloader.py       # Mod downloading
│   ├── mod_id_matcher.py       # Fingerprint matching
│   ├── mod_id_store.py         # Mod ID caching
│   ├── playwright_downloader.py # Playwright fallback
│   ├── playwright_thread_manager.py # Thread management
│   └── update_checker.py       # Update detection
├── ui/                     # UI modules
│   ├── __init__.py
│   ├── app_window.py          # Main window
│   ├── dialogs.py             # Dialog windows
│   └── settings_handlers.py   # Settings management
└── utils/                  # Utility modules
    ├── __init__.py
    ├── file_loader.py    # File loading
    ├── fingerprint.py    # Fingerprint computation
    └── logging.py        # Logging setup
```

### Build Artifacts

```
build/                    # PyInstaller build artifacts
dist/                     # Built executable
playwright_browsers/      # Playwright browser binaries
resources/                # Bundled resources
```

### Resources

```
resources/
├── Forest-ttk-theme/     # Dark Forest theme (by rdbende)
├── icon/
│   └── Hytale.ico        # Application icon
└── kofi_button.png       # Ko-fi donation button
```

## Dependencies

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| requests | Latest | HTTP requests for APIs |
| keyring | Latest | Secure API key storage |
| numpy | Latest | Fingerprint computation |
| playwright | Latest | Browser automation fallback |
| send2trash | Latest | Recycle bin operations |

### Build Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pyinstaller | Latest | Executable packaging |

## Advanced Features

### Fingerprint Matching

The application uses CurseForge's fingerprint algorithm to identify mods:

1. **File Reading**: The file is memory-mapped for efficient reading
2. **Whitespace Removal**: Newlines, carriage returns, and spaces are filtered
3. **Chunk Processing**: 4-byte chunks are processed in batches
4. **Hash Computation**: A 32-bit hash is computed using multiplication and XOR operations
5. **API Matching**: Fingerprints are matched via CurseForge API (exact or fuzzy)

### Database Pagination

The database is built by paginating through all mods on CurseForge:

1. **Total Count**: First page fetch retrieves total mod count
2. **Page Calculation**: Total pages = (count / 50) + 1
3. **Parallel Fetching**: Pages are fetched in parallel threads
4. **Incremental Updates**: Unchanged mods are skipped on subsequent builds
5. **Async Saving**: Database is saved asynchronously to prevent blocking

### Playwright Fallback

When API downloads fail, the application uses Playwright browser automation:

1. **CFWidget API**: First fallback attempts CFWidget API
2. **Browser Launch**: If CFWidget fails, a visible Chromium browser is launched
3. **Cloudflare Handling**: The visible browser allows users to complete Cloudflare verification
4. **Download Monitoring**: Playwright monitors download events
5. **Progress Feedback**: Browser provides visual download progress

## Edge Cases and Error Handling

### API Failures

- **Rate Limiting**: API calls are rate-limited to 0.5 seconds between requests
- **Invalid API Key**: Error message is displayed, user is prompted to verify key
- **Network Errors**: Downloads are retried with fallback mechanisms

### Download Failures

- **API Failure**: Falls back to CFWidget API
- **CFWidget Failure**: Falls back to Playwright browser automation
- **Playwright Failure**: User is shown failed mods with manual download links

### File System Errors

- **Permission Denied**: Error message is displayed with file path
- **Disk Full**: Error message is displayed
- **File in Use**: Backup operations fail gracefully

### Database Errors

- **Corrupted Database**: Database is rebuilt from scratch
- **API Unavailable**: Database refresh fails gracefully
- **JSON Decode Error**: Database is rebuilt from scratch

## Build System

### Build Script

The `build.py` script automates the build process:

1. **Cleanup**: Removes previous build artifacts
2. **Dependency Installation**: Installs requirements from `requirements.txt`
3. **PyInstaller Check**: Ensures PyInstaller is installed
4. **Playwright Setup**: Downloads browser binaries to `playwright_browsers/`
5. **Theme Download**: Downloads Forest-ttk-theme if not present
6. **Hook Creation**: Creates Tkinter hook for PyInstaller
7. **Spec Generation**: Creates PyInstaller spec file
8. **Build Execution**: Runs PyInstaller with the spec file

### PyInstaller Configuration

The spec file includes:

- **Tkinter DLLs**: tk86t.dll, tcl86t.dll
- **Theme Files**: Forest-ttk-theme directory
- **Playwright**: Browser binaries and driver
- **Hidden Imports**: All application modules
- **Data Files**: Resources directory

## Logging

The application uses centralized logging with two handlers:

1. **File Handler**: Logs to `app_debug.log` in the application directory
2. **Console Handler**: Logs to stdout (always enabled for frozen apps)

Log levels:
- **INFO**: General application events
- **DEBUG**: Detailed debugging information (requires debug mode)

## Security Considerations

- **API Key Storage**: API keys are stored in the system keyring (Windows Credential Manager)
- **URL Validation**: All URLs are validated to prevent SSRF attacks
- **Path Traversal**: Backup paths are validated to prevent directory traversal
- **Rate Limiting**: API calls are rate-limited to prevent abuse
- **Thread Safety**: Database operations use locks for thread-safe access

## Credits

- **Forest-ttk-theme**: Created by [rdbende](https://github.com/rdbende/Forest-ttk-theme)

## License
This project is licensed under the MIT License. See the LICENSE file for details.