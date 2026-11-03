"""Care reports must remain useful even when a species is still unidentified."""

from uuid import uuid4

import pytest
from app import assistant_engine as engine
from app.assistant_emotions import reaction
from app.assistant_language import field_values, missed_watering, reported_plants
from app.assistant_observations import care_observations
from app.assistant_state import Memory, advance, intent_of


@pytest.mark.parametrize(
    "text",
    [
        "Eu não deixei ela no sol e reguei muito",
        "Reguei a planta demais, o que faço?",
        "Molhei muito a minha samambaia",
        "Eu rego em excesso",
    ],
)
def test_excess_is_an_action_report_independent_of_plant_name(text):
    assert care_observations(text)["excess_watering"]
    assert intent_of(text, Memory()) == "problem"
    assert reaction(text)["final"] == "serious"


@pytest.mark.parametrize(
    "text",
    [
        "Não reguei demais",
        "Nunca molhei muito",
        "Não esqueci de regar",
        "A terra não está encharcada",
        "Devo regar muito?",
        "Como regar em excesso afeta a planta?",
    ],
)
def test_negations_and_questions_are_not_reported_water_damage(text):
    assert not care_observations(text).get("excess_watering")
    assert not care_observations(text).get("wet_soil")
    assert not missed_watering(text)


@pytest.mark.parametrize("text", ["A terra está encharcada", "O substrato está muito molhado"])
def test_wet_soil_is_recorded_without_diagnosing_rotten_roots(text):
    assert field_values(text)["soil_moisture"] == "encharcado"
    assert intent_of(text, Memory()) == "problem"


def test_direct_sun_and_low_light_are_different_reports():
    values = field_values("Não deixei a planta no sol direto e reguei muito")
    assert values["lighting"] == "relato de ausência de sol direto"
    assert values["watering"] == "relato de rega excessiva"
    assert not care_observations("Não deixei a planta no sol").get("low_light")
    assert care_observations("Ela fica com pouca luz")["low_light"]
    assert not care_observations("Ela não fica com pouca luz").get("low_light")


def test_group_and_appearance_are_not_a_confirmed_species():
    text = "eu só sei que é uma suculenta, parece com a orelha do Sherek"
    assert reported_plants(text) == []
    state = advance(None, text, {"species": []})
    assert state.plant_name is None and state.species_id is None
    assert state.slots["plant_group"] == "suculenta"
    assert "Sherek" in state.slots["description"]
    assert "plant_name" in state.known_unknowns
    again = advance(state.model_dump(), "Minha suculenta fica em vaso", {"species": []})
    assert again.slots["description"] == state.slots["description"]
    assert again.slots["container"] == "vaso"


def test_group_migrates_old_sessions_and_clears_a_different_named_plant():
    old = Memory(plant_name="suculenta", slots={"plant_name": "suculenta", "container": "vaso"})
    migrated = advance(old.model_dump(), "reguei muito", {"species": []})
    assert migrated.plant_name is None and migrated.slots["plant_group"] == "suculenta"
    assert migrated.slots["container"] == "vaso" and migrated.intent == "problem"
    named = Memory(plant_name="roseira", species_id=9, slots={"environment": "externo"})
    changed = advance(named.model_dump(), "Tenho uma suculenta", {"species": []})
    assert changed.plant_name is None and changed.species_id is None
    assert "environment" not in changed.slots


def send(client, headers, cid, text):
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=headers,
        json={"text": text, "request_id": str(uuid4())},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize(
    "introduction",
    [
        "eu só sei que é uma suculenta, parece com a orelha do Sherek",
        "Tenho uma Lavanda",
        "Tenho uma samambaia",
    ],
)
def test_use_care_reports_before_identification_or_external_search(
    client, auth, monkeypatch, introduction
):
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    send(client, auth["one"], cid, introduction)
    monkeypatch.setattr(
        engine, "research", lambda *args: pytest.fail("Care reports already available")
    )
    reply = send(client, auth["one"], cid, "eu não deixei ela no sol e reguei muito")
    assert reply["meta"]["source_type"] == "care"
    assert reply["expression"] == "serious"
    assert "umidade" in reply["text"] and "escoa" in reply["text"]
    assert "dentro ou fora" not in reply["text"] and "nome da planta" not in reply["text"]
    assert not reply["meta"]["research"]["needed"]
    state = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()["memory"]
    assert state["intent"] == "problem" and state["slots"]["watering"] == "relato de rega excessiva"
    assert "ausência de sol direto" in state["slots"]["lighting"]


def test_switch_to_an_unidentified_group_never_reuses_old_catalogue_species(
    client, auth, monkeypatch
):
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    send(client, auth["one"], cid, "Tenho uma Lavanda")
    group = send(client, auth["one"], cid, "Tenho uma suculenta, parece uma orelha")
    assert "Lavanda" not in group["text"]
    monkeypatch.setattr(
        engine, "research", lambda *args: pytest.fail("No need to identify the group first")
    )
    send(client, auth["one"], cid, "A terra está encharcada depois de regar muito")
    state = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()["memory"]
    assert state["plant_name"] is None and state["species_id"] is None
    assert state["slots"]["plant_group"] == "suculenta"
