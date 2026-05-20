# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for LLM Chat App
# One can use this file to customize the build process, such as adding data files, hidden imports, etc. 
# One_dir can be used to specify the output directory for the built application.
# One_file can be used to create a single executable file, but it may increase the build time and the size of the executable.   
# Gives Both OneDIr and OneFile Build (v6.7.0 Stable Sync)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources/', 'resources'),
        ('ui_designer/', 'ui_designer'),
        ('extension/', 'extension'),
        ('headless/', 'headless'),
        ('README.md', '.'),           
        ('LICENSE', '.'),        
        ('API_SERVER.md', '.'),
        ('IDE_INTEGRATION.md', '.'),
        ('SECURITY.md', '.'),
        ('HEADLESS_GUIDE.md', '.'),
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'werkzeug.serving',
        'openai',
        'google',
        'google.genai',
        'google.genai.types',
        'google.generativeai',
        'google.generativeai.types',
        'google.ai.generativelanguage',
        'google.api_core',
        'pydantic',
        'httpx',
        'websockets',
        'proto',
        'markdown',
        'certifi',
        'urllib3',
        'charset_normalizer',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtUiTools',
        'sqlite3',
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
        'logging',
        'webbrowser',
        'shutil',
        'keyring',
        'numpy',
        'pandas',
        'pypdf',
        'docx2txt',
        'pptx',
        'odf',
        'openpyxl',
        'qdrant_client',
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

exe_onefile = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='LLM_Chat_one_file/LLM Chat App',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='resources/app_icon.ico',
    version='file_version_info.txt',
)

exe_onedir = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LLM Chat App',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='resources/app_icon.ico',
    version='file_version_info.txt',
)

coll = COLLECT(
    exe_onedir,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='LLM_Chat_dir'
)

# macOS specific bundle configuration
import sys
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='LLM Chat App.app',
        icon='resources/app_icon.icns',
        bundle_identifier='com.arean82.llmchatapp',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'NSHighResolutionCapable': True,
        },
    )