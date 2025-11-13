# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('outline.png', '.')],
    hiddenimports=[
        'tkinter',
        'tkinter.filedialog',
        'pywintypes',
        'win32timezone',
        'mutagen.flac',      
        'mutagen.mp3',       
        'mutagen.id3',   
        'mutagen.easyid3', 
        'mutagen.wave',  
        'mutagen.oggvorbis',
        'mutagen.mp4',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='网易云音乐',
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
    icon=['outline.png'],
)
