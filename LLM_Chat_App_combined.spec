# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for LLM Chat App
# Triple-Binary Build: LLM Chat App + Migration Companion + Reset Admin (v7.3.0 Phase 10.3)
# Produces both OneDir and OneFile builds for the primary app,
# plus standalone executables for the operator admin portfolio.

# ═══════════════════════════════════════════════════════════════════
#  1. PRIMARY APP: LLM Chat App
# ═══════════════════════════════════════════════════════════════════

a_main = Analysis(
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

pyz_main = PYZ(a_main.pure, a_main.zipped_data, cipher=None)

exe_onefile = EXE(
    pyz_main,
    a_main.scripts,
    a_main.binaries,
    a_main.zipfiles,
    a_main.datas,
    name='LLM_Chat_one_file/LLM Chat App',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='resources/app_icon.ico',
    version='file_version_info.txt',
)

exe_onedir = EXE(
    pyz_main,
    a_main.scripts,
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


# ═══════════════════════════════════════════════════════════════════
#  2. OPERATOR TOOL: Migration Companion
# ═══════════════════════════════════════════════════════════════════

a_companion = Analysis(
    ['operator_tools/migration_companion.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources/app_icon.ico', 'resources'),
        ('saas/config.ini', 'saas'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'sqlite3',
        'pysqlite2',
        'configparser',
        'argparse',
        'hashlib',
        'json',
        'pathlib',
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

pyz_companion = PYZ(a_companion.pure, a_companion.zipped_data, cipher=None)

exe_companion = EXE(
    pyz_companion,
    a_companion.scripts,
    a_companion.binaries,
    a_companion.zipfiles,
    a_companion.datas,
    name='Migration Companion',
    debug=False,
    strip=False,
    upx=True,
    console=True,  # Console for headless/CLI fallback support
    icon='resources/app_icon.ico',
)


# ═══════════════════════════════════════════════════════════════════
#  3. OPERATOR TOOL: Reset Admin
# ═══════════════════════════════════════════════════════════════════

a_reset = Analysis(
    ['operator_tools/reset_admin.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('saas/config.ini', 'saas'),
    ],
    hiddenimports=[
        'sqlite3',
        'pysqlite2',
        'configparser',
        'hashlib',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5',
        'PyQt6',
        'PySide6',
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

pyz_reset = PYZ(a_reset.pure, a_reset.zipped_data, cipher=None)

exe_reset = EXE(
    pyz_reset,
    a_reset.scripts,
    a_reset.binaries,
    a_reset.zipfiles,
    a_reset.datas,
    name='Reset Admin',
    debug=False,
    strip=False,
    upx=True,
    console=True,  # Pure CLI tool — always console
)


# ═══════════════════════════════════════════════════════════════════
#  COLLECT: OneDir build (includes all three executables)
# ═══════════════════════════════════════════════════════════════════

coll = COLLECT(
    exe_onedir,
    a_main.binaries,
    a_main.zipfiles,
    a_main.datas,
    exe_companion,
    exe_reset,
    strip=False,
    upx=True,
    name='LLM_Chat_dir'
)


# ═══════════════════════════════════════════════════════════════════
#  macOS Bundle Configuration
# ═══════════════════════════════════════════════════════════════════

import sys
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='LLM Chat App.app',
        icon='resources/app_icon.icns',
        bundle_identifier='com.arean82.llmchatapp',
        info_plist={
            'CFBundleShortVersionString': '7.3.0',
            'CFBundleVersion': '7.3.0',
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'NSHighResolutionCapable': True,
        },
    )