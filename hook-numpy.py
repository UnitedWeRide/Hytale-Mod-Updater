# hook-numpy.py
# PyInstaller hook to include all numpy submodules and data files
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all numpy submodules
hiddenimports = collect_submodules('numpy')

# Collect numpy data files (for compiled extensions)
datas = collect_data_files('numpy', include_py_files=False)