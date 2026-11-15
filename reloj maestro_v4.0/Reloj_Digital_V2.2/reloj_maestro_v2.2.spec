# -*- mode: python ; coding: utf-8 -*-
import sys
import tempfile
import zipfile
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


def _zip_tcl_tk_datas():
    """Añade Tcl/Tk cuando Python los distribuye comprimidos (zipfs).

    Algunas instalaciones de Python 3.14 en Windows traen ``libtcl*.zip`` y
    ``libtk*.zip`` en vez de las carpetas ``tcl8.x``/``tk8.x``. PyInstaller
    6.21 no sabe leer esa ubicación, así que extraemos los ZIP en una carpeta
    temporal y los declaramos con los nombres que espera su runtime hook.
    En instalaciones normales no se hace nada.
    """
    tcl_root = Path(sys.base_prefix) / 'tcl'
    if not tcl_root.is_dir():
        return []
    if any(path.is_dir() for path in tcl_root.glob('tcl[0-9]*')):
        return []

    datas = []
    temp = Path(tempfile.mkdtemp(prefix='reloj_tcl_'))
    for pattern, libdir, dest in (
        ('libtcl*.zip', 'tcl_library', '_tcl_data'),
        ('libtk*.zip', 'tk_library', '_tk_data'),
    ):
        for archive in sorted(tcl_root.glob(pattern)):
            with zipfile.ZipFile(archive) as zf:
                if not any(name.startswith(libdir + '/') for name in zf.namelist()):
                    continue
                target = temp / archive.stem
                zf.extractall(target)
            datas.append((str(target / libdir), dest))
    return datas


datas = [('Reloj_Maestro.ico', '.')]
datas += _zip_tcl_tk_datas()
binaries = []
hiddenimports = []
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['reloj_maestro_v2.2.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='reloj_maestro_v2.2',
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
    icon=['Reloj_Maestro.ico'],
)
