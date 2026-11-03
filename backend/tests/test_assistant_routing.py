from uuid import uuid4

import pytest
from app import assistant_engine as engine
from app.assistant_research import source_summary
from app.database import SessionLocal
from app.models import Appointment, Species


def ask(client, auth, text, who="one"):
    cid = client.post("/api/assistant/conversations", headers=auth[who]).json()["id"]
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=auth[who],
        json={"text": text, "request_id": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_card_fields_do_not_cover_an_unrelated_subject(client, auth, monkeypatch):
    seen = []
    monkeypatch.setattr(
        engine,
        "research",
        lambda db, name, topic, *args: (
            seen.append(topic) or {"documents": [], "sources": [], "status": "unavailable"}
        ),
    )
    answer = ask(client, auth, "Como fazer propagação da Lavanda?")
    assert not seen and answer["meta"]["research"]["needed"]
    assert answer["meta"]["research"]["status"] == "not_configured"
    assert not answer["meta"]["searched_web"]
    assert "Não encontrei orientação verificada sobre propagação" in answer["text"]


def test_existing_propagation_is_used_without_external_calls(client, auth, monkeypatch):
    with SessionLocal() as db:
        plant = db.get(Species, 1)
        plant.propagation = "Propagação por estaquia, conforme a ficha cadastrada."
        db.commit()
    monkeypatch.setattr(
        engine, "research", lambda *args: pytest.fail("Registered subject is sufficient")
    )
    answer = ask(client, auth, "Como fazer propagação da Lavanda?")
    assert "estaquia" in answer["text"] and not answer["meta"]["research"]["needed"]


@pytest.mark.parametrize(
    "text",
    [
        "Olá",
        "Quem é você?",
        "Não reguei a Lavanda hoje",
        "Vocês fazem poda?",
        "Quanto custa a Lavanda?",
    ],
)
def test_everyday_messages_do_not_research(client, auth, monkeypatch, text):
    monkeypatch.setattr(engine, "research", lambda *args: pytest.fail("Unnecessary research"))
    assert not ask(client, auth, text)["meta"]["research"]["needed"]


def test_current_regional_question_does_not_claim_historical_care_is_current(client, auth):
    answer = ask(
        client, auth, "Qual doença está afetando os ipês na região de Campinas atualmente?"
    )
    assert answer["meta"]["research"]["needed"]
    assert "fontes atuais verificadas" in answer["text"] and not answer["sources"]


def test_customer_names_only_visible_to_admin_and_not_cloud(client, auth, monkeypatch):
    monkeypatch.setattr(engine, "research", lambda *args: pytest.fail("Private information"))
    own = ask(client, auth, "Mostre meus clientes", who="admin")
    denied = ask(client, auth, "Mostre meus clientes")
    assert "Cliente um" in own["text"] and "Cliente dois" in own["text"]
    assert "apenas para o administrador" in denied["text"] and "Cliente dois" not in denied["text"]


def test_customer_schedule_is_owned_and_dates_are_from_database(client, auth, monkeypatch):
    from app.clock import today

    with SessionLocal() as db:
        for id, owner, title in [
            (1, 2, "Serviço do cliente um"),
            (2, 3, "Serviço privado do cliente dois"),
        ]:
            db.add(
                Appointment(
                    id=id,
                    customer_id=owner,
                    service_id=1,
                    title=title,
                    date=today().isoformat(),
                    start_time="15:00",
                    end_time="16:00",
                    responsible="Equipe",
                    status="Agendado",
                    address="Privado",
                )
            )
        db.commit()
    monkeypatch.setattr(engine, "research", lambda *args: pytest.fail("Private agenda"))
    result = ask(client, auth, "Qual é meu próximo serviço?")
    assert "Serviço do cliente um" in result["text"] and "15:00" in result["text"]
    assert "cliente dois" not in result["text"]


def test_web_summary_addresses_the_requested_topic():
    docs = [
        {
            "excerpt": "Light: Full sun Soil Drainage: Good Drainage Recommended Propagation Strategy: Stem Cutting, Division"
        }
    ]
    assert "estaquia" in source_summary(docs, "propagation")
    assert "luminosidade" not in source_summary(docs, "propagation")
    assert source_summary(docs, "toxicity") is None
