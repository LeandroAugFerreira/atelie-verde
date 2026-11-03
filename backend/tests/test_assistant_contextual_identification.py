"""Language and dialogue regressions across clues, typos and unhelpful models."""

from uuid import uuid4

import pytest
from app import assistant_engine as engine
from app.assistant_botany import follows_reference, reference_for, substantive_reply
from app.assistant_language import reported_plants
from app.assistant_observations import reported_group
from app.assistant_state import Memory, SemanticReply, advance, intent_of
from app.assistant_text import understood_text
from app.assistant_web_search import identification_clues


@pytest.mark.parametrize("word", ["suculent5a", "succulenta", "suculenra", "suculentaa"])
def test_generic_typo_is_understood_without_becoming_a_species(word):
    text = f"Gostaria de informações de como cuidar de uma {word}, é igual cactos?"
    assert reported_group(text) == "suculenta"
    assert reported_plants(text) == []
    memory = advance(None, text, {"species": []})
    assert memory.slots["plant_group"] == "suculenta"
    assert memory.plant_name is None and memory.species_id is None


@pytest.mark.parametrize(
    "name", ["Crassula ovata", "Calathea orbifolia", "cacto-colunar", "Echeveria", "suculentinha"]
)
def test_generic_spelling_normalization_never_changes_botanical_names(name):
    assert understood_text(name) == name


@pytest.mark.parametrize("name", ["suculent5a", "parece", "me diga"])
def test_old_phantom_identities_are_repaired_without_erasing_care(name):
    memory = Memory(
        plant_name=name,
        slots={
            "plant_name": name,
            "watering": "relato de rega excessiva",
            "plant_group": "suculenta",
        },
    )
    after = advance(memory.model_dump(), "me diga", {"species": []})
    assert after.plant_name is None and "plant_name" not in after.slots
    assert after.slots["watering"] == memory.slots["watering"]


def test_memory_repair_preserves_long_reported_names():
    memory = Memory(plant_name="espada de São Jorge anã", slots={"container": "vaso"})
    after = advance(memory.model_dump(), "Como regar?", {"species": []})
    assert after.plant_name == memory.plant_name and after.slots["container"] == "vaso"


@pytest.mark.parametrize(
    "text",
    [
        "a que eu ganhei parece com a orelha do sherek",
        "a que comprei lembra um rabo de burro",
        "minha planta parece uma árvore de jade",
    ],
)
def test_appearance_after_acquisition_is_not_a_name(text):
    assert reported_plants(text) == []
    memory = advance(Memory(slots={"plant_group": "suculenta"}).model_dump(), text, {"species": []})
    assert memory.plant_name is None
    assert memory.slots["description"]
    assert memory.intent == "identification"
    assert identification_clues(memory, {"_question": text})


@pytest.mark.parametrize(
    "text", ["vc sabe qual é", "você sabe qual é?", "me diga", "me diz", "pode me dizer?"]
)
def test_short_request_resolves_the_previous_identification_goal(text):
    before = Memory(
        intent="plant_care",
        slots={"plant_group": "suculenta", "description": "parece uma orelha do Shrek"},
    )
    assert reported_plants(text, allow_bare=True) == []
    assert intent_of(text, before) == "identification"
    assert identification_clues(before, {"_question": text})
    assert advance(before.model_dump(), text, {"species": []}).slots == before.slots


@pytest.mark.parametrize(
    "text",
    [
        "Sim, parece com a orelha do sherek.",
        "Sim, eu posso ajudar você a determinar qual é o nome da planta.",
        "Claro, posso identificar a planta.",
    ],
)
def test_capability_promises_and_echoes_do_not_count_as_answers(text):
    question = "parece com a orelha do sherek" if "parece" in text else "me diga"
    assert not substantive_reply(text, question)


@pytest.mark.parametrize(
    "description,label",
    [
        ("parece a orelha do Sherek", "Crassula ovata 'Gollum'"),
        ("lembra uma planta-jade", "Crassula ovata"),
        ("conhecida como rabo-de-burro", "Sedum morganianum"),
    ],
)
def test_reference_library_is_shared_across_aliases(description, label):
    memory = Memory(intent="identification", slots={"description": description})
    assert reference_for(memory, "me diga")["label"] == label


@pytest.mark.parametrize(
    "text",
    [
        "Sim, a espécie que você descreveu é Crassula ovata 'Gollum'. A identidade pode ser confirmada pela descrição.",
        "Uma hipótese é Crassula ovata 'Gollum', da família Crassula ovata.",
        "Com certeza é Crassula ovata 'Gollum'. Essa é a hipótese.",
    ],
)
def test_uncertainty_words_do_not_excuse_a_confirmed_or_incorrect_identity(text):
    reference = reference_for(Memory(intent="identification"), "Parece a orelha do Shrek")
    assert not follows_reference(text, reference)


@pytest.mark.parametrize(
    "description",
    [
        "não parece a orelha do Shrek",
        "lembra uma orelha comum",
        "parece a orelha do Shrek ou um rabo-de-burro",
        "folhas redondas",
    ],
)
def test_negated_generic_and_ambiguous_clues_do_not_select_a_reference(description):
    memory = Memory(intent="identification", slots={"description": description})
    assert reference_for(memory, "me diga") is None


def send(client, headers, cid, text):
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=headers,
        json={"text": text, "request_id": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_entire_reported_conversation_with_bad_local_model(client, auth, monkeypatch):
    monkeypatch.setattr(
        engine,
        "generate_ai",
        lambda *args: SemanticReply(
            text="Sim, posso ajudar você a determinar qual é o nome da planta. Seu espaço parece cactíneo."
        ),
    )
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    send(client, auth["one"], cid, "Olá")
    first = send(
        client,
        auth["one"],
        cid,
        "Eu gostaria de informações de como cuidar de uma suculent5a, é igual cactos?",
    )
    assert "Não exatamente" in first["text"] and "frequência" in first["text"]
    assert not first["meta"]["searched_web"] and not first["meta"]["research"]["needed"]
    for text in ["a que eu ganhei parece com a orelha do sherek", "vc sabe qual é", "me diga"]:
        reply = send(client, auth["one"], cid, text)
        assert "Crassula ovata 'Gollum'" in reply["text"] and "não confirma" in reply["text"]
        assert (
            "cactíneo" not in reply["text"]
            and "posso ajudar você a determinar" not in reply["text"]
        )
        assert reply["sources"] and not reply["meta"]["searched_web"]
    state = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()["memory"]
    assert state["plant_name"] is None and state["species_id"] is None
    assert state["slots"]["plant_group"] == "suculenta"
    assert "sherek" in state["slots"]["description"]
    assert state["identity_hypothesis"]["label"] == "Crassula ovata 'Gollum'"
    assert state["identity_hypothesis"]["origin"] == "internal"
    later = send(client, auth["one"], cid, "Eu não deixei ela no sol e reguei muito")
    assert not later["meta"]["research"]["needed"]
    assert "nome da planta" not in later["text"]
    assert "enquanto o substrato estiver muito molhado" in later["text"]


@pytest.mark.parametrize(
    "introduction",
    [
        "É uma suculenta, parece a orelha do Shrek",
        "Tenho uma Lavanda",
        "Tenho uma samambaia",
    ],
)
def test_excess_watering_uses_verified_guidance_despite_a_misleading_model(
    client, auth, monkeypatch, introduction
):
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    send(client, auth["one"], cid, introduction)
    monkeypatch.setattr(
        engine,
        "generate_ai",
        lambda *args: pytest.fail("Reported excessive water is covered internally"),
    )
    reply = send(client, auth["one"], cid, "Não deixei ela no sol e reguei muito")
    assert "enquanto o substrato estiver muito molhado" in reply["text"]
    assert "ausência de sol direto" in reply["text"]
    assert not reply["meta"]["research"]["needed"] and reply["sources"]


def test_already_reported_wet_soil_is_not_asked_again(client, auth):
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    reply = send(client, auth["one"], cid, "A terra da minha planta está encharcada")
    assert "Como está o substrato agora?" not in reply["text"]
    assert "costuma continuar úmido" not in reply["text"]


def test_comparison_does_not_turn_into_catalogue_recommendations(client, auth):
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    reply = send(client, auth["one"], cid, "Qual a diferença entre cactos e suculentas?")
    assert "Não exatamente" in reply["text"] and "Cactaceae" in reply["text"]
    assert not reply["actions"] and not reply["meta"]["research"]["needed"]
