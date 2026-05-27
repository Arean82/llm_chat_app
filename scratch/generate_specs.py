import os

def create_operator_spec(file_path, script_path, exe_name):
    content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{script_path}'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='operator_tools/{exe_name}',
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
)
"""
    with open(file_path, "w") as f:
        f.write(content)

def create_main_spec(file_path, is_onefile, is_full):
    content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Main Application Analysis
a_main = Analysis(
    ['main.py'],
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

"""

    if is_full:
        content += """# Operator Tools Analysis
a_mig = Analysis(['operator_tools/migration/migration_companion.py'], pathex=[], binaries=[], datas=[], hiddenimports=[], excludes=[], cipher=block_cipher)
pyz_mig = PYZ(a_mig.pure, a_mig.zipped_data, cipher=block_cipher)

a_res = Analysis(['operator_tools/admin_reset/reset_admin.py'], pathex=[], binaries=[], datas=[], hiddenimports=[], excludes=[], cipher=block_cipher)
pyz_res = PYZ(a_res.pure, a_res.zipped_data, cipher=block_cipher)
"""

    if is_onefile:
        content += """
# OneFile Executables
exe_main = EXE(
    pyz_main, a_main.scripts, a_main.binaries, a_main.zipfiles, a_main.datas, [],
    name='LLM_Chat_App', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=False, disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)
"""
        if is_full:
            content += """
exe_mig = EXE(
    pyz_mig, a_mig.scripts, a_mig.binaries, a_mig.zipfiles, a_mig.datas, [],
    name='operator_tools/Migration_Companion', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=False, disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)

exe_res = EXE(
    pyz_res, a_res.scripts, a_res.binaries, a_res.zipfiles, a_res.datas, [],
    name='operator_tools/Admin_Reset', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=False, disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)
"""
    else:
        # Onedir mode
        content += """
# OneDir EXEs
exe_main = EXE(
    pyz_main, a_main.scripts, [], exclude_binaries=True,
    name='LLM_Chat_App', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False, disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)
"""
        if is_full:
            content += """
exe_mig = EXE(
    pyz_mig, a_mig.scripts, [], exclude_binaries=True,
    name='operator_tools/Migration_Companion', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False, disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)

exe_res = EXE(
    pyz_res, a_res.scripts, [], exclude_binaries=True,
    name='operator_tools/Admin_Reset', debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False, disable_windowed_traceback=False, argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)

coll = COLLECT(
    exe_main, a_main.binaries, a_main.zipfiles, a_main.datas,
    exe_mig, a_mig.binaries, a_mig.zipfiles, a_mig.datas,
    exe_res, a_res.binaries, a_res.zipfiles, a_res.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LLM_Chat_App'
)
"""
        else:
            content += """
coll = COLLECT(
    exe_main, a_main.binaries, a_main.zipfiles, a_main.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LLM_Chat_App'
)
"""
    with open(file_path, "w") as f:
        f.write(content)

os.makedirs('operator_tools/migration', exist_ok=True)
os.makedirs('operator_tools/admin_reset', exist_ok=True)

# 1. Operator isolated specs
create_operator_spec('operator_tools/migration/migration.spec', 'migration_companion.py', 'Migration_Companion')
create_operator_spec('operator_tools/admin_reset/reset_admin.spec', 'reset_admin.py', 'Admin_Reset')

# 2. Main App specs
create_main_spec('LLM_Chat_App_onefile.spec', is_onefile=True, is_full=False)
create_main_spec('LLM_Chat_App_onedir.spec', is_onefile=False, is_full=False)
create_main_spec('LLM_Chat_App_onefile_full.spec', is_onefile=True, is_full=True)
create_main_spec('LLM_Chat_App_onedir_full.spec', is_onefile=False, is_full=True)

print("✅ Specs generated")
