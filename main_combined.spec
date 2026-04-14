# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for LLM Chat App
# One can use this file to customize the build process, such as adding data files, hidden imports, etc. 
# One_dir can be used to specify the output directory for the built application.
# One_file can be used to create a single executable file, but it may increase the build time and the size of the executable.   
# Gives Both OneDIr and OneFile Build

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('ui_designer', 'ui_designer'),
        ('workers', 'workers')
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
        'PySide6.QtUiTools'
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LLM Chat App'
)