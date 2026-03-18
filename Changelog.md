# Changelog

## v1.1.0 (2026-03-18)

### Fixed
- **Build incorrectly using the wrong theme repo** - Updated to use the GitHub master branch instead of main branch for the Forest-ttk-theme, ensuring the latest theme files including images are downloaded correctly.

### Added
- **Linux Build Support** - Added full Linux build support with platform-specific build scripts. The build system now supports:
  - Platform detection (auto-detect or explicit `--platform windows/linux`)
  - Platform-specific Playwright browser installation (chrome-win64 vs chrome-linux64)
  - Linux tkinter support with automatic python3-tk installation
  - Platform-specific PyInstaller spec generation
  - Linux executable output (HytaleModUpdater without .exe extension)

- **Scrolling Support Added to Settings Menu** - The settings window now includes:
  - Scrollable canvas-based interface for responsive layout
  - Mouse wheel scrolling support on both Windows and Linux
  - Dynamic window sizing based on screen resolution
  - Proper cleanup of scroll bindings when window is destroyed

### Technical Changes
- Added `os_detector` module with `PlatformDetector` class for cross-platform browser path resolution
- Updated `build.py` to support multi-platform builds with `--platform` argument
- Added `pyi_rth_platform.py` runtime hook to fix `platform.system()` errors in keyring
- Updated dependencies: `keyrings.alt`, `jaraco.context`, `pywin32` (Windows-specific)
- Theme download now includes complete theme directory with images
