# -*- mode: python ; coding: utf-8 -*-
"""
Arquivo de especificacao do PyInstaller para gerar o executavel do Nariz Eletronico.
NOTA: Deixado preparado conforme solicitado. Para compilar o .exe quando estiver pronto,
execute:
    pyinstaller --noconfirm NarizEletronico.spec
ou de duplo-clique em gerar_exe_pyinstaller.bat.
"""

from pathlib import Path

block_cipher = None
project_root = Path(SPECPATH)

added_files = [
    (str(project_root / "version.json"), "."),
    (str(project_root / "nariz_eletronico.ino"), "."),
    (str(project_root / "arduino"), "arduino"),
]

a = Analysis(
    [str(project_root / "run_app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        "pyqtgraph",
        "serial",
        "serial.tools.list_ports",
        "numpy",
        "pandas",
        "sqlite3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NarizEletronico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NarizEletronico",
)
