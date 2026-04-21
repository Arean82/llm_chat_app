# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for LLM Chat App
# One can use this file to customize the build process, such as adding data files, hidden imports, etc. 
# One_file can be used to create a single executable file, but it may increase the build time and the size of the executable.   

# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('ui_designer', 'ui_designer'),
    ],
    hiddenimports=[
        'markdown',
        'openai',
        'certifi',
        'urllib3',
        'charset_normalizer',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtUiTools',
        'pysqlite2',
        'queue',
        'threading',
        'time',
        'json',
        'base64',
        'socket',
        'pathlib',
        're',
        'datetime',
        'importlib.metadata',
        'importlib.resources',
        'markdown.extensions.extra',
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt6',
        'tkinter',
        '_tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# ===== SINGLE FILE EXECUTABLE ONLY =====
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='LLM Chat App',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/app_icon.ico',
)