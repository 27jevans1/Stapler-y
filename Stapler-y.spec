# -*- mode: python ; coding: utf-8 -*-
import os

# Always resolve src/ relative to this spec file, regardless of
# where PyInstaller is invoked from (local machine, CI, etc.)
src_path = os.path.join(os.path.dirname(os.path.abspath(SPECPATH)), 'src')

block_cipher = None

a = Analysis(
    [os.path.join(src_path, 'main.py')],
    pathex=[src_path],
    binaries=[],
    datas=[],
    hiddenimports=[
        'chat_win',
        'ai',
        'history',
        'elderCore',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageTk',
        'PIL.ImageOps',
        'PIL.ImageGrab',
    ],
    hookspath=[],
    hooksconfig={},
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
    name='Stapler-y',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
