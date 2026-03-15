
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
