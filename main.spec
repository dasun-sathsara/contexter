# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Get the project root directory
project_root = Path(os.getcwd())

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('C:/Users/dasun/Desktop/Contexter (Python)/.venv/Lib/site-packages/tiktoken_ext', 'tiktoken_ext'),
    ],
    hiddenimports=[
        'tiktoken',
        'tiktoken.core',
        'tiktoken.load',
        'tiktoken.registry',
        'tiktoken.encoding',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
        'pathspec',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets', 
        'PyQt6.QtGui',
    ],
    hookspath=[str(project_root)],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'PIL',
        'tkinter',
        'unittest',
        'pdb',
        'doctest',
        'difflib',
        'email',
        'http',
        'xml',
        'sqlite3',
        'multiprocessing',
    ],
    noarchive=False,
    optimize=2,
)

# Filter out unnecessary modules
a.binaries = [x for x in a.binaries if not any(
    excluded in x[0].lower() for excluded in [
        'qtwebengine', 'qtquick', 'qtmultimedia', 'qtsql', 
        'qtnetwork', 'qtpdf', 'qtdatavis', 'qtcharts'
    ]
)]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Contexter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
)
