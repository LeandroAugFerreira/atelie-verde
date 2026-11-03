import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from app import assistant_provider as provider
from app.assistant_emotions import expression
from app.assistant_knowledge import grounded_text
from app.database import SessionLocal
from app.models import Article, AssistantMessage, Product, Project
from sqlalchemy import select


def start(client, auth, who="one"):
    response = client.post("/api/assistant/conversations", headers=auth[who])
    assert response.status_code == 201
    return response.json()["id"]


def send(client, auth, id, text="Como cuidar da Lavanda?", **fields):
    return client.post(
        f"/api/assistant/conversations/{id}/messages",
        headers=auth["one"],
        json={"text": text, "request_id": str(uuid4()), **fields},
    )


def test_private_history_preferences_and_no_commercial_mutation(client, auth, monkeypatch):
    monkeypatch.setenv("RAFINHA_PROVIDER", "catalog")
    with SessionLocal() as db:
        db.add(
            Article(
                id=1,
                slug="lavanda",
                title="Cultivar lavanda",
                category="Plantio",
                summary="Cultivo em vasos.",
                minutes=3,
                species_id=1,
                sections=[],
                sources=[{"title": "Guia", "url": "https://example.org/guia"}],
            )
        )
        db.commit()
    id = start(client, auth)
    response = send(client, auth, id)
    assert response.status_code == 200
    answer = response.json()
    assert "Lavanda" in answer["text"] and answer["mode"] == "catalog"
    assert answer["sources"][0]["url"] == "https://example.org/guia"
    assert {a["kind"] for a in answer["actions"]} == {"open_species", "open_article"}
    assert client.get(f"/api/assistant/conversations/{id}", headers=auth["two"]).status_code == 404
    assert (
        client.delete(f"/api/assistant/conversations/{id}", headers=auth["two"]).status_code == 404
    )
    assert client.get("/api/assistant/conversations", headers=auth["two"]).json() == []
    assert (
        client.post(
            f"/api/assistant/conversations/{id}/messages",
            headers=auth["two"],
            json={"text": "olá", "request_id": str(uuid4())},
        ).status_code
        == 404
    )
    prefs = {"enabled": True, "motion": False, "typewriter": False, "voice": False}
    assert client.put("/api/assistant/preferences", headers=auth["one"], json=prefs).json() == prefs
    assert client.get("/api/assistant/preferences", headers=auth["two"]).json()["motion"]
    assert client.get("/api/assistant/preferences", headers=auth["one"]).json() == prefs
    prices = send(client, auth, id, "Qual o preço e estoque da Lavanda?").json()
    assert "R$ 24,90" in prices["text"] and "5 unidade" in prices["text"]
    with SessionLocal() as db:
        assert db.get(Product, 1).stock == 5
    assert (
        client.delete(f"/api/assistant/conversations/{id}", headers=auth["one"]).status_code == 204
    )
    with SessionLocal() as db:
        assert not db.scalars(select(AssistantMessage)).all()


def test_authorized_context_and_idempotency(client, auth, monkeypatch):
    monkeypatch.setenv("RAFINHA_PROVIDER", "catalog")
    with SessionLocal() as db:
        db.add(
            Project(
                id=1,
                customer_id=3,
                name="Jardim privado",
                address="Endereço privado",
                area=10,
                budget_cents=1000,
                start_date="2026-10-05",
                end_date="2026-10-06",
                description="",
                plants=[],
                materials=[],
                services=[],
                tasks=[],
            )
        )
        db.commit()
    id = start(client, auth)
    assert send(client, auth, id, context={"kind": "project", "id": 1}).status_code == 404
    request = str(uuid4())
    response = send(client, auth, id, request_id=request, context={"kind": "product", "id": 1})
    again = send(client, auth, id, request_id=request, context={"kind": "product", "id": 1})
    assert response.json()["id"] == again.json()["id"]
    assert (
        len(
            client.get(f"/api/assistant/conversations/{id}", headers=auth["one"]).json()["messages"]
        )
        == 2
    )
    assert send(client, auth, id, context={"kind": "sql", "id": 1}).status_code == 422
    assert send(client, auth, id, text="   ").status_code == 422


def test_own_planning_context_and_missing_knowledge(client, auth, monkeypatch):
    monkeypatch.setenv("RAFINHA_PROVIDER", "catalog")
    with SessionLocal() as db:
        db.add(
            Project(
                id=1,
                customer_id=2,
                name="Jardim próprio",
                address="Endereço não enviado ao provedor",
                area=96,
                budget_cents=1000,
                start_date="2026-10-05",
                end_date="2026-10-06",
                description="",
                plants=[{"species_id": 1, "quantity": 3}],
                materials=[],
                services=[],
                tasks=[],
                brief={"width": 12, "length": 8, "light": "Sol pleno", "maintenance": "Média"},
            )
        )
        db.commit()
    id = start(client, auth)
    result = send(
        client,
        auth,
        id,
        "Como completar as medidas do levantamento?",
        context={"kind": "project", "id": 1},
    ).json()
    assert "96 m²" in result["text"] and "12 × 8 m" in result["text"]
    assert "Endereço não enviado" not in result["text"]
    unknown = send(client, auth, id, "Minha planta desconhecida está estranha").json()
    assert "nome da planta" in unknown["text"] and unknown["sources"] == []


def test_group_recommendation_and_garden_suggestion(client, auth, monkeypatch):
    from app.models import Service

    monkeypatch.setenv("RAFINHA_PROVIDER", "catalog")
    with SessionLocal() as db:
        db.add(
            Service(
                id=2,
                name="Paisagista virtual",
                category="Projeto",
                delivery_mode="Virtual",
                description="Planejamento remoto do jardim.",
                price_cents=40000,
                unit="projeto",
            )
        )
        db.commit()
    id = start(client, auth)
    flowers = send(
        client, auth, id, "Quais flores de sol pleno combinam com espaço pequeno?"
    ).json()
    assert "Lavanda" in flowers["text"]
    garden = send(client, auth, id, "Quero planejar meu jardim").json()
    assert "Paisagista virtual" in garden["text"]
    assert any(a["kind"] == "open_service" and a["id"] == 2 for a in garden["actions"])


def test_empathy_expression_is_persisted_and_safe(client, auth, monkeypatch):
    monkeypatch.setenv("RAFINHA_PROVIDER", "catalog")
    id = start(client, auth)
    reply = send(client, auth, id, "Não reguei a Lavanda e as folhas estão murchas").json()
    assert reply["expression"] == "concerned" and "com atenção" in reply["text"]
    history = client.get(f"/api/assistant/conversations/{id}", headers=auth["one"]).json()
    assert history["messages"][-1]["expression"] == "concerned"
    assert "_expression" not in history["messages"][-1]["context"]
    assert send(client, auth, id, "Obrigado, a planta melhorou!").json()["expression"] in {
        "happy",
        "relieved",
    }
    assert expression("Olá", {}) == "greeting"
    assert expression("Como cuidar da Lavanda?", {}) == "explaining"


def test_concurrent_reservation_cancel_and_resume(client, auth, monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def slow(*args):
        entered.set()
        assert release.wait(10)
        return "Uma resposta que foi interrompida."

    monkeypatch.setattr(provider, "answer", slow)
    id = start(client, auth)
    request = str(uuid4())
    with ThreadPoolExecutor() as executor:
        pending = executor.submit(send, client, auth, id, request_id=request)
        assert entered.wait(10)
        assert send(client, auth, id).status_code == 409
        assert (
            client.post(
                f"/api/assistant/conversations/{id}/messages/{request}/cancel", headers=auth["two"]
            ).status_code
            == 404
        )
        assert client.post(
            f"/api/assistant/conversations/{id}/messages/{request}/cancel", headers=auth["one"]
        ).json()["cancelled"]
        release.set()
        assert pending.result().status_code == 409
    detail = client.get(f"/api/assistant/conversations/{id}", headers=auth["one"]).json()
    assert detail["pending_request"] == ""
    assert detail["messages"][-1]["status"] == "interrupted"
    monkeypatch.setattr(provider, "answer", lambda *args: None)
    assert send(client, auth, id).status_code == 200


def test_configuration_disabled_provider_and_catalog_fallback(client, auth, monkeypatch):
    monkeypatch.setenv("RAFINHA_OLLAMA_MODEL", "model:cloud")
    assert client.get("/api/assistant/status", headers=auth["one"]).json()["mode"] == "catalog"
    cfg = {
        "enabled": False,
        "greeting": "Mensagem de boas-vindas personalizada.",
        "suggestions": ["Olá"],
    }
    assert (
        client.put("/api/assistant/configuration", headers=auth["one"], json=cfg).status_code == 403
    )
    assert (
        client.put("/api/assistant/configuration", headers=auth["admin"], json=cfg).status_code
        == 200
    )
    assert (
        client.get("/api/assistant/status", headers=auth["one"]).json()["greeting"]
        == cfg["greeting"]
    )
    assert client.post("/api/assistant/conversations", headers=auth["one"]).status_code == 409
    cfg["enabled"] = True
    client.put("/api/assistant/configuration", headers=auth["admin"], json=cfg)
    id = start(client, auth)
    assert (
        send(client, auth, id, "Aprovar meu orçamento e baixar o estoque").json()["mode"]
        == "catalog"
    )
    assert client.get("/api/orders", headers=auth["one"]).json() == []


@pytest.mark.parametrize("behavior", ["success", "timeout", "invalid", "invented_price"])
def test_real_provider_protocol_is_bounded_and_validated(client, auth, monkeypatch, behavior):
    monkeypatch.setenv("RAFINHA_OLLAMA_MODEL", "teste-local")
    monkeypatch.setenv("RAFINHA_PROVIDER", "auto")
    http_client = httpx.AsyncClient

    def handle(request):
        assert request.url.host == "127.0.0.1"
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "teste-local"}]})
        if behavior == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if behavior == "invalid":
            return httpx.Response(200, json={"message": {"content": "not-json"}})
        text = (
            "Use os cuidados da Lavanda informados no catálogo."
            if behavior == "success"
            else "Compre por R$ 9,99."
        )
        return httpx.Response(
            200, json={"message": {"content": __import__("json").dumps({"text": text})}}
        )

    monkeypatch.setattr(
        provider.httpx,
        "AsyncClient",
        lambda **kwargs: http_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    id = start(client, auth)
    response = send(client, auth, id)
    assert response.status_code == 200
    assert response.json()["mode"] == ("local" if behavior == "success" else "catalog")
    assert all(
        a["kind"]
        in {"open_species", "open_article", "open_product", "open_service", "request_quote"}
        for a in response.json()["actions"]
    )
    assert not grounded_text("<script>bad</script>", {"products": [], "services": []})
