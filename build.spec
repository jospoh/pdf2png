# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for PDF2PNG desktop application."""

import dis
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# Workaround for Python 3.10.0 dis module bug (IndexError when scanning
# bytecode compiled by newer Python). Patch _get_const_info to handle
# out-of-range const indices gracefully.
_original_get_const_info = dis._get_const_info
def _patched_get_const_info(const_index, const_list):
    try:
        return _original_get_const_info(const_index, const_list)
    except IndexError:
        return const_index, repr(const_index)
dis._get_const_info = _patched_get_const_info

block_cipher = None

# Collect all fitz/pymupdf data and binaries
fitz_datas, fitz_binaries, fitz_hiddenimports = collect_all('fitz')

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=fitz_binaries,
    datas=fitz_datas,
    hiddenimports=fitz_hiddenimports + [
        'PIL._imaging',
        'PIL.PngImagePlugin',
        'pdf2png',
        'pdf2png_gui',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'IPython',
        'jupyter',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- Icon path (use if exists, otherwise None) ---
_icon_ico = 'assets/icon.ico'
_icon_icns = 'assets/icon.icns'
icon_path = None
if sys.platform == 'win32' and Path(_icon_ico).exists():
    icon_path = _icon_ico
elif sys.platform == 'darwin' and Path(_icon_icns).exists():
    icon_path = _icon_icns

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF2PNG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI mode, no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

# macOS .app bundle (onefile mode: use exe directly)
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='PDF2PNG.app',
        icon=icon_path,
        bundle_identifier='com.pdf2png.converter',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
            'LSMinimumSystemVersion': '12.0',
        },
    )
