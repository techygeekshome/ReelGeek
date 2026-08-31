# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Windows build.

One folder, not one file. A one-file build unpacks itself to a temp folder on
every launch, which is slower to start and is the single biggest reason
PyInstaller apps get flagged by antivirus. A folder next to a shortcut behaves
like every other app on the machine.
"""
from pathlib import Path

ROOT = Path(SPECPATH).parent

datas = [
    (str(ROOT / 'reelgeek' / 'ui.html'), 'reelgeek'),
]

ffmpeg_exe = ROOT / 'ffmpeg' / 'ffmpeg.exe'
if ffmpeg_exe.exists():
    datas.append((str(ffmpeg_exe), 'ffmpeg'))

icon = ROOT / 'packaging' / 'reelgeek.ico'

a = Analysis(
    [str(ROOT / 'desktop.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'reelgeek',
        'reelgeek.server',
        'reelgeek.render',
        'reelgeek.presets',
        'reelgeek.timeline',
        'reelgeek.motion',
        'reelgeek.imaging',
        'reelgeek.text',
        'reelgeek.audio',
        'reelgeek.settings',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc_data', 'test'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ReelGeek',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon) if icon.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='ReelGeek',
)
