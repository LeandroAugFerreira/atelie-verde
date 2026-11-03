"""Fail a release containing private files, credential-shaped literals, or known local secrets.

Identifying a setting name such as OPENAI_API_KEY is expected; embedding its value is not.
Values stay in process memory and are never printed or written to the report.
"""

import argparse
import ast
import hashlib
import json
import marshal
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "packaging"))
sys.path.insert(0, str(PROJECT / "backend"))
from build_manifest import application_files

FORBIDDEN_PARTS = {
    ".env",
    ".local",
    ".git",
    ".venv",
    "node_modules",
    "uploads",
    "credentials",
    "data",
    "logs",
    "recordings",
    "__pycache__",
    "tests",
    "test-results",
    "playwright-report",
}
FORBIDDEN_SUFFIXES = {
    ".ogg",
    ".mp3",
    ".wav",
    ".mp4",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log",
    ".pid",
    ".bin",
}
SECRET_PATTERNS = {
    "openai_key_literal": re.compile(rb"\bsk-[A-Za-z0-9_-]{17,}\b"),
    "tavily_key_literal": re.compile(rb"\btvly-[A-Za-z0-9_-]{15,}\b"),
    "jwt_literal": re.compile(
        rb"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\b"
    ),
}
SECRET_FIELDS = {
    "key",
    "api_key",
    "access_token",
    "refresh_token",
    "id_token",
    "jwt_secret",
    "client_secret",
}
PUBLIC_PROTOCOL_IDENTIFIERS = {b"sk-ecdsa-sha2-nistp256", b"sk-ssh-ed25519"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def known_secrets():
    values = set()

    def collect(value):
        if isinstance(value, dict):
            for name, child in value.items():
                if name.lower() in SECRET_FIELDS and isinstance(child, str) and len(child) >= 20:
                    values.add(child.encode())
                elif isinstance(child, (dict, list)):
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    for key in ("JWT_SECRET", "TAVILY_API_KEY", "OPENAI_API_KEY"):
        value = os.getenv(key, "")
        if len(value) >= 20:
            values.add(value.encode())
    from app import assistant_credentials as vault
    from dotenv import dotenv_values

    for key, value in dotenv_values(PROJECT / ".env").items():
        if key in {"JWT_SECRET", "TAVILY_API_KEY", "OPENAI_API_KEY"} and value and len(value) >= 20:
            values.add(value.encode())
    if vault.root().is_dir():
        for path in vault.root().glob("*.bin"):
            if path.stem.startswith("account-") and path.stem[8:].isdigit():
                collect(vault.load(int(path.stem[8:])))
            elif re.fullmatch(r"[a-z-]{3,60}", path.stem):
                collect(vault.protected_read(path.stem))
    return values


def secret_findings(content, label, values):
    findings = []
    for category, pattern in SECRET_PATTERNS.items():
        # Cryptography supports these published OpenSSH algorithm identifiers. A longer value
        # sharing their prefix is still rejected, and actual known local values always are.
        if any(
            match.group() not in PUBLIC_PROTOCOL_IDENTIFIERS for match in pattern.finditer(content)
        ):
            findings.append({"path": label, "reason": category})
    if any(value in content or value.decode().encode("utf-16le") in content for value in values):
        findings.append({"path": label, "reason": "known_local_secret"})
    return findings


def sources(values):
    findings = []
    files = [p for p, _ in application_files(PROJECT)]
    files.extend((PROJECT / "backend" / "app").glob("*.py"))
    files.extend((PROJECT / "packaging").glob("*.py"))
    for path in files:
        label = path.relative_to(PROJECT).as_posix()
        findings.extend(secret_findings(path.read_bytes(), label, values))
        if path.suffix == ".py":
            findings.extend(hardcoded_settings(path.read_text(encoding="utf-8"), label))
    return findings


def hardcoded_settings(source, label):
    """Catch newly introduced JWT/API secrets even when they have no provider prefix."""

    def sensitive(node):
        if isinstance(node, ast.Name):
            name = node.id.lower()
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            name = str(node.slice.value).lower()
        elif isinstance(node, ast.Constant):
            name = str(node.value).lower()
        else:
            return False
        return name in {
            "secret",
            "jwt_secret",
            "tavily_api_key",
            "openai_api_key",
            "api_key",
            "access_token",
            "refresh_token",
            "client_secret",
        }

    def literal(node):
        return (
            isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) >= 20
        )

    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Assign)
            and literal(node.value)
            and any(sensitive(target) for target in node.targets)
        ):
            return [{"path": label, "reason": "hardcoded_secret_setting"}]
        if isinstance(node, ast.AnnAssign) and literal(node.value) and sensitive(node.target):
            return [{"path": label, "reason": "hardcoded_secret_setting"}]
        if isinstance(node, ast.Dict) and any(
            sensitive(key) and literal(value) for key, value in zip(node.keys, node.values)
        ):
            return [{"path": label, "reason": "hardcoded_secret_setting"}]
    return []


def archives(path, values):
    from PyInstaller.archive.readers import CArchiveReader

    findings, count = [], 0
    reader = CArchiveReader(str(path))
    for name in reader.toc:
        if name.endswith(".pyz"):
            pyz = reader.open_embedded_archive(name)
            for module in pyz.toc:
                extracted = pyz.extract(module)
                raw = extracted if isinstance(extracted, bytes) else marshal.dumps(extracted)
                findings.extend(secret_findings(raw, "archive/" + module, values))
                count += 1
        else:
            content = reader.extract(name)
            if content:
                findings.extend(secret_findings(content, "archive/" + name, values))
                count += 1
    return findings, count


def verify(folder, *, seal=False):
    folder = Path(folder).resolve()
    if not (folder / "AtelieVerde.exe").is_file():
        raise RuntimeError("Executável não encontrado.")
    values = known_secrets()
    findings = sources(values)
    app_entries = {target: digest(source) for source, target in application_files(PROJECT)}
    inventory = {}
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(folder).as_posix()
        if relative in {"release-manifest.json", "security-report.json"}:
            findings.extend(secret_findings(path.read_bytes(), relative, values))
            continue
        if (
            path.is_symlink()
            or any(
                part.lower() in FORBIDDEN_PARTS or part.lower().startswith(".env")
                for part in path.relative_to(folder).parts
            )
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
            or path.name.lower() in {"host-id.txt", ".jwt-secret"}
        ):
            findings.append({"path": relative, "reason": "forbidden_private_file"})
        inventory[relative] = digest(path)
        findings.extend(secret_findings(path.read_bytes(), relative, values))
    for target, expected in app_entries.items():
        path = folder / "_internal" / target
        if not path.is_file() or digest(path) != expected:
            findings.append({"path": target, "reason": "application_allowlist_mismatch"})
    # Source/runtime data under the application namespaces must match the data allowlist exactly.
    for relative in inventory:
        if relative.startswith(("_internal/frontend/", "_internal/backend/", "_internal/app/")):
            target = relative.removeprefix("_internal/")
            if target not in app_entries:
                findings.append({"path": relative, "reason": "unapproved_application_data"})
    archive_findings, modules = archives(folder / "AtelieVerde.exe", values)
    findings.extend(archive_findings)
    manifest_path = folder / "release-manifest.json"
    if not seal:
        if not manifest_path.is_file():
            findings.append({"path": "release-manifest.json", "reason": "missing_release_manifest"})
        elif json.loads(manifest_path.read_text(encoding="utf-8")).get("files") != inventory:
            findings.append(
                {"path": "release-manifest.json", "reason": "release_inventory_changed"}
            )
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ok": not findings,
        "files_checked": len(inventory),
        "archive_entries_checked": modules,
        "known_values_checked": len(values),
        "application_data_files": len(app_entries),
        "findings": findings,
    }
    if seal and not findings:
        manifest_path.write_text(json.dumps({"files": inventory}, indent=2), encoding="utf-8")
    (folder / "security-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return not findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?")
    parser.add_argument("--seal", action="store_true")
    parser.add_argument("--source-only", action="store_true")
    options = parser.parse_args()
    if options.source_only:
        findings = sources(known_secrets())
        print(json.dumps({"ok": not findings, "findings": findings}, ensure_ascii=False))
        return 0 if not findings else 1
    if not options.folder:
        parser.error("Informe a pasta de distribuição.")
    return 0 if verify(options.folder, seal=options.seal) else 1


if __name__ == "__main__":
    raise SystemExit(main())
