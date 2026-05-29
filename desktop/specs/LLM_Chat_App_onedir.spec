import os
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Main Application Analysis
a_main = Analysis(
    [os.path.join('..', os.path.join('..', os.path.join('..', 'main.py')))],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_main = PYZ(a_main.pure, a_main.zipped_data, cipher=block_cipher)


# OneDir EXEs
exe_main = EXE(
    pyz_main, a_main.scripts, [], exclude_binaries=True,
    name='LLM_Chat_App', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False, disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)

coll = COLLECT(
    exe_main, a_main.binaries, a_main.zipfiles, a_main.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LLM_Chat_App'
)
