import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from app import assistant_credentials as vault
from app import assistant_installation as installation
from app import assistant_provider as local
from app.assistant_state import Memory, SemanticReply, advance
from app.assistant_web_search import parse_results, public_history, safe_public_url

SOURCE = {
    "title": "NC State — Crassula ovata",
    "url": "https://plants.ces.ncsu.edu/plants/crassula-ovata/",
}
ANSWER = "Uma possibilidade é *Crassula ovata 'Gollum'*, pelas folhas tubulares. Isso ainda é uma hipótese. fonte"


def researched_response():
    end = len(ANSWER)
    output = [
        {
            "type": "web_search_call",
            "status": "completed",
            "action": {"type": "search", "sources": [SOURCE]},
            "results": [
                {
                    "type": "image_result",
                    "image_url": "https://images.example.test/plant.jpg",
                    "source_website_url": SOURCE["url"],
                    "caption": "Folhas tubulares",
                },
            ],
        },
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": ANSWER,
                    "annotations": [
                        {
                            "type": "url_citation",
                            **SOURCE,
                            "start_index": end - 5,
                            "end_index": end,
                        },
                    ],
                }
            ],
        },
    ]
    event = {"type": "response.completed", "response": {"status": "completed", "output": output}}
    return httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        content=("data: " + json.dumps(event) + "\n\n").encode(),
    )


@pytest.fixture
def account(tmp_path, monkeypatch):
    """Administrator installation search is shared; old personal keys remain inert."""
    monkeypatch.setenv("RAFINHA_CREDENTIALS_DIR", str(tmp_path / "private"))
    vault.save(
        2,
        {
            "kind": "chatgpt",
            "generation": "legacy",
            "state": "ready",
            "enabled": True,
            "model": "gpt-test",
            "access_token": "legacy-unused",
            "daily_limit": 20,
            "web_enabled": True,
        },
    )
    installation.save_credential("tavily", "tvly-test-not-real-000000000", {})
    seen = []
    handler = {
        "response": lambda request: httpx.Response(
            200,
            json={
                "results": [
                    {
                        **SOURCE,
                        "content": "Crassula ovata Gollum has tubular leaves and cup-shaped tips.",
                        "score": 0.9,
                        "images": [
                            {
                                "url": "https://images.example.test/plant.jpg",
                                "description": "Folhas tubulares",
                            }
                        ],
                    }
                ]
            },
        )
    }
    original = httpx.AsyncClient

    def request(req):
        assert req.url.host == "api.tavily.com", (
            "Only the administrator Tavily credential may be used"
        )
        seen.append(json.loads(req.content))
        return handler["response"](req)

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(request), **kwargs),
    )
    monkeypatch.setattr(
        local,
        "answer",
        lambda *args: SemanticReply(text="Vamos continuar com os cuidados já relatados."),
    )

    def synthesis(question, facts, history, results, summaries, budget):
        return SemanticReply(text=ANSWER.replace("fonte", "[1]")), {
            "confidence": "medium",
            "sufficient": True,
            "agrees": True,
            "candidate": "Crassula ovata 'Gollum'",
        }

    monkeypatch.setattr(local, "evidence_answer", synthesis)
    return seen, handler


def start(client, auth):
    return client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]


def send(client, auth, cid, text):
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=auth["one"],
        json={"text": text, "request_id": str(uuid4())},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize(
    "text",
    [
        "Olá",
        "Bom dia",
        "Obrigado",
        "Quem é você?",
        "Vocês fazem poda?",
        "Quanto custa a Lavanda?",
        "Tem fertilizante em estoque?",
        "Quais serviços tenho hoje?",
        "Como regar uma suculenta?",
    ],
)
def test_internal_and_routine_messages_never_attach_web_tool(client, auth, account, text):
    seen, _ = account
    reply = send(client, auth, start(client, auth), text)
    assert not reply["meta"]["searched_web"]
    assert not any("tools" in body for body in seen)


@pytest.mark.parametrize(
    "text",
    [
        "Que suculenta parece a orelha do Shrek?",
        "Pesquise essa planta para mim",
        "Essa planta é tóxica para gatos?",
        "Existe alerta atual sobre praga X?",
        "Minha planta está com fungos",
        "Confira fontes sobre esta planta",
    ],
)
def test_use_one_tavily_search_when_external_evidence_matters(client, auth, account, text):
    seen, _ = account
    reply = send(client, auth, start(client, auth), text)
    assert reply["meta"]["searched_web"] and reply["meta"]["source_type"] == "web"
    assert len(seen) == 1
    assert seen[0]["search_depth"] == "basic"
    assert seen[0]["include_answer"] is False
    assert reply["sources"][0]["url"] == SOURCE["url"]
    assert reply["sources"][0]["domain"] == "plants.ces.ncsu.edu"
    assert "[1]" in reply["text"] and "cite" not in reply["text"]


@pytest.mark.parametrize("patch", [{"search_enabled": False}, {"mode": "on_request"}])
def test_disabled_connection_or_search_never_spends_a_search_request(client, auth, account, patch):
    seen, _ = account
    vault.protected_save("installation-ai-settings", {**installation.settings(), **patch})
    reply = send(client, auth, start(client, auth), "Que suculenta parece a orelha do Shrek?")
    assert not reply["meta"]["searched_web"] and not seen


def test_on_request_mode_still_honours_an_explicit_request(client, auth, account):
    vault.protected_save(
        "installation-ai-settings", {**installation.settings(), "mode": "on_request"}
    )
    reply = send(client, auth, start(client, auth), "Pesquise essa planta para mim")
    assert reply["meta"]["searched_web"]


def test_hypothesis_and_previous_symptoms_survive_the_next_care_report(client, auth, account):
    seen, _ = account
    cid = start(client, auth)
    send(client, auth, cid, "Tenho uma planta que está morrendo e não sei o que fazer")
    seen.clear()
    result = send(client, auth, cid, "eu só sei que é uma suculenta, parece com a orelha do Shrek")
    assert result["meta"]["searched_web"] and len(result["images"]) == 1
    assert seen[0]["include_images"] is True
    assert seen[0]["include_image_descriptions"] is True
    follow = send(client, auth, cid, "eu não deixei ela no sol e reguei muito")
    assert not follow["meta"]["searched_web"] and len(seen) == 1
    memory = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()["memory"]
    assert memory["plant_name"] is None and memory["species_id"] is None
    assert memory["identity_hypothesis"]["label"] == "Crassula ovata 'Gollum'"
    assert memory["identity_hypothesis"]["status"] == "hypothesis"
    assert "morrendo" in memory["slots"]["symptoms"]
    assert "excessiva" in memory["slots"]["watering"]


@pytest.mark.parametrize("status", [400, 403, 503])
def test_search_failure_uses_local_without_another_paid_request(client, auth, account, status):
    seen, handler = account
    handler["response"] = lambda request: httpx.Response(status)
    reply = send(client, auth, start(client, auth), "Pesquise essa planta para mim")
    assert not reply["meta"]["searched_web"] and len(seen) == 1
    assert "Não consegui conferir fontes externas" in reply["text"] and not reply["sources"]
    if status in {400, 403}:
        assert installation.public_status()["providers"]["tavily"]["configured"]


def test_unverified_generated_links_are_never_presented_as_consulted_sources(
    client, auth, account, monkeypatch
):
    _, handler = account
    handler["response"] = lambda request: httpx.Response(
        200, json={"answer": "Fonte: https://invented.example.test", "results": []}
    )
    reply = send(client, auth, start(client, auth), "Pesquise essa planta para mim")
    assert not reply["sources"] and "invented.example" not in reply["text"]


def test_legacy_chatgpt_token_never_authorizes_paid_research(client, auth, account):
    seen, _ = account
    reply = send(client, auth, start(client, auth), "Pesquise essa planta para mim")
    assert reply["mode"] in {"local", "catalog"} and reply["meta"]["searched_web"]
    assert len(seen) == 1 and "tools" not in seen[0]
    assert not vault.usage(2).get("calls")
    assert installation.usage()["daily"].get("openai", 0) == 0


def test_administrator_search_options_persist_independently(client, auth, account):
    updated = client.put(
        "/api/assistant/admin-ai/settings",
        headers=auth["admin"],
        json={"mode": "on_request", "images": False},
    )
    assert updated.status_code == 200, updated.text
    saved = installation.settings()
    assert saved["mode"] == "on_request" and saved["images"] is False
    assert saved["response_timeout"] == 30 and saved["tavily_daily_limit"] == 50
    assert saved["search_enabled"] and not saved["paid_search_enabled"]
    denied = client.put(
        "/api/assistant/admin-ai/settings", headers=auth["one"], json={"paid_search_enabled": True}
    )
    assert denied.status_code == 403 and not installation.settings()["paid_search_enabled"]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/a",
        "https://10.1.2.3/a",
        "javascript:alert(1)",
        "https://secret@public.test/a",
        "https://server.local/a",
    ],
)
def test_sources_and_images_reject_private_or_executable_urls(url):
    assert safe_public_url(url) is None
    result = parse_results(
        [
            {
                "type": "web_search_call",
                "status": "completed",
                "results": [
                    {"type": "image_result", "image_url": url, "source_website_url": SOURCE["url"]}
                ],
            }
        ],
        "texto",
    )
    assert not result["images"]


def test_research_does_not_send_private_commercial_history():
    messages = [
        SimpleNamespace(text="Meus pedidos", context={}),
        SimpleNamespace(text="Pedido privado", context={"_meta": {"source_type": "company"}}),
        SimpleNamespace(text="Tenho uma suculenta", context={}),
    ]
    assert public_history(messages) == messages[2:]


def test_an_explicit_new_plant_clears_the_old_hypothesis():
    memory = Memory(
        identity_hypothesis={"label": "Crassula ovata"},
        research_context={"summary": "Fonte antiga"},
        slots={"plant_group": "suculenta"},
    )
    changed = advance(memory.model_dump(), "Tenho uma roseira", {"species": []})
    assert (
        changed.plant_name == "roseira"
        and not changed.identity_hypothesis
        and not changed.research_context
    )


def test_outside_italic_cultivar_is_a_hypothesis_and_tracking_links_are_deduplicated():
    output = [
        {
            "type": "web_search_call",
            "status": "completed",
            "action": {
                "sources": [SOURCE, {**SOURCE, "url": SOURCE["url"] + "?utm_source=openai"}]
            },
        }
    ]
    result = parse_results(output, "Pela descrição, talvez seja *Crassula ovata* ‘Gollum’.")
    assert result["hypothesis"]["label"] == "Crassula ovata 'Gollum'"
    assert len(result["sources"]) == 1


def test_remote_origin_cannot_enable_research_or_change_usage_settings(client, auth, account):
    response = client.put(
        "/api/assistant/admin-ai/settings",
        headers={**auth["admin"], "Origin": "https://external.example.test"},
        json={"search_enabled": False, "tavily_daily_limit": 100},
    )
    assert response.status_code == 403
    assert (
        installation.settings()["search_enabled"]
        and installation.settings()["tavily_daily_limit"] == 50
    )


def test_no_internet_falls_back_without_leaking_transport_details(client, auth, account):
    seen, handler = account

    def offline(request):
        raise httpx.ConnectError("Offline diagnostic", request=request)

    handler["response"] = offline
    reply = send(client, auth, start(client, auth), "Pesquise essa planta para mim")
    assert len(seen) == 1 and not reply["meta"]["searched_web"]
    assert "Não consegui conferir fontes externas" in reply["text"]
    assert "Offline diagnostic" not in reply["text"]
