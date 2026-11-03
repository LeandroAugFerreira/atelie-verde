"""Explicit application-data allowlist, shared by the spec and release verifier."""

from pathlib import Path

PUBLIC_FOLDERS = {"assets", "catalog-media", "decor", "plants", "projects", "rafinha", "references"}
PUBLIC_SUFFIXES = {".js", ".css", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".woff", ".woff2"}


def application_files(project):
    project = Path(project).resolve()
    entries = []
    frontend = project / "frontend" / "dist"
    if not (frontend / "index.html").is_file():
        raise RuntimeError("Compile o frontend antes de empacotar.")
    for path in sorted(frontend.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(frontend)
        allowed = (
            relative.as_posix() == "index.html"
            or (relative.parts[0] in PUBLIC_FOLDERS and path.suffix.lower() in PUBLIC_SUFFIXES)
            or relative.as_posix() == "rafinha/official/manifest.json"
        )
        if not allowed or path.is_symlink():
            raise RuntimeError(f"Recurso não autorizado para distribuição: {relative.as_posix()}")
        entries.append((path, "frontend/dist/" + relative.as_posix()))
    for name in (
        "botanical_catalog.json",
        "photo_manifest.json",
        "photo_quality_manifest.json",
        "photo_curated_manifest.json",
        "product_media_manifest.json",
    ):
        entries.append((project / "backend" / "app" / name, "app/" + name))
    entries.append((project / "backend" / "alembic.ini", "backend/alembic.ini"))
    migrations = project / "backend" / "migrations"
    for path in sorted(migrations.rglob("*")):
        relative = path.relative_to(migrations)
        if not path.is_file() or "__pycache__" in relative.parts:
            continue
        if path.is_symlink() or not (
            relative.as_posix() in {"env.py", "script.py.mako"}
            or len(relative.parts) == 2
            and relative.parts[0] == "versions"
            and path.suffix == ".py"
        ):
            raise RuntimeError("Arquivo de migração não autorizado.")
        entries.append((path, "backend/migrations/" + relative.as_posix()))
    return entries
