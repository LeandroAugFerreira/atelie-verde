import hashlib
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.assistant_emotions import reaction
from app.assistant_state import Memory
from app.database import SessionLocal
from app.models import Appointment, Project
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def test_official_assets_have_alpha_shared_canvas_and_safe_margins():
    directory = ROOT / "frontend/public/rafinha/official"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["poses"]) == 12
    assert (
        hashlib.sha256((ROOT / manifest["source"]).read_bytes()).hexdigest()
        == manifest["source_sha256"]
    )
    for pose in manifest["poses"]:
        image = Image.open(directory / pose["file"]).convert("RGBA")
        assert image.size == (320, 400) and pose["mouth"] == [0.5, 0.525]
        alpha = image.getchannel("A")
        assert alpha.getextrema() == (0, 255)
        left, top, right, bottom = alpha.getbbox()
        assert 0 < left < right < 320 and 0 < top < bottom < 400
    assert sum(file.stat().st_size for file in directory.glob("*.webp")) < 2_000_000


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Olá", "greeting"),
        ("Boa noite", "sleepy"),
        ("Rafinha, você é muito fofo", "shy"),
        ("Vou jogar água sanitária na planta", "serious"),
        ("Minha planta morreu", "sad"),
        ("Olha como ela floresceu", "delighted"),
        ("Orçamento aprovado", "celebrating"),
        ("Eu rego a suculenta cinco vezes por dia", "serious"),
    ],
)
def test_official_reactions_match_the_situation(message, expected):
    assert reaction(message)["final"] == expected


def test_recovery_uses_the_previous_emotional_state():
    assert (
        reaction("Ela se recuperou!", memory=Memory(last_expression="concerned"))["final"]
        == "celebrating"
    )
    plant = SimpleNamespace(watering="Baixa")
    assert reaction("Não reguei hoje", {"species": [plant]})["final"] == "relieved"


@pytest.mark.parametrize(
    "text",
    [
        "Minha planta não morreu",
        "Não vou colocar água sanitária na planta",
        "Não rego a suculenta cinco vezes por dia",
    ],
)
def test_denial_does_not_trigger_loss_or_a_harsh_reaction(text):
    assert reaction(text)["initial"] not in {"sad", "angry", "serious", "surprised"}


def ask(client, headers, text):
    cid = client.post("/api/assistant/conversations", headers=headers).json()["id"]
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=headers,
        json={"text": text, "request_id": str(uuid4())},
    )
    assert response.status_code == 200
    return response.json()


def test_stock_summary_and_minimum_permissions(client, auth):
    summary = ask(client, auth["one"], "Quantas plantas temos em estoque?")
    assert "5 unidade" in summary["text"] and "1 produto" in summary["text"]
    denied = ask(client, auth["one"], "Quais produtos estão abaixo do estoque mínimo?")
    admin = ask(client, auth["admin"], "Quais produtos estão abaixo do estoque mínimo?")
    assert "administrador" in denied["text"] and "Vaso" not in denied["text"]
    assert "Vaso" in admin["text"] and "mínimo 2" in admin["text"]


def test_project_query_preserves_scoped_results_and_detects_real_delays(client, auth, monkeypatch):
    from app import assistant_engine

    monkeypatch.setattr(assistant_engine, "today", lambda: date(2026, 10, 7))
    with SessionLocal() as db:
        for id, owner, name, end, status in [
            (1, 2, "Jardim próprio", "2026-10-06", "Execução"),
            (2, 3, "Projeto privado", "2026-10-05", "Execução"),
            (3, 2, "Projeto concluído", "2026-10-01", "Finalizado"),
        ]:
            db.add(
                Project(
                    id=id,
                    customer_id=owner,
                    name=name,
                    address="Privado",
                    area=10,
                    budget_cents=1000,
                    start_date="2026-10-01",
                    end_date=end,
                    status=status,
                )
            )
        db.commit()
    own = ask(client, auth["one"], "Qual projeto está atrasado?")
    assert (
        "Jardim próprio" in own["text"]
        and "Projeto privado" not in own["text"]
        and "Projeto concluído" not in own["text"]
    )
    admin = ask(client, auth["admin"], "Quais projetos estão em andamento?")
    assert "Projeto privado" in admin["text"]


def test_schedule_today_does_not_include_tomorrow_or_another_customer(client, auth, monkeypatch):
    from app import assistant_engine

    monkeypatch.setattr(assistant_engine, "today", lambda: date(2026, 10, 7))
    with SessionLocal() as db:
        for id, owner, title, day in [
            (1, 2, "Minha visita hoje", "2026-10-07"),
            (2, 2, "Minha visita amanhã", "2026-10-08"),
            (3, 3, "Visita privada", "2026-10-07"),
        ]:
            db.add(
                Appointment(
                    id=id,
                    customer_id=owner,
                    service_id=1,
                    title=title,
                    date=day,
                    start_time="10:00",
                    end_time="11:00",
                    responsible="Equipe",
                    address="Privado",
                )
            )
        db.commit()
    result = ask(client, auth["one"], "Tenho serviço marcado hoje?")
    assert (
        "Minha visita hoje" in result["text"]
        and "amanhã" not in result["text"]
        and "Visita privada" not in result["text"]
    )
