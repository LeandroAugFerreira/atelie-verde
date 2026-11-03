"""Desktop-specific routes must not expose files or accept untrusted shutdown requests."""

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("desktop_launcher", PACKAGE / "launcher.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.fixture
def desktop(monkeypatch, tmp_path):
    portal = tmp_path / "frontend" / "dist"
    portal.mkdir(parents=True)
    (portal / "index.html").write_text("<html>portal shell</html>")
    (portal / "assets").mkdir()
    (portal / "assets" / "main.js").write_text("public script")
    application = FastAPI()
    server = types.SimpleNamespace(should_exit=False)

    def administrator(request: Request):
        if request.headers.get("Authorization") != "Bearer synthetic-admin":
            raise HTTPException(403, "Admin required")
        return {"role": "admin"}

    monkeypatch.setitem(sys.modules, "app.main", types.SimpleNamespace(app=application))
    monkeypatch.setitem(sys.modules, "app.security", types.SimpleNamespace(admin=administrator))
    monkeypatch.setattr(launcher, "resource_root", lambda: tmp_path)
    client = TestClient(launcher.application(server, 8017, "synthetic-owner-control"))
    return client, server


def test_public_assets_and_client_route_reloads(desktop):
    client, _ = desktop
    assert client.get("/").status_code == 200
    assert client.get("/login").text == "<html>portal shell</html>"
    assert client.get("/assets/main.js").text == "public script"
    assert client.get("/assets/main.js").headers["content-type"].startswith("text/javascript")


@pytest.mark.parametrize(
    "path", ["/.env", "/api/missing", "/.local/credentials", "/assets/missing.js"]
)
def test_hidden_and_missing_api_paths_do_not_fall_back_to_portal(desktop, path):
    client, _ = desktop
    assert client.get(path).status_code == 404


def test_shutdown_rejects_customer_and_external_origins(desktop):
    client, server = desktop
    assert (
        client.post(
            "/api/desktop/shutdown", headers={"Authorization": "Bearer customer"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/desktop/shutdown",
            headers={
                "Authorization": "Bearer synthetic-admin",
                "Origin": "https://external.example",
            },
        ).status_code
        == 403
    )
    assert client.post("/api/desktop/control/shutdown").status_code == 403
    assert (
        client.post(
            "/api/desktop/control/shutdown",
            headers={
                "X-Atelie-Desktop": "synthetic-owner-control",
                "Origin": "https://external.example",
            },
        ).status_code
        == 403
    )
    assert server.should_exit is False


def test_local_owner_control_can_stop_the_server_without_saving_a_portal_token(desktop):
    client, server = desktop
    assert (
        client.post(
            "/api/desktop/control/shutdown", headers={"X-Atelie-Desktop": "synthetic-owner-control"}
        ).status_code
        == 200
    )
    assert server.should_exit is True


def test_public_installation_ignores_developer_environment_and_uses_separate_vault(
    monkeypatch, tmp_path
):
    names = [
        "APP_ENV",
        "DATA_DIR",
        "DATABASE_URL",
        "JWT_SECRET",
        "RAFINHA_CREDENTIALS_DIR",
        "RAFINHA_PROVIDER",
        "RAFINHA_MODE",
        "RAFINHA_OLLAMA_URL",
        "RAFINHA_OLLAMA_MODEL",
        "RAFINHA_ALLOW_DEV_API_KEYS",
        "TAVILY_API_KEY",
        "OPENAI_API_KEY",
        "CORS_ORIGINS",
        "SEED_DEMO",
        "WEB_SEARCH_URL",
        "WEB_SEARCH_PROVIDER",
    ]
    for name in names:
        monkeypatch.setenv(name, os.getenv(name, ""))
    monkeypatch.setenv("RAFINHA_CREDENTIALS_DIR", str(tmp_path / "developer-vault"))
    monkeypatch.setenv("RAFINHA_MODE", "hybrid")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-developer-credential-not-real")
    monkeypatch.setenv("RAFINHA_ALLOW_DEV_API_KEYS", "true")
    monkeypatch.setattr(launcher, "resource_root", lambda: tmp_path / "bundle")
    monkeypatch.setattr(
        launcher.logging.handlers,
        "RotatingFileHandler",
        lambda *args, **kwargs: types.SimpleNamespace(setFormatter=lambda value: None),
    )
    monkeypatch.setattr(launcher.logging, "basicConfig", lambda **kwargs: None)
    root = launcher.configure(
        types.SimpleNamespace(data_root=str(tmp_path / "public-installation"), no_ollama=False)
    )
    assert os.environ["RAFINHA_CREDENTIALS_DIR"] == str(root / "RafinhaPublic")
    assert os.environ["RAFINHA_MODE"] == "chatgpt"
    assert os.environ["RAFINHA_PROVIDER"] == "catalog" and not os.environ["RAFINHA_OLLAMA_MODEL"]
    assert (
        "OPENAI_API_KEY" not in os.environ and os.environ["RAFINHA_ALLOW_DEV_API_KEYS"] == "false"
    )
