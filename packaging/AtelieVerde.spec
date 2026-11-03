# Build application data only from the explicit public allowlist.
from pathlib import Path
import hashlib
import sys

project = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(project / "packaging"))
from build_manifest import application_files

public_files = application_files(project)
input_files = [source for source, _ in public_files] + list((project / "backend" / "app").glob("*.py")) + [project / "packaging" / "launcher.py"]
def snapshot():
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in input_files}
input_snapshot = snapshot()
datas = [(str(source), str(Path(target).parent)) for source, target in public_files]
a = Analysis(
    [str(project / "packaging" / "launcher.py")],
    pathex=[str(project / "backend")],
    binaries=[], datas=datas,
    hiddenimports=[
        "uvicorn.logging", "uvicorn.loops.asyncio", "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan.on", "pwdlib.hashers.argon2", "alembic.ddl.sqlite",
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["pytest", "ruff", "tkinter", "unittest", "psycopg", "psycopg_binary"],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="AtelieVerde",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=True,
)
collect = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="AtelieVerde")
if snapshot() != input_snapshot:
    raise RuntimeError("Arquivos da aplicação mudaram durante o build. Gere uma nova saída antes de distribuir.")
