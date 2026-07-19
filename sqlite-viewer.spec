# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ


analysis = Analysis(["src/sqlite_viewer/app.py"], pathex=["src"])
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    name="SQLite Viewer",
    console=False,
    exclude_binaries=True,
)
coll = COLLECT(exe, analysis.binaries, analysis.datas, name="SQLite Viewer")
