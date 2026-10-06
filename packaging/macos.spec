# PyInstaller spec for the macOS app bundle.
#   pyinstaller packaging/macos.spec --noconfirm
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "assets" / "menubar@2x.png"), "assets")],
    hiddenimports=["iqosbar.ui_mac", "iqosbar.panel"],
    excludes=["tkinter", "pystray", "PIL"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="IQOS Bar",
          console=False, target_arch=None)
coll = COLLECT(exe, a.binaries, a.datas, name="IQOS Bar")
app = BUNDLE(
    coll,
    name="IQOS Bar.app",
    icon=str(ROOT / "assets" / "AppIcon.icns"),
    bundle_identifier="com.furkantirit.iqosbar",
    version="1.0.0",
    info_plist={
        "LSUIElement": True,                 # menu bar only, no Dock icon
        "CFBundleShortVersionString": "1.0.0",
        "NSHumanReadableCopyright": "MIT License, Furkan Tirit",
        "LSMinimumSystemVersion": "11.0",
    },
)
