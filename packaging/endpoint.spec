from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

root = Path.cwd()

a = Analysis(
    [str(root / "backend" / "endpoint" / "launcher.py")],
    pathex=[str(root / "backend")],
    binaries=[],
    datas=[(str(root / "dist"), "web")],
    hiddenimports=collect_submodules("endpoint") + collect_submodules("uvicorn"),
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
    name="endpoint",
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
