"""Regression tests for private-file rejection and secrets inside compiled constants."""

import importlib.util
import marshal
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from build_manifest import application_files

spec = importlib.util.spec_from_file_location(
    "release_checker", PROJECT.parent / "scripts" / "verificar_release.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def public_tree(root):
    frontend = root / "frontend" / "dist"
    frontend.mkdir(parents=True)
    (frontend / "index.html").write_text("<html>public portal</html>")
    app = root / "backend" / "app"
    app.mkdir(parents=True)
    for name in (
        "botanical_catalog.json",
        "photo_manifest.json",
        "photo_quality_manifest.json",
        "photo_curated_manifest.json",
        "product_media_manifest.json",
    ):
        (app / name).write_text("{}")
    (root / "backend" / "alembic.ini").write_text("[alembic]")
    (root / "backend" / "migrations").mkdir()
    return frontend


@pytest.mark.parametrize(
    "name", [".env", "customer.db", "Audio 1.ogg", "token.json", "index.js.map"]
)
def test_private_or_unapproved_input_refuses_build(tmp_path, name):
    frontend = public_tree(tmp_path)
    (frontend / name).write_text("private content")
    with pytest.raises(RuntimeError, match="não autorizado"):
        application_files(tmp_path)


def test_allowlist_includes_public_files_without_copying_backend_state(tmp_path):
    frontend = public_tree(tmp_path)
    (frontend / "assets").mkdir()
    (frontend / "assets" / "portal.js").write_text("public")
    data = tmp_path / "backend" / "data"
    data.mkdir()
    (data / "greenscape.db").write_bytes(b"private database")
    (tmp_path / ".env").write_text("private development settings")
    targets = [target for _, target in application_files(tmp_path)]
    assert "frontend/dist/assets/portal.js" in targets
    assert not any("data/" in target or ".env" in target for target in targets)


def test_compiled_credentials_are_detected_without_echoing_value():
    # Deliberately synthetic data; the checker must inspect decompressed PYZ constants too.
    secret = "arbitrary-private-session-value-123456789"
    compiled = marshal.dumps(compile("SECRET = " + repr(secret), "synthetic.py", "exec"))
    findings = checker.secret_findings(compiled, "archive/application", {secret.encode()})
    assert findings == [{"path": "archive/application", "reason": "known_local_secret"}]
    assert secret not in repr(findings)


def test_setting_identifiers_do_not_count_as_embedded_credentials():
    content = b'os.getenv("OPENAI_API_KEY"); os.getenv("TAVILY_API_KEY"); os.getenv("JWT_SECRET")'
    assert checker.secret_findings(content, "public/backend.py", set()) == []
    assert (
        checker.secret_findings(b"sk-ecdsa-sha2-nistp256@openssh.com", "archive/ssh", set()) == []
    )
    assert checker.secret_findings(
        b"sk-ecdsa-sha2-nistp256", "archive/ssh", {b"sk-ecdsa-sha2-nistp256"}
    ) == [{"path": "archive/ssh", "reason": "known_local_secret"}]
    assert checker.secret_findings(
        b"sk-ecdsa-sha2-nistp256-actual-key-shaped-suffix", "archive/application", set()
    )


def test_a_new_secret_without_a_provider_prefix_cannot_be_hardcoded():
    value = "new-private-random-value-that-is-not-in-local-vault"
    source = 'os.environ["JWT_SECRET"] = ' + repr(value)
    findings = checker.hardcoded_settings(source, "backend/app/security.py")
    assert findings == [{"path": "backend/app/security.py", "reason": "hardcoded_secret_setting"}]
    assert value not in repr(findings)
    assert (
        checker.hardcoded_settings('SECRET = os.getenv("JWT_SECRET")', "backend/app/security.py")
        == []
    )


@pytest.mark.parametrize("prefix", ["sk-proj-", "tvly-"])
def test_unrecognized_provider_key_shapes_are_still_rejected(prefix):
    content = (prefix + "synthetic-example-value-only-1234567890").encode()
    findings = checker.secret_findings(content, "archive/application", set())
    assert findings and all("synthetic" not in str(item) for item in findings)
