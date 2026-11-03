"""Opt-in personal OpenAI connections; loopback OAuth and an encrypted per-user vault."""

import asyncio
import base64
import hashlib
import json
import re
import secrets
import threading
import time
import uuid
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal
from urllib.parse import parse_qs, urlencode, urlparse
from zoneinfo import ZoneInfo

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import assistant_credentials as vault
from . import assistant_runtime
from .assistant_request import local_access
from .security import admin as administrator

router = APIRouter(prefix="/assistant/connection")
API = "https://api.openai.com/v1"
ISSUER = "https://auth.openai.com"
TOKEN_URL = ISSUER + "/api/accounts/oauth/token"
SCOPE = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
_lock = threading.RLock()
_attempts = {}


def current_user(request: Request, user=Depends(administrator)):
    if not local_access(request):
        raise HTTPException(403, "Acesse suas conexões administrativas pela instalação local.")
    return user


def profile_id(user):
    return assistant_runtime.management_profile(user.id)


class ConnectionError(Exception):
    pass


def default_model(available):
    # Use an account-authorized workhorse for conversation rather than defaulting
    # to the most expensive reasoning tier; preserve explicit saved choices.
    return next((m["id"] for m in available if m["id"].endswith("-sol")), available[0]["id"])


async def remote(method, url, bearer=None, *, data=None, timeout=6):
    headers = {"Accept": "application/json"}
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    async with asyncio.timeout(timeout):
        async with httpx.AsyncClient(
            timeout=timeout, trust_env=False, follow_redirects=False
        ) as client:
            async with client.stream(method, url, headers=headers, data=data) as response:
                response.raise_for_status()
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 600000:
                        raise ConnectionError("Resposta da conexão excedeu o limite.")
                value = json.loads(body)
                if not isinstance(value, dict):
                    raise ConnectionError("Resposta de conexão inválida.")
                return value


async def models(token, kind, timeout=6):
    body = await remote("GET", API + "/models", token, timeout=timeout)
    rows = body.get("models" if kind == "chatgpt" else "data", [])
    if not isinstance(rows, list):
        raise ConnectionError("A conta não retornou uma lista de modelos válida.")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("slug" if kind == "chatgpt" else "id", "")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,100}", name):
            continue
        if kind == "chatgpt" and row.get("visibility") != "list":
            continue
        if kind == "api" and (
            not name.startswith(("gpt-", "chat-", "o1", "o3", "o4"))
            or any(w in name for w in ["image", "audio", "realtime", "transcrib"])
        ):
            continue
        result.append({"id": name, "name": str(row.get("display_name", name))[:100]})
    if not result:
        raise ConnectionError("Nenhum modelo compatível foi liberado nesta conta.")
    return result[:80]


def public_status(user_id):
    connection = vault.load(user_id)
    counters = vault.usage(user_id)
    day = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    with _lock:
        attempt = _attempts.get(user_id, {})
        login_state = attempt.get("status", "idle")
        login_message = attempt.get("message", "")
    return {
        "connected": bool(connection),
        "kind": (connection or {}).get("kind", "local"),
        "enabled": (connection or {}).get("enabled", False),
        "model": (connection or {}).get("model", ""),
        "models": (connection or {}).get("models", []),
        "email": (connection or {}).get("email", ""),
        "state": (connection or {}).get("state", "local"),
        "message": (connection or {}).get("message", ""),
        "daily_limit": (connection or {}).get("daily_limit", 20),
        "response_timeout": (connection or {}).get(
            "response_timeout", 30 if assistant_runtime.chatgpt_mode() else 10
        ),
        "web_enabled": (connection or {}).get("web_enabled", False),
        "web_mode": (connection or {}).get("web_mode", "automatic"),
        "web_images": (connection or {}).get("web_images", True),
        "web_message": (connection or {}).get("web_message", ""),
        "attempts_today": counters.get("calls", 0) if counters.get("day") == day else 0,
        "login_state": login_state,
        "login_message": login_message,
        "fallback": "Orientações do catálogo"
        if assistant_runtime.chatgpt_mode()
        else "Rafinha local e catálogo",
    }


def ready(user_id):
    value = vault.load(user_id)
    day = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    counters = vault.usage(user_id)
    exhausted = (
        value
        and counters.get("day") == day
        and counters.get("calls", 0) >= value.get("daily_limit", 20)
    )
    return (
        value
        if value
        and value.get("enabled")
        and value.get("model")
        and value.get("state") == "ready"
        and not exhausted
        and value.get("cooldown_until", 0) <= time.time()
        else None
    )


@router.get("")
def status(user=Depends(current_user)):
    return public_status(profile_id(user))


class ApiConnection(BaseModel):
    key: str = Field(min_length=20, max_length=300)


@router.post("/api")
def connect_api(body: ApiConnection, request: Request, user=Depends(current_user)):
    if not local_access(request):
        raise HTTPException(403, "Configure a chave pessoal na instalação local.")
    if not re.fullmatch(r"sk-[A-Za-z0-9_-]{17,297}", body.key):
        raise HTTPException(422, "Informe uma chave pessoal válida da API OpenAI.")
    try:
        available = asyncio.run(models(body.key, "api"))
    except (TimeoutError, httpx.HTTPError, ValueError, ConnectionError):
        raise HTTPException(
            422,
            "Não foi possível verificar esta chave. Confira a chave e o acesso à API; o Rafinha local continua disponível.",
        ) from None
    vault.save(
        user.id,
        {
            "generation": uuid.uuid4().hex,
            "kind": "api",
            "api_key": body.key,
            "enabled": False,
            "model": "",
            "models": available,
            "state": "ready",
            "daily_limit": 20,
            "message": "Chave verificada. Escolha um modelo para usar a API, que tem cobrança por uso.",
        },
    )
    return public_status(user.id)


class Options(BaseModel):
    enabled: bool | None = None
    model: str | None = Field(default=None, max_length=100)
    daily_limit: int | None = Field(default=None, ge=1, le=100)
    response_timeout: Literal[10, 30] | None = None
    web_enabled: bool | None = None
    web_mode: Literal["automatic", "on_request"] | None = None
    web_images: bool | None = None


@router.put("")
def configure(body: Options, request: Request, user=Depends(current_user)):
    if not local_access(request):
        raise HTTPException(
            403, "Altere sua conexão e as preferências de pesquisa na instalação local."
        )
    owner_id = profile_id(user)
    value = vault.load(owner_id)
    if not value:
        raise HTTPException(
            409, "Conecte sua própria conta primeiro ou continue com o Rafinha local."
        )
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    enabled = updates.get("enabled", value.get("enabled", False))
    model = updates.get("model", value.get("model", ""))
    if enabled and value["kind"] == "chatgpt" and not model and value.get("models"):
        model = updates["model"] = default_model(value["models"])
    if enabled and value["kind"] == "chatgpt":
        updates["priority"] = "cloud"
    if enabled and model not in {m["id"] for m in value.get("models", [])}:
        raise HTTPException(422, "Selecione um modelo liberado para esta conta.")
    if updates.get("enabled") is True and value.get("state") != "ready":
        raise HTTPException(409, "Entre novamente na sua conta para reativar a conexão.")
    if "enabled" in updates and value.get("state") == "ready":
        updates["message"] = ""
    if "response_timeout" in updates and value.get("state") == "ready":
        updates.update({"message": "", "cooldown_until": 0})
    if "web_enabled" in updates:
        updates["web_message"] = ""
    if not vault.update(owner_id, value["generation"], updates):
        raise HTTPException(409, "A conexão mudou. Atualize a tela e tente novamente.")
    if assistant_runtime.chatgpt_mode() and value["kind"] == "chatgpt":
        assistant_runtime.select_profile(owner_id)
    return public_status(owner_id)


def cancel_attempt(user_id):
    with _lock:
        old = _attempts.pop(user_id, None)
    if old and old.get("server"):
        if old.get("timer"):
            old["timer"].cancel()
        threading.Thread(target=close_server, args=(old["server"],), daemon=True).start()


def close_server(server):
    server.shutdown()
    server.server_close()


def close_all():
    for user_id in list(_attempts):
        cancel_attempt(user_id)


@router.delete("", status_code=204)
def disconnect(user=Depends(current_user)):
    owner_id = profile_id(user)
    cancel_attempt(owner_id)
    assistant_runtime.unselect(owner_id)
    vault.remove(owner_id)


def local_request(request):
    origin = request.headers.get("origin")
    return request.client.host in {"127.0.0.1", "::1"} and (
        not origin or urlparse(origin).hostname in {"127.0.0.1", "localhost", "::1"}
    )


async def verify_identity(encoded, client_id, nonce=None, expected_subject=None):
    header = jwt.get_unverified_header(encoded)
    if header.get("alg") != "RS256" or not header.get("kid"):
        raise ConnectionError("Identidade OpenAI inválida.")
    jwks = await remote("GET", ISSUER + "/.well-known/jwks.json")
    key = next(
        (
            k
            for k in jwks.get("keys", [])
            if k.get("kid") == header["kid"] and k.get("kty") == "RSA"
        ),
        None,
    )
    if not key:
        raise ConnectionError("Não foi possível verificar a identidade OpenAI.")
    claims = jwt.decode(
        encoded,
        jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key)),
        algorithms=["RS256"],
        audience=client_id,
        issuer=ISSUER,
        options={"require": ["iss", "aud", "sub", "exp", "iat"]},
    )
    if nonce is not None and not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
        raise ConnectionError("A identidade não pertence a esta tentativa de login.")
    if expected_subject and claims["sub"] != expected_subject:
        raise ConnectionError("A conta retornada difere da conta selecionada.")
    return claims


def record_tokens(tokens, previous=None):
    if (
        not isinstance(tokens.get("access_token"), str)
        or not 20 < len(tokens["access_token"]) < 20000
    ):
        raise ConnectionError("Credencial retornada inválida.")
    scopes = str(tokens.get("scope", "")).split()
    if "chatgpt.tokens.use.direct" not in scopes:
        raise ConnectionError(
            "Esta conta não autorizou uso do plano ChatGPT. Continue com o Rafinha local ou configure sua API pessoal."
        )
    earliest = tokens.get("earliest_refresh_at", 0)
    try:
        earliest = float(earliest)
    except (ValueError, TypeError):
        earliest = datetime.fromisoformat(str(earliest).replace("Z", "+00:00")).timestamp()
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "id_token": tokens.get("id_token") or (previous or {}).get("id_token", ""),
        "earliest_refresh_at": earliest,
        "scopes": scopes,
        "expires_at": time.time() + min(int(tokens.get("expires_in", 3600)), 3600),
    }


async def finish_login(attempt, query):
    if query.get("error"):
        raise ConnectionError("Login não autorizado. O Rafinha local continua disponível.")
    client_id = query.get("client_id") or attempt.get("client_id", "")
    if attempt.get("client_id") and client_id != attempt["client_id"]:
        raise ConnectionError("O registro retornado difere da conta selecionada.")
    if not re.fullmatch(r"oaiapp_[A-Za-z0-9_-]{1,160}", client_id):
        raise ConnectionError("O registro OpenAI não foi concluído.")
    code = query.get("code", "")
    if not code or len(code) > 3000:
        raise ConnectionError("Código de autorização inválido.")
    tokens = await remote(
        "POST",
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "code_verifier": attempt["verifier"],
            "redirect_uri": attempt["redirect_uri"],
            "resource": API,
        },
    )
    claims = await verify_identity(
        tokens.get("id_token", ""), client_id, attempt["nonce"], attempt.get("subject")
    )
    available = await models(tokens["access_token"], "chatgpt")
    previous = vault.load(attempt["user_id"])
    same_account = previous and previous.get("subject") == claims["sub"]
    previous_model = previous.get("model", "") if same_account else ""
    chosen = (
        previous_model
        if previous_model in {m["id"] for m in available}
        else default_model(available)
    )
    value = {
        **record_tokens(tokens),
        "generation": uuid.uuid4().hex,
        "kind": "chatgpt",
        "subject": claims["sub"],
        "client_id": client_id,
        "email": str(claims.get("email", ""))[:254],
        # The sign-in button requests plan use and the official browser consent
        # authorizes it. No second activation or mandatory model picker is needed.
        "enabled": True,
        "model": chosen,
        "daily_limit": previous.get("daily_limit", 20) if same_account else 20,
        "response_timeout": previous.get(
            "response_timeout", 30 if assistant_runtime.chatgpt_mode() else 10
        )
        if same_account
        else 30
        if assistant_runtime.chatgpt_mode()
        else 10,
        "web_enabled": previous.get("web_enabled", False)
        if same_account
        else assistant_runtime.chatgpt_mode(),
        "web_mode": previous.get("web_mode", "automatic") if same_account else "automatic",
        "web_images": previous.get("web_images", True) if same_account else True,
        "priority": "cloud",
        "state": "ready",
        "message": "Tudo pronto. Você já pode conversar com o Rafinha usando seu plano ChatGPT.",
        "models": available,
    }
    # A replaced/cancelled attempt can never install credentials after disconnect.
    with _lock:
        if _attempts.get(attempt["user_id"]) is not attempt or attempt["status"] != "exchanging":
            raise ConnectionError("Esta tentativa foi cancelada.")
        vault.save(attempt["user_id"], value)
        if assistant_runtime.chatgpt_mode():
            assistant_runtime.select_profile(attempt["user_id"])


class LoginStart(BaseModel):
    open_browser: bool = True


@router.post("/chatgpt/start")
def start_login(body: LoginStart, request: Request, user=Depends(current_user)):
    if not local_request(request):
        raise HTTPException(
            403,
            "O login ChatGPT deste projeto está disponível na instalação local. Use sua API pessoal em outros ambientes.",
        )
    owner_id = profile_id(user)
    cancel_attempt(owner_id)
    previous = vault.load(owner_id)
    attempt = {
        "user_id": owner_id,
        "state": secrets.token_urlsafe(32),
        "nonce": secrets.token_urlsafe(32),
        "verifier": secrets.token_urlsafe(48),
        "expires": time.time() + 300,
        "status": "waiting",
        "message": "Aguardando autorização no navegador.",
    }
    if previous and previous["kind"] == "chatgpt":
        attempt.update({"client_id": previous["client_id"], "subject": previous["subject"]})

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log callback URLs containing authorization codes.

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != "/auth/callback":
                self.send_error(404)
                return
            query = {k: v[0] for k, v in parse_qs(parsed.query).items() if len(v) == 1}
            with _lock:
                valid = (
                    _attempts.get(owner_id) is attempt
                    and attempt["status"] == "waiting"
                    and time.time() < attempt["expires"]
                    and secrets.compare_digest(query.get("state", ""), attempt["state"])
                )
                if valid:
                    attempt["status"] = "exchanging"
            if not valid:
                self.send_error(400, "Invalid authorization attempt")
                return
            try:
                asyncio.run(finish_login(attempt, query))
                attempt["status"] = "complete"
                attempt["message"] = (
                    "Tudo pronto! Volte ao Ateliê Verde para conversar com o Rafinha."
                )
            except (
                TimeoutError,
                httpx.HTTPError,
                ValueError,
                ConnectionError,
                jwt.PyJWTError,
                KeyError,
                TypeError,
            ):
                attempt["status"] = "error"
                attempt["message"] = (
                    "Não foi possível concluir o login ou liberar o plano. O Rafinha local continua disponível; tente novamente ou use uma chave pessoal de API."
                )
            text = attempt["message"].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(text)
            attempt["timer"].cancel()
            threading.Thread(target=close_server, args=(self.server,), daemon=True).start()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Callback)
    server.daemon_threads = True
    attempt["server"] = server
    attempt["redirect_uri"] = f"http://127.0.0.1:{server.server_port}/auth/callback"
    with _lock:
        _attempts[owner_id] = attempt
    threading.Thread(target=server.serve_forever, daemon=True).start()
    timer = threading.Timer(
        300,
        lambda: (
            attempt.update(
                {"status": "error", "message": "O login expirou. Você pode tentar novamente."}
            )
            if attempt["status"] == "waiting"
            else None,
            close_server(server),
        ),
    )
    timer.daemon = True
    attempt["timer"] = timer
    timer.start()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(attempt["verifier"].encode()).digest())
        .decode()
        .rstrip("=")
    )
    params = {
        "client_id": attempt.get("client_id", "dynamic_agent_client"),
        "ext_agent_host_id": vault.host_id(),
        "response_type": "code",
        "redirect_uri": attempt["redirect_uri"],
        "scope": SCOPE,
        "resource": API,
        "state": attempt["state"],
        "nonce": attempt["nonce"],
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    if not attempt.get("client_id"):
        params["agent_name_hint"] = "Ateliê Verde"
    url = ISSUER + "/api/accounts/authorize?" + urlencode(params)
    opened = webbrowser.open(url) if body.open_browser else False
    return {"authorization_url": url, "browser_opened": opened}


async def _refresh_unlocked(connection, user_id, timeout):
    if connection["kind"] != "chatgpt" or connection.get("expires_at", 0) > time.time() + 45:
        return connection
    if time.time() < connection.get("earliest_refresh_at", 0):
        if connection.get("expires_at", 0) > time.time():
            return connection
        raise ConnectionError("A renovação ainda não foi liberada para esta conta.")
    tokens = await remote(
        "POST",
        TOKEN_URL,
        timeout=timeout,
        data={
            "grant_type": "refresh_token",
            "client_id": connection["client_id"],
            "refresh_token": connection.get("refresh_token", ""),
            "resource": API,
        },
    )
    updated = record_tokens(tokens, connection)
    if tokens.get("id_token"):
        await verify_identity(
            tokens["id_token"], connection["client_id"], expected_subject=connection["subject"]
        )
    if not vault.update(user_id, connection["generation"], updated):
        raise ConnectionError("A conexão foi removida.")
    return {**connection, **updated}


async def refresh(connection, user_id, timeout):
    # OAuth refresh tokens rotate; serialize renewal across local processes.
    with vault.installation_lock():
        current = vault.load(user_id)
        if (
            not current
            or current.get("generation") != connection.get("generation")
            or not current.get("enabled")
        ):
            raise ConnectionError("A conexão mudou ou foi removida.")
        return await _refresh_unlocked(current, user_id, timeout)
