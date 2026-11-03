"""Windows desktop launcher: loopback server, public resources, external protected state."""

import argparse
import asyncio
import ctypes
import json
import logging
import logging.handlers
import mimetypes
import os
import secrets
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def resource_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def local_request(url, *, data=None, headers=None):
    request = urllib.request.Request(url, data=data, headers=headers or {})
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=2)


def local_model():
    """Select an installed local model only. Never pull a model or start an external provider."""
    try:
        with local_request("http://127.0.0.1:11434/api/tags") as response:
            models = json.load(response).get("models", [])
        names = sorted(
            item["name"]
            for item in models
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and not item.get("remote_host")
            and not item.get("remote_model")
            and ":cloud" not in item["name"]
        )
        return names[0] if names else ""
    except (OSError, ValueError, TypeError, KeyError):
        return ""


def configure(options):
    root = (
        Path(options.data_root).expanduser().resolve()
        if options.data_root
        else Path(os.environ["LOCALAPPDATA"]) / "AtelieVerde"
    )
    bundle = resource_root().resolve()
    if root == bundle or bundle in root.parents:
        raise RuntimeError("Use uma pasta de dados fora da distribuição.")
    if getattr(sys, "frozen", False):
        executable_folder = Path(sys.executable).resolve().parent
        if root == executable_folder or executable_folder in root.parents:
            raise RuntimeError("Use uma pasta de dados fora da distribuição.")
    data = root / "Data"
    data.mkdir(parents=True, exist_ok=True)
    # A distributed build ignores developer environment, database URLs, and API key variables.
    for key in (
        "JWT_SECRET",
        "DATABASE_URL",
        "DATA_DIR",
        "RAFINHA_CREDENTIALS_DIR",
        "TAVILY_API_KEY",
        "OPENAI_API_KEY",
        "RAFINHA_ALLOW_DEV_API_KEYS",
        "WEB_SEARCH_URL",
        "WEB_SEARCH_PROVIDER",
        "RAFINHA_OLLAMA_MODEL",
        "RAFINHA_OLLAMA_URL",
        "RAFINHA_PROVIDER",
        "RAFINHA_MODE",
        "CORS_ORIGINS",
        "SEED_DEMO",
    ):
        os.environ.pop(key, None)
    os.environ.update(
        APP_ENV="production",
        DATA_DIR=str(data),
        DATABASE_URL="sqlite:///" + (data / "greenscape.db").as_posix(),
        RAFINHA_CREDENTIALS_DIR=str(root / "RafinhaPublic"),
        RAFINHA_ALLOW_DEV_API_KEYS="false",
        RAFINHA_PROVIDER="catalog",
        RAFINHA_MODE="chatgpt",
        RAFINHA_OLLAMA_URL="http://127.0.0.1:11434",
        RAFINHA_OLLAMA_MODEL="",
        SEED_DEMO="true",
    )
    log_dir = root / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_dir / "desktop.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    return root


def install_session_secret():
    # Run only after acquiring the installation lock, so two first starts cannot replace the key.
    from app.assistant_credentials import protected_read, protected_save

    record = protected_read("desktop-authentication")
    if not isinstance(record.get("jwt_secret"), str) or len(record["jwt_secret"]) < 48:
        record = {"jwt_secret": secrets.token_urlsafe(64)}
        protected_save("desktop-authentication", record)
    os.environ["JWT_SECRET"] = record["jwt_secret"]


def stop():
    from app.assistant_credentials import protected_read

    record = protected_read("desktop-runtime")
    if not record:
        return 0
    try:
        with local_request(
            f"http://127.0.0.1:{int(record['port'])}/api/desktop/control/shutdown",
            data=b"",
            headers={"X-Atelie-Desktop": record["control"]},
        ):
            return 0
    except (OSError, KeyError, ValueError):
        return 1


def migrate():
    from alembic import command
    from alembic.config import Config

    backend = resource_root() / "backend"
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    command.upgrade(config, "head")


def application(server, port, control):
    from app.assistant_request import local_access
    from app.main import app
    from app.security import admin
    from fastapi import Depends, HTTPException, Request
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from starlette.exceptions import HTTPException as StaticHTTPException

    # Annotation globals are needed by FastAPI when postponed introspection resolves dependencies.
    globals()["Request"] = Request
    # Windows file associations can otherwise send WebP or module scripts as octet-stream.
    for suffix, media_type in {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "text/javascript",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".json": "application/json",
    }.items():
        mimetypes.add_type(media_type, suffix)

    @app.post("/api/desktop/shutdown", include_in_schema=False)
    async def shutdown(request: Request, user=Depends(admin)):
        if not local_access(request):
            raise HTTPException(403, "Ação disponível na instalação local.")
        server.should_exit = True
        return {"status": "stopping"}

    @app.post("/api/desktop/control/shutdown", include_in_schema=False)
    async def stop_owner(request: Request):
        if not local_access(request) or not secrets.compare_digest(
            request.headers.get("X-Atelie-Desktop", ""), control
        ):
            raise HTTPException(403, "Ação disponível ao proprietário desta instalação.")
        server.should_exit = True
        return {"status": "stopping"}

    static = resource_root() / "frontend" / "dist"
    if not (static / "index.html").is_file():
        raise RuntimeError("Os arquivos públicos do portal estão incompletos.")

    class PortalFiles(StaticFiles):
        async def get_response(self, path, scope):
            path = path.replace("\\", "/").lstrip("/")
            if path == ".":
                path = ""
            # Unknown API paths remain API 404s; they must never return the HTML shell.
            if (
                path == "api"
                or path.startswith("api/")
                or any(part.startswith(".") for part in path.split("/") if part)
            ):
                raise HTTPException(404, "Recurso não encontrado.")
            try:
                return await super().get_response(path, scope)
            except StaticHTTPException as error:
                if error.status_code != 404 or Path(path).suffix:
                    raise
                return FileResponse(static / "index.html", media_type="text/html")

    app.mount("/", PortalFiles(directory=static, html=True), name="portal")
    return app


def run(options, root):
    import msvcrt

    import uvicorn
    from app.assistant_credentials import protected_read, protected_remove, protected_save

    # OS lock prevents concurrent schema changes and two writers fighting over startup metadata.
    lock = (root / "Data" / ".desktop-lock").open("a+b")
    lock.seek(0)
    lock.write(b"0")
    lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock.close()
        record = protected_read("desktop-runtime")
        if record.get("port") and not options.no_browser:
            webbrowser.open(f"http://127.0.0.1:{int(record['port'])}")
        return 0
    try:
        install_session_secret()
        logging.info("Aplicando migrações na instalação local.")
        migrate()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", options.port))
        listener.listen(128)
        port = listener.getsockname()[1]
        os.environ["CORS_ORIGINS"] = f"http://127.0.0.1:{port},http://localhost:{port}"
        control = secrets.token_urlsafe(48)
        config = uvicorn.Config(
            "app.main:app",
            host="127.0.0.1",
            port=port,
            log_config=None,
            access_log=False,
            loop="asyncio",
            http="h11",
            ws="none",
            proxy_headers=False,
        )
        server = uvicorn.Server(config)
        logging.info("Carregando API e recursos públicos do portal.")
        config.app = application(server, port, control)
        protected_save("desktop-runtime", {"port": port, "control": control, "pid": os.getpid()})

        def ready():
            for _ in range(120):
                if server.should_exit:
                    return
                try:
                    with local_request(f"http://127.0.0.1:{port}/api/health") as response:
                        if json.load(response).get("status") == "ok":
                            if not options.no_browser:
                                webbrowser.open(f"http://127.0.0.1:{port}")
                            return
                except (OSError, ValueError):
                    pass
                time.sleep(0.5)

        if not options.no_browser:
            threading.Thread(target=ready, daemon=True).start()
        try:
            logging.info("Iniciando servidor exclusivo de loopback.")
            asyncio.run(server.serve(sockets=[listener]))
        finally:
            listener.close()
            protected_remove("desktop-runtime")
    finally:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        lock.close()
    return 0


def main():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(resource_root() / "backend"))
    parser = argparse.ArgumentParser(description="Ateliê Verde: portal local Windows")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-ollama", action="store_true")
    parser.add_argument("--data-root", help="Pasta externa de dados (testes ou instalação isolada)")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--stop", action="store_true")
    options = parser.parse_args()
    try:
        root = configure(options)
        return stop() if options.stop else run(options, root)
    except Exception as error:
        # Do not serialize exceptions, environment, API headers, or user data in startup diagnostics.
        logging.error("Não foi possível iniciar o portal (%s).", type(error).__name__)
        if not options.no_browser:
            ctypes.windll.user32.MessageBoxW(
                None,
                "Não foi possível iniciar o Ateliê Verde. Consulte Logs/desktop.log na pasta de dados da instalação.",
                "Ateliê Verde",
                0x10,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
