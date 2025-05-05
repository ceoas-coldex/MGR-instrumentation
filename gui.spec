# -*- mode: python ; coding: utf-8 -*-


added_files = [
    ('logs/',  'logs'),
    ('data/', 'data'),
    ('config/', 'config'),
    ('doc/', 'doc'),
    ('README.md', '.')
]

a = Analysis(
    ['gui.py'],
    pathex=['/main_pipeline'],
    binaries=[],
    datas=added_files,
    hiddenimports=['main_pipeline'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='gui',
)
