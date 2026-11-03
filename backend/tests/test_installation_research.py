"""Installation BYOK and the 18 required hybrid-routing/security scenarios."""

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from app import assistant_credentials as vault
from app import assistant_installation as installation
from app import assistant_provider as local
from app.assistant_hybrid_search import quality
from app.assistant_language import reported_plants
from app.assistant_search_providers import normalize_tavily
from app.assistant_state import SemanticReply

TAVILY_KEY = "tvly-test-credential-not-real-000001"
OPENAI_KEY = "sk-test-credential-not-real-000002"
SOURCES = [
    {
        "title": "NC State Crassula ovata Gollum",
        "url": "https://plants.ces.ncsu.edu/plants/crassula-ovata/",
        "content": "Crassula ovata Gollum has tubular leaves with cup-shaped tips. Overwatering can damage roots.",
        "score": 0.94,
        "images": [
            {"url": "https://images.example.test/gollum.jpg", "description": "Folhas tubulares"}
        ],
    },
    {
        "title": "University jade plant",
        "url": "https://homegarden.cahnr.uconn.edu/factsheets/jade-plants/",
        "content": "Crassula ovata Gollum has tubular leaves. Good drainage matters and overwatering can harm roots.",
        "score": 0.92,
    },
]


@pytest.fixture
def providers(tmp_path, monkeypatch):
    monkeypatch.setenv("RAFINHA_CREDENTIALS_DIR", str(tmp_path / "private"))
    calls = []
    state = {
        "tavily_status": 200,
        "rows": SOURCES,
        "confidence": "high",
        "sufficient": True,
        "agrees": True,
        "conflicting": False,
    }
    original = httpx.AsyncClient

    def respond(request):
        calls.append(
            (
                request.url.host,
                request.url.path,
                request.method,
                json.loads(request.content) if request.content else None,
            )
        )
        if request.url.path == "/usage":
            return httpx.Response(
                200,
                json={
                    "key": {"usage": 0, "limit": 1000},
                    "account": {"current_plan": "Researcher", "plan_usage": 0, "plan_limit": 1000},
                },
            )
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "gpt-4.1-mini"}]})
        if request.url.host == "api.tavily.com":
            if state["tavily_status"] == "offline":
                raise httpx.ConnectError("Secret transport diagnostic", request=request)
            return httpx.Response(
                state["tavily_status"], json={"results": state["rows"], "usage": {"credits": 1}}
            )
        if request.url.path == "/v1/responses":
            text = "Uma possibilidade é *Crassula ovata 'Gollum'*, pelas folhas tubulares. fonte"
            event = {
                "type": "response.completed",
                "response": {
                    "status": "completed",
                    "output": [
                        {
                            "type": "web_search_call",
                            "status": "completed",
                            "action": {
                                "sources": [
                                    {
                                        "title": "Kew Crassula ovata Gollum",
                                        "url": "https://powo.science.kew.org/taxon/example",
                                    }
                                ]
                            },
                        },
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": text,
                                    "annotations": [
                                        {
                                            "type": "url_citation",
                                            "title": "Kew Crassula ovata Gollum",
                                            "url": "https://powo.science.kew.org/taxon/example",
                                            "start_index": len(text) - 5,
                                            "end_index": len(text),
                                        }
                                    ],
                                }
                            ],
                        },
                    ],
                },
            }
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=("data: " + json.dumps(event) + "\n\n").encode(),
            )
        return httpx.Response(500)

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs),
    )
    monkeypatch.setattr(
        local,
        "answer",
        lambda *args: SemanticReply(
            text="Vamos aproveitar o que você já contou e conferir os cuidados."
        ),
    )

    def synthesis(question, facts, history, results, summaries, budget):
        reply = SemanticReply(
            text="Uma possibilidade é *Crassula ovata 'Gollum'*, pela descrição de folhas tubulares [1]. Isso é uma hipótese. Como estão as folhas agora?"
        )
        return reply, {
            **{k: state[k] for k in ["confidence", "sufficient", "agrees", "conflicting"]},
            "candidate": "Crassula ovata 'Gollum'",
        }

    monkeypatch.setattr(local, "evidence_answer", synthesis)
    return calls, state


def configure(client, auth, provider):
    response = client.post(
        f"/api/assistant/admin-ai/providers/{provider}/key",
        headers=auth["admin"],
        json={"key": TAVILY_KEY if provider == "tavily" else OPENAI_KEY},
    )
    assert response.status_code == 200, response.text
    return response.json()


def start(client, auth):
    return client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]


def ask(client, auth, text, cid=None):
    cid = cid or start(client, auth)
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=auth["one"],
        json={"text": text, "request_id": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


def search_calls(calls, provider):
    return [
        c
        for c in calls
        if c[0] == ("api.tavily.com" if provider == "tavily" else "api.openai.com")
        and c[2] == "POST"
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Olá",
        "Vocês fazem poda?",
        "Quanto custa a Lavanda?",
        "Tem hortelã em estoque?",
        "Mostre meus projetos em andamento",
        "Não reguei minha planta hoje",
    ],
)
def test_internal_requests_never_search(client, auth, providers, text):
    calls, _ = providers
    configure(client, auth, "tavily")
    ask(client, auth, text)
    assert not search_calls(calls, "tavily") and not search_calls(calls, "openai")


def test_identification_uses_tavily_then_local_synthesis(client, auth, providers):
    calls, _ = providers
    configure(client, auth, "tavily")
    answer = ask(client, auth, "Qual suculenta é conhecida como Orelha-de-Shrek?")
    assert len(search_calls(calls, "tavily")) == 1 and not search_calls(calls, "openai")
    assert answer["mode"] == "local" and answer["meta"]["searched_web"]
    assert "hipótese" in answer["text"] and len(answer["images"]) == 1
    assert answer["sources"][0]["provider"] == "tavily" and answer["sources"][0]["score"] == 0.94


def test_no_key_uses_local_without_search(client, auth, providers):
    calls, _ = providers
    answer = ask(client, auth, "Qual suculenta parece a orelha do Shrek?")
    # The mocked model only offers to help; supported internal guidance must
    # replace it rather than displaying an empty identification promise.
    assert answer["mode"] == "catalog" and not answer["meta"]["searched_web"]
    assert "Gollum" in answer["text"] and "não confirma" in answer["text"]
    assert not search_calls(calls, "tavily") and not search_calls(calls, "openai")
    assert not installation.available("tavily") and not installation.available("openai")


def test_typo_comparison_clue_and_short_followups_keep_one_search(client, auth, providers):
    calls, _ = providers
    configure(client, auth, "tavily")
    cid = start(client, auth)
    ask(client, auth, "Como cuidar de uma suculent5a, é igual cactos?", cid)
    assert not search_calls(calls, "tavily")
    found = ask(client, auth, "a que eu ganhei parece com a orelha do sherek", cid)
    assert found["meta"]["searched_web"] and len(search_calls(calls, "tavily")) == 1
    for text in ["vc sabe qual é", "me diga", "eu não deixei ela no sol e reguei muito"]:
        answer = ask(client, auth, text, cid)
        assert not answer["meta"]["searched_web"]
    memory = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()["memory"]
    assert memory["plant_name"] is None and memory["species_id"] is None
    assert memory["identity_hypothesis"]["label"] == "Crassula ovata 'Gollum'"
    assert memory["slots"]["plant_group"] == "suculenta"
    assert len(search_calls(calls, "tavily")) == 1 and not search_calls(calls, "openai")


@pytest.mark.parametrize("openai_configured", [False, True])
def test_primary_failure_never_uses_paid_without_authorization(
    client, auth, providers, openai_configured
):
    calls, state = providers
    configure(client, auth, "tavily")
    if openai_configured:
        configure(client, auth, "openai")
    state["tavily_status"] = 432
    answer = ask(client, auth, "Pesquise esta suculenta para mim")
    assert not search_calls(calls, "openai") and not installation.settings()["paid_search_enabled"]
    assert not answer["meta"]["searched_web"]


def test_paid_fallback_requires_valid_key_and_explicit_admin_activation(client, auth, providers):
    calls, state = providers
    configure(client, auth, "tavily")
    info = configure(client, auth, "openai")
    assert not info["settings"]["paid_search_enabled"]
    enabled = client.put(
        "/api/assistant/admin-ai/settings",
        headers=auth["admin"],
        json={"paid_search_enabled": True},
    )
    assert enabled.status_code == 200
    state["tavily_status"] = 503
    answer = ask(client, auth, "Pesquise essa suculenta para mim")
    assert len(search_calls(calls, "tavily")) == 1 and len(search_calls(calls, "openai")) == 1
    assert answer["mode"] == "local" and answer["meta"]["searched_web"]
    assert calls.index(search_calls(calls, "tavily")[0]) < calls.index(
        search_calls(calls, "openai")[0]
    )


def test_high_confidence_does_not_call_paid_provider(client, auth, providers):
    calls, _ = providers
    configure(client, auth, "tavily")
    configure(client, auth, "openai")
    client.put(
        "/api/assistant/admin-ai/settings",
        headers=auth["admin"],
        json={"paid_search_enabled": True},
    )
    answer = ask(client, auth, "Pesquise cuidados gerais para meu jardim")
    assert answer["meta"]["confidence"] == "high" and not search_calls(calls, "openai")


def test_low_confidence_in_important_subject_allows_additional_verification(
    client, auth, providers
):
    calls, state = providers
    configure(client, auth, "tavily")
    configure(client, auth, "openai")
    client.put(
        "/api/assistant/admin-ai/settings",
        headers=auth["admin"],
        json={"paid_search_enabled": True, "mode": "important_double"},
    )
    state.update(confidence="low", conflicting=True, sufficient=False, agrees=False)
    answer = ask(client, auth, "Essa planta é tóxica para gatos? Alguns sites discordam")
    assert len(search_calls(calls, "tavily")) == 1 and len(search_calls(calls, "openai")) == 1
    assert answer["meta"]["research"]["conflicting"] and answer["meta"]["confidence"] == "low"


@pytest.mark.parametrize("provider", ["tavily", "openai"])
def test_key_is_protected_masked_and_really_removed(client, auth, providers, provider):
    info = configure(client, auth, provider)
    key = TAVILY_KEY if provider == "tavily" else OPENAI_KEY
    assert (
        key not in json.dumps(info)
        and key.encode() not in (vault.root() / f"installation-{provider}.bin").read_bytes()
    )
    assert (
        client.delete(
            f"/api/assistant/admin-ai/providers/{provider}", headers=auth["admin"]
        ).status_code
        == 204
    )
    assert installation.credential(provider) is None and not installation.available(provider)
    assert not (vault.root() / f"installation-{provider}.bin").exists()


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", "/api/assistant/admin-ai", None),
        ("put", "/api/assistant/admin-ai/settings", {"paid_search_enabled": True}),
        ("post", "/api/assistant/admin-ai/providers/tavily/key", {"key": TAVILY_KEY}),
        ("delete", "/api/assistant/admin-ai/providers/openai", None),
        ("get", "/api/assistant/connection", None),
        ("post", "/api/assistant/connection/chatgpt/start", {"open_browser": False}),
    ],
)
def test_customer_cannot_manage_any_provider(client, auth, providers, method, path, body):
    response = getattr(client, method)(
        path, headers=auth["one"], **({"json": body} if body else {})
    )
    assert response.status_code == 403
    assert not providers[0]


def test_admin_permission_and_clean_install_defaults(client, auth, providers):
    response = client.get("/api/assistant/admin-ai", headers=auth["admin"])
    assert response.status_code == 200 and response.json()["permission"] == "MANAGE_AI_SETTINGS"
    assert not response.json()["providers"]["tavily"]["configured"]
    assert not response.json()["providers"]["openai"]["configured"]
    assert not response.json()["settings"]["paid_search_enabled"]


def test_offline_search_keeps_green_scape_and_local_conversation(
    client, auth, providers, monkeypatch
):
    calls, state = providers
    configure(client, auth, "tavily")
    state["tavily_status"] = "offline"
    answer = ask(client, auth, "Pesquise essa planta para mim")
    assert not answer["meta"]["searched_web"] and "Secret transport" not in answer["text"]
    assert client.get("/api/health").status_code == 200
    monkeypatch.setattr(local, "answer", lambda *args: None)
    assert "Poda" in ask(client, auth, "Vocês fazem poda?")["text"]
    assert not search_calls(calls, "openai")


def test_description_hypothesis_symptoms_and_watering_survive_followups(client, auth, providers):
    calls, _ = providers
    configure(client, auth, "tavily")
    cid = start(client, auth)
    ask(client, auth, "Tenho uma planta que está morrendo", cid)
    answer = ask(client, auth, "É uma suculenta, parece uma orelha do Shrek", cid)
    assert answer["meta"]["searched_web"]
    before = len(search_calls(calls, "tavily"))
    ask(client, auth, "Eu não deixei ela no sol e reguei muito", cid)
    memory = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()["memory"]
    assert memory["identity_hypothesis"]["label"] == "Crassula ovata 'Gollum'"
    assert "morrendo" in memory["slots"]["symptoms"] and "excessiva" in memory["slots"]["watering"]
    assert memory["plant_name"] is None and len(search_calls(calls, "tavily")) == before


def test_paid_limits_are_atomic_and_disconnect_does_not_reset_counters(client, auth, providers):
    configure(client, auth, "openai")
    client.put(
        "/api/assistant/admin-ai/settings",
        headers=auth["admin"],
        json={"paid_search_enabled": True, "paid_daily_limit": 3, "paid_monthly_limit": 3},
    )
    with ThreadPoolExecutor(max_workers=6) as pool:
        reservations = list(
            pool.map(lambda _: installation.reserve("openai", "test_limit"), range(12))
        )
    assert sum(value is not None for value, _ in reservations) == 3
    client.delete("/api/assistant/admin-ai/providers/openai", headers=auth["admin"])
    configure(client, auth, "openai")
    assert (
        installation.usage()["daily"]["openai"] == 3
        and not installation.settings()["paid_search_enabled"]
    )


def test_on_request_mode_and_disabled_paid_mode(client, auth, providers):
    calls, _ = providers
    configure(client, auth, "tavily")
    configure(client, auth, "openai")
    client.put(
        "/api/assistant/admin-ai/settings", headers=auth["admin"], json={"mode": "on_request"}
    )
    ask(client, auth, "Qual suculenta parece orelha do Shrek?")
    assert not search_calls(calls, "tavily")
    ask(client, auth, "Pesquise qual suculenta parece orelha do Shrek")
    assert len(search_calls(calls, "tavily")) == 1
    client.put(
        "/api/assistant/admin-ai/settings",
        headers=auth["admin"],
        json={"mode": "free_only", "paid_search_enabled": True},
    )
    assert not installation.settings()["paid_search_enabled"]


def test_urls_are_deduplicated_and_unattributed_top_level_images_are_not_shown():
    result = normalize_tavily(
        {
            "results": [SOURCES[0], {**SOURCES[0], "url": SOURCES[0]["url"] + "?utm_source=test"}],
            "images": ["https://images.example.test/no-origin.jpg"],
        },
        True,
    )
    assert len(result.results) == 1 and len(result.images) == 1


def test_customer_status_never_exposes_installation_credentials_or_cost_controls(
    client, auth, providers
):
    configure(client, auth, "tavily")
    configure(client, auth, "openai")
    info = client.get("/api/assistant/status", headers=auth["one"]).json()
    assert (
        "providers" not in info and "connection" not in info and "paid_search_enabled" not in info
    )
    assert TAVILY_KEY not in json.dumps(info) and OPENAI_KEY not in json.dumps(info)


def test_credentials_pasted_in_chat_are_rejected_before_database_write(client, auth, providers):
    cid = start(client, auth)
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=auth["one"],
        json={"text": "Minha chave é " + TAVILY_KEY, "request_id": str(uuid4())},
    )
    assert response.status_code == 422 and TAVILY_KEY not in response.text
    assert not client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()[
        "messages"
    ]


def test_admin_validation_errors_never_echo_extra_sensitive_fields(client, auth, providers):
    response = client.put(
        "/api/assistant/admin-ai/settings", headers=auth["admin"], json={"unknown_key": OPENAI_KEY}
    )
    assert response.status_code == 422 and OPENAI_KEY not in response.text


def test_source_content_credentials_are_redacted_before_cache_or_model():
    data = normalize_tavily({"results": [{**SOURCES[0], "content": "Plant facts. " + OPENAI_KEY}]})
    assert (
        OPENAI_KEY not in data.results[0].content
        and "credencial removida" in data.results[0].content
    )


def test_current_information_never_gets_high_confidence_from_undated_sources():
    result = normalize_tavily({"results": SOURCES})
    assessment = {"confidence": "high", "agrees": True, "sufficient": True, "conflicting": False}
    assert quality(result.results, assessment) == "high"
    assert quality(result.results, assessment, current=True) == "low"


def test_paid_limit_is_shared_between_independent_processes(client, auth, providers):
    configure(client, auth, "openai")
    client.put(
        "/api/assistant/admin-ai/settings",
        headers=auth["admin"],
        json={"paid_search_enabled": True, "paid_daily_limit": 3, "paid_monthly_limit": 3},
    )
    snippet = "from app.assistant_installation import reserve; print(bool(reserve('openai','process_limit')[0]))"
    environment = {**os.environ, "PYTHONPATH": "backend"}
    children = [
        subprocess.Popen(
            [sys.executable, "-c", snippet],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        for _ in range(6)
    ]
    outputs = []
    for child in children:
        out, err = child.communicate(timeout=30)
        assert child.returncode == 0, err.decode(errors="replace")
        outputs.append(out.decode().strip())
    assert outputs.count("True") == 3 and outputs.count("False") == 3


@pytest.mark.parametrize("provider", ["tavily", "openai"])
def test_testing_a_key_cannot_resurrect_it_after_concurrent_removal(
    client, auth, providers, monkeypatch, provider
):
    from app import assistant_admin_ai

    configure(client, auth, provider)

    def remote_validation(kind, key):
        installation.remove_credential(kind)
        return {"usage": {}} if kind == "tavily" else {"models": [{"id": "gpt-4.1-mini"}]}

    monkeypatch.setattr(assistant_admin_ai, "validate", remote_validation)
    response = client.post(
        f"/api/assistant/admin-ai/providers/{provider}/test", headers=auth["admin"]
    )
    assert response.status_code == 409 and installation.credential(provider) is None


@pytest.mark.parametrize("key", ["sk-" + "a" * 17, "tvly-" + "a" * 15])
def test_minimum_accepted_key_lengths_are_also_rejected_in_chat(client, auth, providers, key):
    cid = start(client, auth)
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=auth["one"],
        json={"text": key, "request_id": str(uuid4())},
    )
    assert response.status_code == 422 and key not in response.text


def test_failed_paid_search_is_cached_instead_of_repeated_on_same_question(
    client, auth, providers, monkeypatch
):
    from app.assistant_search_providers import OpenAIWebSearchProvider, SearchBundle

    calls, state = providers
    configure(client, auth, "tavily")
    configure(client, auth, "openai")
    client.put(
        "/api/assistant/admin-ai/settings",
        headers=auth["admin"],
        json={"paid_search_enabled": True},
    )
    state.update(confidence="low", sufficient=False, agrees=False)
    paid_attempts = []

    def fail(*args, **kwargs):
        paid_attempts.append(True)
        return SearchBundle("openai", "http_error")

    monkeypatch.setattr(OpenAIWebSearchProvider, "search", fail)
    for _ in range(2):
        ask(client, auth, "Pesquise cuidados gerais para meu jardim")
    assert len(paid_attempts) == 1 and len(search_calls(calls, "tavily")) == 1


@pytest.mark.parametrize(
    "text",
    [
        "Esqueci de regar e ela está murchando",
        "Fui regar e a planta estava murcha",
        "Não sei cuidar e ela está amarelada",
        "Preciso regar ou ela pode secar",
    ],
)
def test_care_action_followed_by_a_conjunction_is_not_a_new_plant(text):
    assert reported_plants(text) == []


def test_missed_watering_continues_the_previously_named_plant(client, auth, providers):
    cid = start(client, auth)
    ask(client, auth, "Tenho uma planta, uma roseira", cid)
    ask(client, auth, "Esqueci de regar e ela está murchando", cid)
    memory = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()["memory"]
    assert memory["plant_name"] == "roseira" and not memory["plant_choices"]
    assert "murchando" in memory["slots"]["symptoms"]


def test_repeated_model_intro_is_not_used_after_a_new_problem_report(
    client, auth, providers, monkeypatch
):
    repeated = (
        "Posso ajudar com os cuidados gerais. Se houver algum problema específico, me informe!"
    )
    monkeypatch.setattr(local, "answer", lambda *args: SemanticReply(text=repeated))
    cid = start(client, auth)
    first = ask(client, auth, "Tenho uma planta, uma roseira", cid)
    assert "roseira" in first["text"] and "cuidados gerais" in first["text"]
    assert first["text"] != repeated and first["meta"]["fallback"]
    second = ask(client, auth, "Esqueci de regar e ela está murchando", cid)
    assert second["text"] != repeated and "umidade" in second["text"]
    assert "seca ou ainda úmida" in second["text"] and second["meta"]["fallback"]


def test_suggested_questions_are_not_sent_as_asserted_facts():
    from app.assistant_provider import prompt

    facts = {
        "records": {
            "session": {"plant_name": "roseira", "slots": {"plant_name": "roseira"}},
            "species": [],
        },
        "products": [],
        "services": [],
        "_topic": "problem",
    }
    value = prompt("Ela está murchando", facts, [], compact=True)
    assert "next_question" not in value[0]["content"]
