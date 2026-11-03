import json
import time
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx
import jwt
import pytest
from app import assistant_connections as connections
from app import assistant_credentials as vault
from app import assistant_engine as engine
from app import assistant_provider as local
from app import assistant_runtime as runtime
from app.assistant_request import cloud_permitted
from app.assistant_state import SemanticReply
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(autouse=True)
def isolated_accounts(tmp_path, monkeypatch):
    monkeypatch.setenv("RAFINHA_CREDENTIALS_DIR", str(tmp_path / "private"))
    yield
    connections.close_all()


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )


def connected_api(client, auth, monkeypatch, handler=None, limit=20):
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "gpt-test-mini"}]})
        return handler(request) if handler else httpx.Response(500)

    transport(monkeypatch, respond)
    response = client.post(
        "/api/assistant/connection/api",
        headers=auth["admin"],
        json={"key": "sk-test-unusable-personal-key-000000"},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    configured = client.put(
        "/api/assistant/connection",
        headers=auth["admin"],
        json={"enabled": True, "model": "gpt-test-mini", "daily_limit": limit},
    )
    assert configured.status_code == 200


def message(client, headers, text):
    cid = client.post("/api/assistant/conversations", headers=headers).json()["id"]
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=headers,
        json={"text": text, "request_id": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


def sse(text):
    value = {
        "type": "response.completed",
        "response": {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps({"text": text})}],
                }
            ],
        },
    }
    return httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        content=("data: " + json.dumps(value) + "\n\n").encode(),
    )


def test_vault_is_encrypted_and_owned():
    vault.save(2, {"generation": "a", "api_key": "private-placeholder-0001"})
    assert b"private-placeholder" not in (vault.root() / "account-2.bin").read_bytes()
    assert vault.load(2)["api_key"] == "private-placeholder-0001"
    assert vault.load(3) is None
    assert not vault.update(2, "other-generation", {"enabled": True})
    vault.remove(2)
    assert vault.load(2) is None


def test_legacy_connection_is_admin_only_and_never_returns_credentials(client, auth, monkeypatch):
    connected_api(client, auth, monkeypatch)
    own = client.get("/api/assistant/connection", headers=auth["admin"])
    assert own.json()["connected"]
    assert "sk-test" not in own.text and "api_key" not in own.json()
    for who in ["one", "two"]:
        assert client.get("/api/assistant/connection", headers=auth[who]).status_code == 403
        assert (
            client.put(
                "/api/assistant/connection", headers=auth[who], json={"enabled": True}
            ).status_code
            == 403
        )
        assert client.delete("/api/assistant/connection", headers=auth[who]).status_code == 403
        assert (
            client.post(
                "/api/assistant/connection/api",
                headers=auth[who],
                json={"key": "sk-test-unusable-personal-key-000000"},
            ).status_code
            == 403
        )
    assert client.get("/api/assistant/connection").status_code == 401


def test_limit_saves_independently_without_resetting_model_or_activation(client, auth, monkeypatch):
    connected_api(client, auth, monkeypatch)
    updated = client.put(
        "/api/assistant/connection", headers=auth["admin"], json={"daily_limit": 47}
    )
    assert updated.status_code == 200
    assert updated.json()["daily_limit"] == 47 and updated.json()["enabled"]
    assert updated.json()["model"] == "gpt-test-mini"
    assert (
        client.get("/api/assistant/connection", headers=auth["admin"]).json()["daily_limit"] == 47
    )
    paused = client.put("/api/assistant/connection", headers=auth["admin"], json={"enabled": False})
    assert paused.json()["daily_limit"] == 47 and paused.json()["model"] == "gpt-test-mini"
    assert (
        client.put(
            "/api/assistant/connection", headers=auth["admin"], json={"daily_limit": 101}
        ).status_code
        == 422
    )
    assert vault.load(1)["daily_limit"] == 47
    value = vault.load(1)
    vault.update(1, value["generation"], {"state": "reconnect", "message": "Entre novamente"})
    limited = client.put(
        "/api/assistant/connection", headers=auth["admin"], json={"daily_limit": 51}
    )
    assert limited.json()["daily_limit"] == 51 and limited.json()["state"] == "reconnect"
    assert limited.json()["message"] == "Entre novamente"


def test_internal_data_never_call_optional_cloud(client, auth, monkeypatch):
    seen = []
    connected_api(client, auth, monkeypatch, lambda req: seen.append(req) or sse("Unexpected"))
    monkeypatch.setattr(engine, "research", lambda *args: pytest.fail("Internal query"))
    for text in [
        "Olá",
        "Quem é você?",
        "Vocês fazem poda?",
        "Quanto custa a Lavanda?",
        "Mostre meus clientes",
        "Qual meu próximo serviço?",
    ]:
        result = message(client, auth["one"], text)
        assert result["mode"] == "catalog" and not result["meta"]["research"]["needed"]
    assert not seen


def test_timeout_preference_persists_without_resetting_other_connection_fields(
    client, auth, monkeypatch
):
    connected_api(client, auth, monkeypatch, limit=47)
    assert connections.public_status(1)["response_timeout"] == 10
    value = vault.load(1)
    vault.update(1, value["generation"], {"cooldown_until": time.time() + 60, "message": "Timeout"})
    updated = client.put(
        "/api/assistant/connection", headers=auth["admin"], json={"response_timeout": 30}
    )
    assert updated.status_code == 200 and updated.json()["response_timeout"] == 30
    saved = client.get("/api/assistant/connection", headers=auth["admin"]).json()
    assert saved["enabled"] and saved["model"] == "gpt-test-mini" and saved["daily_limit"] == 47
    assert saved["response_timeout"] == 30 and saved["message"] == ""
    assert connections.ready(1)
    assert (
        client.put(
            "/api/assistant/connection", headers=auth["admin"], json={"response_timeout": 60}
        ).status_code
        == 422
    )


def test_installation_timeout_reaches_local_model_and_ignores_legacy_preference(
    client, auth, monkeypatch
):
    connected_api(client, auth, monkeypatch)
    client.put("/api/assistant/connection", headers=auth["admin"], json={"response_timeout": 10})
    seen = []

    def model(question, facts, history):
        seen.append(facts["_budget"].remaining())
        return SemanticReply(text="Vamos conferir a umidade e a drenagem antes de regar novamente.")

    monkeypatch.setattr(engine, "generate_ai", model)
    # Excessive watering now uses verified internal guidance. Check the model
    # budget with a turn that still requires local conversational inference.
    message(client, auth["one"], "Minha Lavanda está murchando")
    assert len(seen) == 1 and 25 < seen[0] <= 27
    assert not vault.usage(1).get("calls")


def test_local_first_does_not_spend_a_cloud_request(client, auth, monkeypatch):
    seen = []
    connected_api(client, auth, monkeypatch, lambda req: seen.append(req) or sse("Cloud"))
    monkeypatch.setattr(
        local, "answer", lambda *args: SemanticReply(text="Resposta local contextual.")
    )
    result = message(client, auth["one"], "Minha Lavanda está murchando")
    assert result["mode"] == "local" and not seen


def test_local_failure_never_activates_a_legacy_paid_connection(client, auth, monkeypatch):
    calls = []
    connected_api(client, auth, monkeypatch, lambda req: calls.append(req) or sse("Cloud"))
    monkeypatch.setattr(local, "answer", lambda *args: None)
    for who in ["one", "admin"]:
        result = message(client, auth[who], "Minha Lavanda está murchando")
        assert result["mode"] == "catalog"
    assert not calls and not vault.usage(1).get("calls")


def test_legacy_cloud_priority_does_not_override_contextual_local_conversation(
    client, auth, monkeypatch
):
    calls = []
    connected_api(client, auth, monkeypatch, lambda req: calls.append(req) or sse("Legacy cloud"))
    value = vault.load(1)
    vault.update(1, value["generation"], {"priority": "cloud"})
    received = []

    def answer(question, facts, history):
        received.append(facts["records"]["session"])
        return SemanticReply(
            text="Sua rosa vermelha está em vaso no apartamento. Vamos entender a luz que ela recebe."
        )

    monkeypatch.setattr(local, "answer", answer)
    result = message(
        client, auth["one"], "se trata de rosa vermelha, plantada em vaso e fica no meu apartamento"
    )
    assert result["mode"] == "local" and not calls
    assert received[0]["slots"]["environment"] == "interno"


def test_legacy_cloud_failure_is_not_contacted_before_local_answer(client, auth, monkeypatch):
    calls = []
    connected_api(client, auth, monkeypatch, lambda req: calls.append(req) or httpx.Response(503))
    value = vault.load(1)
    vault.update(1, value["generation"], {"priority": "cloud"})
    monkeypatch.setattr(
        local, "answer", lambda *args: SemanticReply(text="Vamos observar a planta juntos.")
    )
    result = message(client, auth["one"], "Como cuidar da Lavanda?")
    assert result["mode"] == "local" and not calls


def allow_plan_transport():
    value = vault.load(1)
    value.pop("api_key", None)
    value.update(
        {
            "kind": "chatgpt",
            "access_token": "synthetic-chatgpt-access-not-real",
            "scopes": ["chatgpt.tokens.use.direct"],
            "expires_at": time.time() + 3600,
        }
    )
    vault.save(1, value)
    runtime.select_profile(1)
    return cloud_permitted.set(True)


def test_chatgpt_transport_native_text_without_json_is_preserved(monkeypatch):
    from app import assistant_openai as cloud
    from app.assistant_budget import Budget

    text = "Claro 🌹 Você quer ajuda com cuidados gerais, poda ou algum problema da roseira?"
    vault.save(
        1,
        {
            "generation": "isolated",
            "kind": "api",
            "enabled": True,
            "state": "ready",
            "model": "gpt-test",
            "api_key": "sk-test-not-real-000000000",
        },
    )

    def response(request):
        body = json.loads(request.content)
        assert body["store"] is False and body["stream"] is True
        assert "max_output_tokens" not in body
        assert not any(item["role"] == "system" for item in body["input"])
        event = {
            "type": "response.completed",
            "response": {
                "status": "completed",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
            },
        }
        return httpx.Response(200, content=("data: " + json.dumps(event) + "\n\n").encode())

    transport(monkeypatch, response)
    gate = allow_plan_transport()
    try:
        result = cloud.generate(
            "Tenho uma roseira",
            {
                "_allow_cloud": True,
                "_owner_id": 1,
                "_budget": Budget(2),
                "products": [],
                "services": [],
            },
            [],
            "Converse com o cliente.",
        )
    finally:
        cloud_permitted.reset(gate)
    assert result.text == text and result._provider == "chatgpt"


def test_default_model_uses_an_authorized_workhorse():
    assert (
        connections.default_model([{"id": "gpt-6-astra"}, {"id": "gpt-5.6-sol"}]) == "gpt-5.6-sol"
    )
    assert connections.default_model([{"id": "gpt-test"}]) == "gpt-test"


def test_registered_products_and_services_use_local_facts_without_legacy_chatgpt(
    client, auth, monkeypatch
):
    calls, received = [], []
    connected_api(client, auth, monkeypatch, lambda req: calls.append(req) or sse("Legacy"))
    value = vault.load(1)
    vault.update(
        1,
        value["generation"],
        {
            "kind": "chatgpt",
            "access_token": "test-not-real-access",
            "expires_at": time.time() + 3600,
            "priority": "cloud",
        },
    )

    def answer(question, facts, history):
        received.append(facts["records"])
        return SemanticReply(
            text="A Lavanda custa R$ 24,90."
            if "custa" in question
            else "Sim, temos Poda cadastrada."
        )

    monkeypatch.setattr(local, "answer", answer)
    for question in ["Quanto custa a Lavanda?", "Vocês fazem poda?"]:
        assert message(client, auth["one"], question)["mode"] == "local"
    assert "R$ 24,90" in str(received[0]) and "Poda" in str(received[1])
    denied = message(client, auth["one"], "Mostre meus clientes")
    assert denied["mode"] == "catalog" and len(received) == 2 and not calls


def test_chatgpt_completed_stream_keeps_text_delivered_in_deltas(monkeypatch):
    from app import assistant_openai as cloud
    from app.assistant_budget import Budget

    text = "Claro! Em que você quer ajuda com sua roseira?"
    vault.save(
        1,
        {
            "generation": "isolated",
            "kind": "api",
            "enabled": True,
            "state": "ready",
            "model": "gpt-test",
            "api_key": "sk-test-not-real-000000000",
        },
    )
    events = [
        {"type": "response.output_text.delta", "delta": text},
        {"type": "response.completed", "response": {"status": "completed", "output": []}},
    ]
    transport(
        monkeypatch,
        lambda request: httpx.Response(
            200, content="".join("data: " + json.dumps(event) + "\n\n" for event in events).encode()
        ),
    )
    gate = allow_plan_transport()
    try:
        result = cloud.generate(
            "Tenho uma roseira",
            {
                "_allow_cloud": True,
                "_owner_id": 1,
                "_budget": Budget(2),
                "products": [],
                "services": [],
            },
            [],
            "Converse com o cliente.",
        )
    finally:
        cloud_permitted.reset(gate)
    assert result.text == text


def test_legacy_disconnect_and_reconnect_do_not_reset_stored_usage(client, auth, monkeypatch):
    from app.assistant_openai import consume

    connected_api(client, auth, monkeypatch, limit=1)
    assert consume(1, vault.load(1))
    assert not consume(1, vault.load(1))
    assert vault.usage(1)["calls"] == 1
    client.delete("/api/assistant/connection", headers=auth["admin"])
    response = client.post(
        "/api/assistant/connection/api",
        headers=auth["admin"],
        json={"key": "sk-test-unusable-personal-key-000000"},
    )
    assert response.status_code == 200
    client.put(
        "/api/assistant/connection",
        headers=auth["admin"],
        json={"enabled": True, "model": "gpt-test-mini", "daily_limit": 1},
    )
    assert not connections.ready(1) and vault.usage(1)["calls"] == 1
    assert message(client, auth["one"], "Minha Lavanda está murchando")["mode"] == "catalog"


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_legacy_external_errors_cannot_trigger_any_paid_account(client, auth, monkeypatch, status):
    calls = []
    connected_api(
        client, auth, monkeypatch, lambda req: calls.append(req) or httpx.Response(status)
    )
    monkeypatch.setattr(local, "answer", lambda *args: None)
    result = message(client, auth["one"], "Minha Lavanda está murchando")
    assert result["mode"] == "catalog" and not calls
    assert "sk-test" not in result["text"] and not vault.usage(1).get("calls")


def test_remote_origin_never_uses_personal_cloud(client, auth, monkeypatch):
    seen = []
    connected_api(client, auth, monkeypatch, lambda req: seen.append(req) or sse("Cloud"))
    monkeypatch.setattr(local, "answer", lambda *args: None)
    cid = client.post("/api/assistant/conversations", headers=auth["admin"]).json()["id"]
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers={**auth["admin"], "Origin": "http://192.0.2.44:5173"},
        json={"text": "Minha Lavanda está murchando", "request_id": str(uuid4())},
    )
    assert response.status_code == 200 and response.json()["mode"] == "catalog" and not seen


def test_legacy_chatgpt_or_api_tokens_are_inert_in_current_chat_pipeline(client, auth, monkeypatch):
    vault.save(
        1,
        {
            "generation": "chat-account",
            "kind": "chatgpt",
            "enabled": True,
            "model": "gpt-test",
            "state": "ready",
            "expires_at": time.time() + 3600,
            "access_token": "test-chatgpt-access-token-000000000",
            "api_key": "sk-unused-paid-key-placeholder",
            "daily_limit": 20,
        },
    )
    used = []
    transport(monkeypatch, lambda request: used.append(request) or httpx.Response(429))
    monkeypatch.setattr(local, "answer", lambda *args: None)
    for who in ["one", "admin"]:
        result = message(client, auth[who], "Minha Lavanda está murchando")
        assert result["mode"] == "catalog"
    assert not used and not vault.usage(1).get("calls")


def test_legacy_transport_partial_stream_is_not_a_completed_answer(monkeypatch):
    from app import assistant_openai as cloud
    from app.assistant_budget import Budget

    vault.save(
        1,
        {
            "generation": "isolated",
            "kind": "api",
            "enabled": True,
            "state": "ready",
            "model": "gpt-test",
            "api_key": "sk-test-not-real-000000000",
        },
    )
    transport(
        monkeypatch,
        lambda request: httpx.Response(
            200, content=b'data: {"type":"response.output_text.delta","delta":"Unfinished"}\n\n'
        ),
    )
    assert (
        cloud.generate(
            "Tenho uma roseira",
            {"_owner_id": 1, "_budget": Budget(2), "products": [], "services": []},
            [],
            "Converse com o cliente.",
        )
        is None
    )


def test_oauth_pkce_state_identity_and_scope(client, auth, monkeypatch):
    monkeypatch.setattr(connections, "local_request", lambda request: True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    public_key["kid"] = "test-key"

    def remote(request):
        if request.url.path.endswith("jwks.json"):
            return httpx.Response(200, json={"keys": [public_key]})
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"slug": "gpt-test", "display_name": "Test model", "visibility": "list"}
                    ]
                },
            )
        body = parse_qs(request.content.decode())
        attempt = connections._attempts[1]
        assert body["code_verifier"] == [attempt["verifier"]]
        assert body["resource"] == [connections.API]
        token = jwt.encode(
            {
                "iss": connections.ISSUER,
                "aud": "oaiapp_test",
                "sub": "verified-owner",
                "nonce": attempt["nonce"],
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "email": "person@example.test",
            },
            key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )
        return httpx.Response(
            200,
            json={
                "access_token": "test-access-token-with-enough-length",
                "refresh_token": "test-refresh",
                "id_token": token,
                "expires_in": 3600,
                "scope": connections.SCOPE,
            },
        )

    transport(monkeypatch, remote)
    started = client.post(
        "/api/assistant/connection/chatgpt/start",
        headers=auth["admin"],
        json={"open_browser": False},
    )
    assert started.status_code == 200
    query = parse_qs(urlparse(started.json()["authorization_url"]).query)
    assert query["client_id"] == ["dynamic_agent_client"] and query["code_challenge_method"] == [
        "S256"
    ]
    assert "verifier" not in started.text
    callback = query["redirect_uri"][0]
    invalid = httpx.get(
        callback, params={"state": "wrong", "code": "test-code", "client_id": "oaiapp_test"}
    )
    assert invalid.status_code == 400 and vault.load(1) is None
    valid = httpx.get(
        callback,
        params={"state": query["state"][0], "code": "test-code", "client_id": "oaiapp_test"},
        timeout=10,
    )
    assert valid.status_code == 200
    stored = vault.load(1)
    assert stored["subject"] == "verified-owner" and stored["enabled"]
    assert stored["model"] == "gpt-test" and stored["priority"] == "cloud"
    assert "test-access" not in client.get("/api/assistant/connection", headers=auth["admin"]).text
    client.put(
        "/api/assistant/connection",
        headers=auth["admin"],
        json={"daily_limit": 39, "response_timeout": 30},
    )
    again = client.post(
        "/api/assistant/connection/chatgpt/start",
        headers=auth["admin"],
        json={"open_browser": False},
    )
    next_query = parse_qs(urlparse(again.json()["authorization_url"]).query)
    assert next_query["client_id"] == ["oaiapp_test"]
    returned = httpx.get(
        next_query["redirect_uri"][0],
        params={"state": next_query["state"][0], "code": "new-code"},
        timeout=10,
    )
    assert returned.status_code == 200 and vault.load(1)["daily_limit"] == 39
    assert vault.load(1)["response_timeout"] == 30


def test_declined_chatgpt_consent_keeps_free_mode(client, auth, monkeypatch):
    monkeypatch.setattr(connections, "local_request", lambda request: True)
    started = client.post(
        "/api/assistant/connection/chatgpt/start",
        headers=auth["admin"],
        json={"open_browser": False},
    )
    query = parse_qs(urlparse(started.json()["authorization_url"]).query)
    response = httpx.get(
        query["redirect_uri"][0], params={"state": query["state"][0], "error": "access_denied"}
    )
    assert response.status_code == 200 and vault.load(1) is None
    assert connections.public_status(1)["login_state"] == "error"
