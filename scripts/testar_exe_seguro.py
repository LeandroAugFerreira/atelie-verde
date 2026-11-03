"""Exercise a frozen release with an empty isolated DB/vault and no paid calls."""

import argparse
import json
import os
import re
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

PROJECT = Path(__file__).resolve().parents[1]


def wait_ready(process, client):
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError("O executável encerrou antes de ficar pronto.")
        try:
            if client.get("/api/health").json().get("status") == "ok":
                return
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.5)
    raise RuntimeError("A API não ficou pronta em 60 segundos.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder")
    options = parser.parse_args()
    folder = Path(options.folder).resolve()
    executable = folder / "AtelieVerde.exe"
    if not executable.is_file():
        parser.error("Executável não encontrado.")
    # Keep evidence in ignored workspace folders. Never remove existing user data.
    evidence = PROJECT / ".local" / "exe-smoke"
    evidence.mkdir(parents=True, exist_ok=True)
    isolated = Path(tempfile.mkdtemp(prefix="installation-", dir=evidence)).resolve()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    environment = dict(os.environ)
    for key in (
        "TAVILY_API_KEY",
        "OPENAI_API_KEY",
        "JWT_SECRET",
        "DATABASE_URL",
        "RAFINHA_CREDENTIALS_DIR",
    ):
        environment.pop(key, None)
    checks = []
    process = subprocess.Popen(
        [
            str(executable),
            "--no-browser",
            "--no-ollama",
            "--data-root",
            str(isolated),
            "--port",
            str(port),
        ],
        env=environment,
        cwd=folder,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False)
    admin_headers = {}
    try:
        wait_ready(process, client)
        checks.append("health_ok")
        portal = client.get("/")
        assert portal.status_code == 200 and '<div id="root"></div>' in portal.text
        scripts = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', portal.text)
        assert scripts
        for asset in scripts:
            compiled = client.get(asset)
            assert compiled.status_code == 200
            if asset.endswith(".js"):
                assert compiled.headers["content-type"].startswith("text/javascript")
            if asset.endswith(".css"):
                assert compiled.headers["content-type"].startswith("text/css")
        checks.append("frontend_compiled_assets_ok")
        assert client.get("/api/unknown-route").status_code == 404
        assert client.get("/../.env").status_code == 404
        assert client.get("/assets/unknown.js").status_code == 404
        checks.append("unknown_api_and_private_files_denied")
        for mood in (
            "happy",
            "sad",
            "serious",
            "angry",
            "thinking",
            "sleepy",
            "greeting",
            "surprised",
            "shy",
            "skeptical",
            "delighted",
            "celebrating",
        ):
            asset = client.get(f"/rafinha/official/rafinha_{mood}.webp")
            assert asset.status_code == 200 and asset.headers["content-type"].startswith(
                "image/webp"
            )
        checks.append("twelve_original_rafinha_assets_ok")
        password = "AtelieVerde@2026"
        admin_login = client.post(
            "/api/auth/login", json={"email": "admin@atelieverde.local", "password": password}
        )
        customer_login = client.post(
            "/api/auth/login", json={"email": "cliente@atelieverde.local", "password": password}
        )
        assert admin_login.status_code == customer_login.status_code == 200
        admin_data, customer_data = admin_login.json(), customer_login.json()
        assert admin_data["user"]["name"] == "Leandro" and customer_data["user"]["name"] == "Rafael"
        admin_headers = {"Authorization": "Bearer " + admin_data["access_token"]}
        customer_headers = {"Authorization": "Bearer " + customer_data["access_token"]}
        checks.append("admin_customer_login_ok")
        assert client.get("/api/assistant/admin-ai", headers=customer_headers).status_code == 403
        assert (
            client.put(
                "/api/assistant/admin-ai/settings",
                headers=customer_headers,
                json={"mode": "free_only"},
            ).status_code
            == 403
        )
        assert client.post("/api/desktop/shutdown", headers=customer_headers).status_code == 403
        assert client.post("/api/desktop/control/shutdown").status_code == 403
        checks.append("customer_config_and_shutdown_denied")
        status = client.get("/api/assistant/admin-ai", headers=admin_headers)
        assert status.status_code == 200
        settings = status.json()
        assert settings["settings"]["paid_search_enabled"] is False
        assert all(value["has_key"] is False for value in settings["providers"].values())
        assert not (isolated / "RafinhaPublic" / "installation-tavily.bin").exists()
        assert not (isolated / "RafinhaPublic" / "installation-openai.bin").exists()
        assert not (isolated / "RafinhaPublic" / "chatgpt-selection.bin").exists()
        personal = client.get("/api/assistant/connection", headers=admin_headers).json()
        assert not personal["connected"] and not personal["enabled"]
        assert client.get("/api/assistant/status", headers=customer_headers).json()["mode"] == "catalog"
        checks.append("chatgpt_locked_until_own_login")
        checks.append("empty_vault_no_keys_paid_disabled")
        connection = client.get("/api/assistant/connection", headers=customer_headers)
        assert connection.status_code == 403
        checks.append("customer_legacy_personal_connection_denied")
        vault = isolated / "RafinhaPublic" / "desktop-authentication.bin"
        assert vault.read_bytes().startswith(b"DP1")
        encrypted_session = vault.read_bytes()
        assert not (isolated / "Data" / ".jwt-secret").exists()
        checks.append("runtime_jwt_dpapi_outside_package")
        assert (isolated / "Data" / "greenscape.db").is_file()
        assert client.post("/api/desktop/shutdown", headers=admin_headers).status_code == 200
        process.wait(timeout=15)
        assert process.returncode == 0
        assert not (isolated / "Rafinha" / "desktop-runtime.bin").exists()
        checks.append("admin_shutdown_clean_exit")
        process = subprocess.Popen(
            [
                str(executable),
                "--no-browser",
                "--no-ollama",
                "--data-root",
                str(isolated),
                "--port",
                str(port),
            ],
            env=environment,
            cwd=folder,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        wait_ready(process, client)
        assert vault.read_bytes() == encrypted_session
        # The previous session is valid only because this installation retained its own secret.
        assert client.get("/api/auth/me", headers=admin_headers).status_code == 200
        checks.append("restart_preserves_external_database_and_protected_session")
        stopper = subprocess.run(
            [
                str(executable),
                "--stop",
                "--no-browser",
                "--no-ollama",
                "--data-root",
                str(isolated),
            ],
            env=environment,
            cwd=folder,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        assert stopper.returncode == 0
        process.wait(timeout=15)
        assert process.returncode == 0
        checks.append("local_owner_stop_command_ok")
        report = {"ok": True, "checks": checks, "isolated_data": str(isolated), "external_calls": 0}
        (evidence / "latest-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    finally:
        if process.poll() is None:
            try:
                if admin_headers:
                    client.post("/api/desktop/shutdown", headers=admin_headers)
                process.wait(timeout=10)
            except (httpx.HTTPError, subprocess.TimeoutExpired):
                process.terminate()
                process.wait(timeout=10)
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
