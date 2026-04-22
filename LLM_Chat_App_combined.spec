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
        ('resources/app_icon.png', 'resources'),
        ('resources/app_icon.ico', 'resources'),
        ('resources/styles.qss', 'resources'),
        ('resources/models.json', 'resources'),
        ('resources/user_prompts.json', 'resources'),
        ('README.md', '.'),           
        ('LICENSE', '.'),        
        ('API_SERVER.md', '.'),
        ('IDE_INTEGRATION.md', '.'),
        ('extension/vscode-llm-chat-1.0.0.vsix', 'extension'),
        ('extension/jetbrains-llm-chat-1.0.0.zip', 'extension'),  
        ('ui_designer/login_dialog.ui', 'ui_designer'),
        ('ui_designer/log_viewer.ui', 'ui_designer'),
        ('ui_designer/main_window.ui', 'ui_designer'),
        ('ui_designer/model_edit_dialog.ui', 'ui_designer'),
        ('ui_designer/model_manager.ui', 'ui_designer'),
        ('ui_designer/model_popup.ui', 'ui_designer'),
        ('ui_designer/system_prompt_manager.ui', 'ui_designer'),
    ],
    hiddenimports=[
        'flask',
        'openai',
        'markdown',
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
        'logging',
        'webbrowser',
        'shutil',
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='LLM Chat App',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='resources/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='LLM Chat App'
)