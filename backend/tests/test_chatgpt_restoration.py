"""ChatGPT-only conversations and the credential boundary of a public install."""

import asyncio
import base64
import io
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from app import assistant_credentials as vault
from app import assistant_engine as engine
from app import assistant_provider as local
from app import assistant_runtime as runtime
from app import assistant_stream
from PIL import Image

HTTP_CLIENT = httpx.AsyncClient


def credential(uid=1, **updates):
    return {
        "generation": "synthetic-generation",
        "kind": "chatgpt",
        "enabled": True,
        "state": "ready",
        "model": "gpt-5.6-sol",
        "models": [{"id": "gpt-5.6-sol", "name": "ChatGPT"}],
        "access_token": "synthetic-access-credential-not-real",
        "scopes": ["chatgpt.tokens.use.direct"],
        "expires_at": time.time() + 3600,
        "daily_limit": 47,
        "response_timeout": 30,
        "web_enabled": False,
        **updates,
    }


@pytest.fixture
def chatgpt(tmp_path, monkeypatch):
    monkeypatch.setenv("RAFINHA_MODE", "chatgpt")
    monkeypatch.setenv("RAFINHA_CREDENTIALS_DIR", str(tmp_path / "own-account"))
    vault.save(1, credential())
    runtime.select_profile(1)
    calls = []
    original = httpx.AsyncClient

    def respond(request):
        assert request.url.host == "api.openai.com" and request.url.path == "/v1/responses"
        body = json.loads(request.content)
        calls.append(body)
        text = "Claro 🌿 Vamos considerar a planta que você contou e os cuidados que deseja. Confira as condições atuais antes de decidir a rega."
        event = {
            "type": "response.completed",
            "response": {
                "status": "completed",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
            },
        }
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=("data: " + json.dumps(event) + "\n\n").encode(),
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs),
    )
    monkeypatch.setattr(local, "answer", lambda *args: pytest.fail("Ollama cannot replace ChatGPT"))
    monkeypatch.setattr(
        engine,
        "research_reply",
        lambda *args: pytest.fail("Tavily/paid APIs are outside this mode"),
    )
    return calls


def start(client, auth):
    return client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]


def ask(client, auth, text, cid=None, **headers):
    response = client.post(
        f"/api/assistant/conversations/{cid or start(client, auth)}/messages",
        headers={**auth["one"], **headers},
        json={"text": text, "request_id": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


def photo(client, auth, cid, format="PNG", size=(2560, 1600)):
    data = io.BytesIO()
    Image.new("RGB", size, "green").save(data, format=format)
    response = client.post(
        f"/api/assistant/conversations/{cid}/attachments",
        headers=auth["one"],
        files={"file": ("plant." + format.lower(), data.getvalue(), "image/" + format.lower())},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_photo_pixels_reach_chatgpt_and_remain_available_for_followups(client, auth, chatgpt):
    cid = start(client, auth)
    attachment = photo(client, auth, cid)
    reply = ask(client, auth, "Analise a imagem da minha planta", cid)
    current = chatgpt[-1]["input"][-1]["content"]
    assert current[0] == {"type": "input_text", "text": "Analise a imagem da minha planta"}
    assert current[1]["type"] == "input_image" and current[1]["detail"] == "high"
    assert current[1]["image_url"].startswith("data:image/jpeg;base64,")
    raw = base64.b64decode(current[1]["image_url"].split(",", 1)[1])
    with Image.open(io.BytesIO(raw)) as image:
        assert image.size == (2048, 1280) and not image.getexif()
        assert image.getpixel((400, 400))[1] >= 125
    assert reply["meta"]["image_analysis"] == {"submitted": 1, "performed": True}
    assert "data:image" not in json.dumps(reply)
    stored = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()
    assert "data:image" not in json.dumps(stored)
    ask(client, auth, "E como cuidar dela?", cid)
    assert len(chatgpt[-1]["input"][-1]["content"]) == 2
    assert sum("input_image" in json.dumps(row) for row in chatgpt[-1]["input"]) == 1
    assert client.get(attachment["url"], headers=auth["two"]).status_code == 404
    assert (
        client.delete(f"/api/assistant/conversations/{cid}", headers=auth["one"]).status_code == 204
    )
    assert client.get(attachment["url"], headers=auth["one"]).status_code == 404


def test_photos_cannot_be_forwarded_from_another_users_conversation(client, auth, chatgpt):
    cid = start(client, auth)
    photo(client, auth, cid)
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=auth["two"],
        json={"text": "Veja a foto", "request_id": str(uuid4())},
    )
    assert response.status_code == 404 and not chatgpt
    other = client.post("/api/assistant/conversations", headers=auth["two"]).json()["id"]
    response = client.post(
        f"/api/assistant/conversations/{other}/messages",
        headers=auth["two"],
        json={"text": "Tenho uma roseira", "request_id": str(uuid4())},
    )
    assert response.status_code == 200 and len(chatgpt) == 1
    assert "input_image" not in json.dumps(chatgpt[0])


def test_no_connection_does_not_claim_it_analyzed_a_photo(client, auth, chatgpt):
    runtime.unselect(1)
    cid = start(client, auth)
    photo(client, auth, cid)
    reply = ask(client, auth, "Analise a imagem da minha planta", cid)
    assert reply["mode"] == "catalog" and not chatgpt
    assert reply["meta"]["image_analysis"]["performed"] is False
    assert "conexão ChatGPT ativa" in reply["text"]


def test_webp_is_supported_but_animated_images_are_rejected(client, auth, chatgpt):
    cid = start(client, auth)
    photo(client, auth, cid, format="WEBP", size=(64, 48))
    data = io.BytesIO()
    Image.new("RGB", (24, 24), "red").save(
        data, format="GIF", save_all=True, append_images=[Image.new("RGB", (24, 24), "green")]
    )
    response = client.post(
        f"/api/assistant/conversations/{cid}/attachments",
        headers=auth["one"],
        files={"file": ("moving.gif", data.getvalue(), "image/gif")},
    )
    assert response.status_code == 422
    reply = ask(client, auth, "Veja a foto", cid)
    assert reply["meta"]["image_analysis"]["submitted"] == 1


@pytest.mark.parametrize(
    "text",
    [
        "Olá",
        "Tenho uma roseira",
        "Eu reguei muito a planta",
        "Tenho uma suculenta, parece a orelha do Shrek",
        "Quero cuidados gerais",
    ],
)
def test_chatgpt_handles_dialogue_instead_of_local_templates(client, auth, chatgpt, text):
    reply = ask(client, auth, text)
    assert reply["mode"] == "chatgpt" and len(chatgpt) == 1
    assert chatgpt[0]["store"] is False and chatgpt[0]["stream"] is True
    assert chatgpt[0]["model"] == "gpt-5.6-sol" and "tools" not in chatgpt[0]
    assert vault.usage(1)["calls"] == 1 and not vault.usage(2).get("calls")


@pytest.mark.parametrize(
    "text",
    [
        "Boa noite, dormiu bem?",
        "Hoje meu dia foi corrido, estou cansado.",
        "Pode corrigir esta frase: eu foi na loja ontem?",
        "Por que o céu é azul?",
        "Quem é você?",
        "Qual o preço da Lavanda?",
    ],
)
def test_social_general_identity_and_public_shop_dialogue_reach_chatgpt(
    client, auth, chatgpt, text
):
    reply = ask(client, auth, text)
    assert reply["mode"] == "chatgpt" and len(chatgpt) == 1
    assert chatgpt[0]["input"][-1]["content"] == text
    assert "não dorme" in chatgpt[0]["instructions"]
    assert "não uma obrigação de mudar qualquer conversa para plantas" in chatgpt[0]["instructions"]


def test_real_ai_failure_never_starts_an_offline_plant_questionnaire(
    client, auth, chatgpt, monkeypatch
):
    event = {"type": "response.failed", "response": {"error": {"code": "server_is_overloaded"}}}
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: HTTP_CLIENT(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=sse(event))),
            **kwargs,
        ),
    )
    cid = start(client, auth)
    reply = ask(client, auth, "Boa noite, dormiu bem?", cid)
    assert reply["mode"] == "catalog" and reply["meta"]["chatgpt_failed"]
    assert "ChatGPT não conseguiu" in reply["text"] and "nome da planta" not in reply["text"]
    detail = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()
    assert detail["memory"]["pending_field"] is None


def test_nickname_identification_requests_images_and_retains_a_hypothesis(
    client, auth, chatgpt, monkeypatch
):
    vault.update(1, vault.load(1)["generation"], {"web_enabled": True, "web_images": True})
    source = {
        "title": "NC State Extension",
        "url": "https://plants.ces.ncsu.edu/plants/crassula-ovata/",
    }
    item = {
        "type": "web_search_call",
        "status": "completed",
        "action": {"sources": [source]},
        "results": [
            {
                "type": "image_result",
                "image_url": "https://images.example.test/gollum.jpg",
                "source_website_url": source["url"],
                "caption": None,
            },
        ],
    }
    bodies = []

    def respond(request):
        body = json.loads(request.content)
        bodies.append(body)
        if "tools" not in body:
            return httpx.Response(
                200, content=sse(completed("Confira a umidade antes de regar novamente."))
            )
        event = completed(
            "Pela descrição, uma hipótese é *Crassula ovata 'Gollum'*. Compare as folhas tubulares com as referências; ainda não é uma confirmação."
        )
        event["response"]["output"].insert(0, item)
        return httpx.Response(200, content=sse(event))

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: HTTP_CLIENT(transport=httpx.MockTransport(respond), **kwargs),
    )
    cid = start(client, auth)
    reply = ask(client, auth, "Eu só sei que é uma suculenta, parece com a orelha do Shrek", cid)
    assert reply["mode"] == "chatgpt" and reply["meta"]["searched_web"]
    assert len(reply["images"]) == 1 and reply["images"][0]["source_url"] == source["url"]
    assert reply["images"][0]["caption"] == "Referência da pesquisa"
    assert bodies[0]["tools"][0]["search_content_types"] == ["text", "image"]
    assert "web_search_call.results" in bodies[0]["include"] and "max_tool_calls" not in bodies[0]
    followup = ask(client, auth, "Não deixei no sol e reguei muito", cid)
    assert "tools" not in bodies[-1] and followup["expression"] in {"concerned", "serious"}
    detail = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()
    assert detail["memory"]["identity_hypothesis"]["status"] == "hypothesis"
    assert not detail["memory"]["species_id"]


def test_history_and_authorized_current_context_reach_the_same_account(client, auth, chatgpt):
    cid = start(client, auth)
    ask(client, auth, "Tenho uma roseira", cid)
    ask(client, auth, "Ela fica dentro de casa em vaso", cid)
    body = chatgpt[-1]
    assert any(row["content"] == "Tenho uma roseira" for row in body["input"])
    assert "roseira" in body["instructions"] and "interno" in body["instructions"]
    assert "synthetic-access" not in json.dumps(body)


def test_recent_history_does_not_cut_off_the_clients_reported_conditions(client, auth, chatgpt):
    cid = start(client, auth)
    text = (
        "Tenho uma roseira. "
        + "Estou observando as folhas. " * 45
        + "O substrato continua encharcado."
    )
    assert len(text) > 1000
    ask(client, auth, text, cid)
    ask(client, auth, "E devo regar novamente?", cid)
    assert any(row["content"] == text for row in chatgpt[-1]["input"])


@pytest.mark.parametrize(
    "text",
    [
        "Minha roseira está murchando, esqueci de regar por uma semana. O que faço?",
        "Minha orquídea está murcha porque esqueci de regar. O que posso fazer?",
        "Tenho uma suculenta que parece a orelha do Shrek. Qual pode ser e como cuidar?",
    ],
)
def test_routine_care_and_available_identification_references_do_not_delay_the_chat(
    client, auth, chatgpt, text
):
    value = vault.load(1)
    vault.update(1, value["generation"], {"web_enabled": True, "web_images": False})
    reply = ask(client, auth, text)
    assert reply["mode"] == "chatgpt" and len(chatgpt) == 1
    assert "tools" not in chatgpt[0]
    if "Shrek" in text:
        assert (
            "Crassula" in chatgpt[0]["instructions"] and "hypothesis" in chatgpt[0]["instructions"]
        )


@pytest.mark.parametrize(
    "followup",
    [
        "Esqueci de regar durante uma semana e agora ela está murchando.",
        "Quero cuidar de outra planta, tenho uma Lavanda",
    ],
)
def test_chatgpt_keeps_history_when_reported_conditions_or_subject_change(
    client, auth, chatgpt, followup
):
    cid = start(client, auth)
    ask(client, auth, "Tenho uma roseira", cid)
    ask(client, auth, followup, cid)
    assert any(row["content"] == "Tenho uma roseira" for row in chatgpt[-1]["input"])
    if "murchando" in followup:
        memory = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()[
            "memory"
        ]
        assert memory["plant_name"] == "roseira"


def test_developer_like_profile_is_inert_until_explicitly_selected(client, auth, chatgpt):
    runtime.unselect(1)
    vault.save(2, credential())
    reply = ask(client, auth, "Tenho uma roseira")
    assert reply["mode"] == "catalog" and not chatgpt
    assert client.get("/api/assistant/status", headers=auth["one"]).json()["mode"] == "catalog"


@pytest.mark.parametrize("updates", [{"kind": "api"}, {"scopes": []}])
def test_paid_api_or_identity_only_token_cannot_be_selected(client, auth, chatgpt, updates):
    runtime.unselect(1)
    vault.save(1, credential(**updates))
    with pytest.raises(ValueError):
        runtime.select_profile(1)
    assert ask(client, auth, "Tenho uma roseira")["mode"] == "catalog" and not chatgpt


def test_disconnect_and_generation_change_block_old_credentials(client, auth, chatgpt):
    vault.save(1, credential(generation="replacement"))
    assert ask(client, auth, "Tenho uma roseira")["mode"] == "catalog" and not chatgpt
    runtime.select_profile(1)
    assert client.delete("/api/assistant/connection", headers=auth["admin"]).status_code == 204
    assert runtime.connection() is None
    assert ask(client, auth, "Tenho uma roseira")["mode"] == "catalog" and not chatgpt


def test_external_origin_cannot_consume_the_local_account(client, auth, chatgpt):
    assert (
        ask(client, auth, "Tenho uma roseira", Origin="https://external.example")["mode"]
        == "catalog"
    )
    assert not chatgpt and not vault.usage(1).get("calls")


def test_quota_is_preserved_without_switching_to_other_providers(client, auth, chatgpt):
    value = vault.load(1)
    vault.update(1, value["generation"], {"daily_limit": 1})
    ask(client, auth, "Tenho uma roseira")
    assert ask(client, auth, "Quero cuidados gerais")["mode"] == "catalog"
    assert len(chatgpt) == 1 and vault.usage(1)["calls"] == 1


def test_admin_preferences_manage_the_selected_local_profile_and_keep_limits(client, auth, chatgpt):
    vault.save(2, credential())
    runtime.select_profile(2)
    response = client.put(
        "/api/assistant/connection", headers=auth["admin"], json={"daily_limit": 51}
    )
    assert response.status_code == 200 and response.json()["daily_limit"] == 51
    assert vault.load(2)["model"] == "gpt-5.6-sol" and vault.load(2)["enabled"]
    assert client.get("/api/assistant/connection", headers=auth["one"]).status_code == 403


@pytest.mark.parametrize(
    "error_code,expected_calls",
    [("server_error", 2), ("subscription_sharing_usage_limit_exceeded", 1)],
)
def test_web_failure_only_retries_the_same_account_when_allowed(
    client, auth, chatgpt, monkeypatch, error_code, expected_calls
):
    value = vault.load(1)
    vault.update(1, value["generation"], {"web_enabled": True})
    bodies = []

    def respond(request):
        body = json.loads(request.content)
        bodies.append(body)
        assert request.url.host == "api.openai.com"
        if "tools" in body:
            event = {"type": "response.failed", "response": {"error": {"code": error_code}}}
        else:
            assert '"unavailable": true' in body["instructions"]
            event = {
                "type": "response.completed",
                "response": {
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "Não consegui conferir fontes agora, mas podemos continuar com os cuidados gerais da roseira.",
                                }
                            ],
                        }
                    ],
                },
            }
        return httpx.Response(200, content=("data: " + json.dumps(event) + "\n\n").encode())

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: HTTP_CLIENT(transport=httpx.MockTransport(respond), **kwargs),
    )
    answer = ask(client, auth, "Pesquise como cuidar da minha roseira")
    assert len(bodies) == expected_calls and vault.usage(1)["calls"] == expected_calls
    assert answer["mode"] == ("chatgpt" if expected_calls == 2 else "catalog")


def sse(event):
    return ("data: " + json.dumps(event) + "\n\n").encode()


def completed(text):
    return {
        "type": "response.completed",
        "response": {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        },
    }


def test_completion_does_not_wait_for_the_stream_to_close(client, auth, chatgpt, monkeypatch):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield sse(completed("Claro, vamos considerar a sua roseira e a luz do local."))
            pytest.fail("A finished response must not await the next SSE event")

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: HTTP_CLIENT(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Stream())),
            **kwargs,
        ),
    )
    reply = ask(client, auth, "Tenho uma roseira")
    assert reply["mode"] == "chatgpt" and "roseira" in reply["text"]


@pytest.mark.parametrize("finish", ["complete", "cancel", "delete", "fail"])
def test_live_preview_is_private_ephemeral_and_keeps_the_concerned_expression(
    client, auth, chatgpt, monkeypatch, finish
):
    cid = start(client, auth)
    req = str(uuid4())
    entered, release = threading.Event(), threading.Event()
    text = "Vamos olhar a sua roseira com atenção. Confira se a terra está seca antes de regar."

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield sse({"type": "response.reasoning_text.delta", "delta": "Internal reasoning"})
            yield sse({"type": "response.output_text.delta", "delta": text})
            entered.set()
            assert await asyncio.to_thread(release.wait, 8)
            yield sse(
                completed(text)
                if finish != "fail"
                else {"type": "response.failed", "response": {"error": {"code": "server_error"}}}
            )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: HTTP_CLIENT(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Stream())),
            **kwargs,
        ),
    )
    with ThreadPoolExecutor() as executor:
        future = executor.submit(
            client.post,
            f"/api/assistant/conversations/{cid}/messages",
            headers=auth["one"],
            json={"text": "Minha roseira está murchando, esqueci de regar", "request_id": req},
        )
        try:
            assert entered.wait(8)
            progress = client.get(
                f"/api/assistant/conversations/{cid}/progress", headers=auth["one"]
            )
            assert progress.json() == {
                "request_id": req,
                "phase": "writing",
                "text": text,
                "expression": "concerned",
            }
            assert "Internal reasoning" not in json.dumps(progress.json())
            assert (
                client.get(
                    f"/api/assistant/conversations/{cid}/progress", headers=auth["two"]
                ).status_code
                == 404
            )
            remote = client.get(
                f"/api/assistant/conversations/{cid}/progress",
                headers={**auth["one"], "Origin": "https://external.example"},
            ).json()
            assert "text" not in remote
            detail = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()
            assert detail["messages"][-1]["text"] == ""
            if finish == "cancel":
                assert client.post(
                    f"/api/assistant/conversations/{cid}/messages/{req}/cancel", headers=auth["one"]
                ).json()["cancelled"]
            elif finish == "delete":
                assert (
                    client.delete(
                        f"/api/assistant/conversations/{cid}", headers=auth["one"]
                    ).status_code
                    == 204
                )
        finally:
            release.set()
        response = future.result(timeout=8)
    assert not assistant_stream.snapshot(1, cid, req)
    if finish in {"cancel", "delete"}:
        assert response.status_code == 409
    else:
        assert response.status_code == 200
        assert response.json()["mode"] == ("chatgpt" if finish == "complete" else "catalog")
        if finish == "complete":
            assert response.json()["text"] == text and response.json()["expression"] == "concerned"


def test_slow_search_can_continue_with_same_chatgpt_without_blocking_the_account(
    client, auth, chatgpt, monkeypatch
):
    value = vault.load(1)
    vault.update(1, value["generation"], {"web_enabled": True})
    bodies = []

    def respond(request):
        body = json.loads(request.content)
        bodies.append(body)
        if "tools" in body:
            raise httpx.ReadTimeout("Synthetic slow search", request=request)
        return httpx.Response(
            200,
            content=sse(
                completed(
                    "Posso orientar pelos cuidados gerais, mas não consegui conferir fontes agora."
                )
            ),
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: HTTP_CLIENT(transport=httpx.MockTransport(respond), **kwargs),
    )
    answer = ask(client, auth, "Pesquise como cuidar da minha roseira")
    assert answer["mode"] == "chatgpt" and len(bodies) == 2
    assert bodies[0]["reasoning"] == {"effort": "low"}
    assert bodies[1]["reasoning"] == {"effort": "none"}
    assert vault.load(1)["cooldown_until"] == 0


def test_discarded_preview_cannot_be_revived_or_read_by_another_user():
    publish = assistant_stream.begin(412, 123, "one")
    publish("Um texto público de orientação.", "serious")
    assert not assistant_stream.snapshot(413, 123, "one")
    assistant_stream.discard(412, 123)
    publish("Uma resposta atrasada.", "happy")
    assert not assistant_stream.snapshot(412, 123, "one")


@pytest.mark.parametrize(
    "source_url,has_preview",
    [
        ("https://plants.ces.ncsu.edu/plants/rosa/", True),
        ("http://127.0.0.1/private", False),
    ],
)
def test_search_streams_verified_text_before_completion_and_blocks_private_sources(
    client, auth, chatgpt, monkeypatch, source_url, has_preview
):
    vault.update(1, vault.load(1)["generation"], {"web_enabled": True})
    cid, req = start(client, auth), str(uuid4())
    entered, release = threading.Event(), threading.Event()
    text = "A roseira precisa de boa luz e rega conforme a umidade da terra."
    source = {"title": "NC State Extension", "url": source_url}
    item = {"type": "web_search_call", "status": "completed", "action": {"sources": [source]}}
    bodies = []

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield sse({"type": "response.output_item.done", "item": item})
            yield sse({"type": "response.output_text.delta", "delta": text})
            entered.set()
            assert await asyncio.to_thread(release.wait, 8)
            event = completed(text)
            event["response"]["output"].insert(0, item)
            yield sse(event)

    def respond(request):
        body = json.loads(request.content)
        bodies.append(body)
        return (
            httpx.Response(200, stream=Stream())
            if "tools" in body
            else httpx.Response(200, content=sse(completed("Não consegui conferir fontes agora.")))
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: HTTP_CLIENT(transport=httpx.MockTransport(respond), **kwargs),
    )
    with ThreadPoolExecutor() as executor:
        future = executor.submit(
            client.post,
            f"/api/assistant/conversations/{cid}/messages",
            headers=auth["one"],
            json={
                "text": "Pesquise como cuidar de uma roseira em vaso e cite as fontes consultadas.",
                "request_id": req,
            },
        )
        try:
            assert entered.wait(8)
            progress = client.get(
                f"/api/assistant/conversations/{cid}/progress", headers=auth["one"]
            ).json()
            assert bool(progress.get("text")) == has_preview
            if has_preview:
                assert progress["text"] == text and progress["phase"] == "writing"
        finally:
            release.set()
        response = future.result(timeout=8)
    assert response.status_code == 200
    assert response.json()["meta"]["searched_web"] == has_preview
    # Subscription token sharing rejects options accepted by the paid API.
    assert "max_tool_calls" not in bodies[0] and "max_output_tokens" not in bodies[0]
    assert bodies[0]["include"] == ["web_search_call.action.sources"]
    assert bodies[0]["reasoning"] == {"effort": "low"}
    assert not assistant_stream.snapshot(1, cid, req)


def test_sourced_answer_can_finish_after_the_search_phase_deadline(
    client, auth, chatgpt, monkeypatch
):
    vault.update(1, vault.load(1)["generation"], {"web_enabled": True})
    original_timeout = asyncio.timeout
    monkeypatch.setattr(asyncio, "timeout", lambda seconds: original_timeout(0.05))
    source = {"title": "NC State Extension", "url": "https://plants.ces.ncsu.edu/plants/rosa/"}
    item = {"type": "web_search_call", "status": "completed", "action": {"sources": [source]}}

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield sse({"type": "response.output_item.done", "item": item})
            await asyncio.sleep(0.15)
            event = completed("Confira a luz e a umidade da terra da sua roseira.")
            event["response"]["output"].insert(0, item)
            yield sse(event)

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: HTTP_CLIENT(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Stream())),
            **kwargs,
        ),
    )
    reply = ask(client, auth, "Pesquise como cuidar da minha roseira")
    assert reply["mode"] == "chatgpt" and reply["meta"]["searched_web"]
    assert reply["sources"][0]["url"] == source["url"]
    assert vault.usage(1)["calls"] == 1
