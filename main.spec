# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for LLM Chat App
# One can use this file to customize the build process, such as adding data files, hidden imports, etc. 
# One_dir can be used to specify the output directory for the built application.
# One_file can be used to create a single executable file, but it may increase the build time and the size of the executable.   

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('ui_designer', 'ui_designer'),
        ('workers', 'workers')  # ADD THIS - include workers folder
    ],
    hiddenimports=[
        'markdown',
        'openai',
        'certifi',
        'urllib3',
        'charset_normalizer',
        'PySide6.QtCore',      # ADD THIS
        'PySide6.QtWidgets',   # ADD THIS
        'PySide6.QtGui',       # ADD THIS
        'PySide6.QtUiTools'    # ADD THIS
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt6',
        'tkinter',
        '_tkinter'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

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
    console=False,  # Keep False for production, change to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/app_icon.ico',
)