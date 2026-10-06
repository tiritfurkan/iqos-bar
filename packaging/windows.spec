# PyInstaller spec for the Windows build (single .exe, no console window).
#   pyinstaller packaging/windows.spec --noconfirm
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    # pystray picks its backend at runtime, so PyInstaller can't see it.
    hiddenimports=["iqosbar.ui_win", "pystray._win32", "PIL.ImageFont"],
    excludes=["tkinter", "objc", "AppKit", "Foundation", "WebKit"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="IQOS Bar",
    console=False,
    icon=str(ROOT / "assets" / "AppIcon.ico"),
)
