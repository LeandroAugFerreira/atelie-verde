"""A welcome cannot replace a response to a new topic or supplied information."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from app import assistant_engine as engine
from app.assistant_dialogue import greeting_only, replay_reason
from app.assistant_state import Memory, SemanticReply, merge_semantics

WELCOME = "Oi! Que bom ter você por aqui 🌿 Como posso ajudar com seu espaço verde?"


@pytest.mark.parametrize(
    "text",
    [
        WELCOME,
        "Olá! Como posso ajudar hoje?",
        "Boa tarde. Estou aqui para ajudar você.",
        "Seja bem-vindo ao Ateliê Verde! Como podemos ajudar com seu jardim?",
    ],
)
def test_greetings_are_detected_even_when_wording_changes(text):
    assert greeting_only(text)
    assert replay_reason(
        text, "tenho uma roseira", Memory(intent="plant_care"), Memory(intent="greeting"), []
    )


@pytest.mark.parametrize(
    "text",
    [
        "Oi! Você tem uma roseira. Quer cuidados gerais ou ajuda com algum problema?",
        "Claro! Para a Lavanda, confira a drenagem e a luminosidade.",
        "Olá! A poda está cadastrada como um serviço presencial.",
    ],
)
def test_friendly_intro_with_a_substantive_response_is_allowed(text):
    assert not greeting_only(text)
    assert (
        replay_reason(
            text,
            "tenho uma roseira",
            Memory(intent="plant_care", plant_name="roseira"),
            Memory(),
            [],
        )
        is None
    )


def test_repeated_greetings_with_a_meaningful_tail_are_not_discarded():
    text = "Oi que bom ter você por aqui " * 40
    assert greeting_only(text)
    assert not greeting_only(text + "A roseira precisa de cuidados específicos.")


@pytest.mark.parametrize(
    "text",
    [
        "Oi! Tenho uma roseira. Como posso ajudar com seu espaço verde? 🌿",
        "Você tem uma roseira. Como posso ajudar hoje?",
        "Claro, você tem uma roseira.",
        "Ganhei uma roseira. Posso ajudar com o jardim.",
    ],
)
def test_subject_echo_and_ownership_inversion_are_not_substantive(text):
    assert replay_reason(
        text, "tenho uma roseira", Memory(intent="plant_care", plant_name="roseira"), Memory(), []
    )


@pytest.mark.parametrize(
    "question,intent,slots",
    [
        ("Ela fica dentro de casa", "plant_care", {"environment": "interno"}),
        ("Minha planta está amarela", "problem", {"symptoms": "amarela"}),
        ("Quanto custa o vaso?", "price", {}),
        ("E a luminosidade?", "lighting", {}),
    ],
)
def test_replay_guard_applies_to_changes_beyond_a_plant_problem(question, intent, slots):
    text = "Vamos conferir as condições que você contou antes de escolher o cuidado."
    history = [SimpleNamespace(role="assistant", status="completed", text=text)]
    assert (
        replay_reason(
            text, question, Memory(intent=intent, slots=slots), Memory(intent="general"), history
        )
        == "repeated_after_new_information"
    )


def test_explicit_repeat_and_same_factual_subject_remain_allowed():
    text = "O Vaso custa R$ 10,00."
    history = [SimpleNamespace(role="assistant", status="completed", text=text)]
    current = Memory(intent="price")
    assert (
        replay_reason(text, "Repita, por favor", current, Memory(intent="general"), history) is None
    )
    assert replay_reason(text, "Qual o valor do vaso?", current, current, history) is None
    assert replay_reason(WELCOME, "Olá", Memory(intent="greeting"), current, history) is None


def test_answering_the_pending_care_goal_must_not_replay_its_question():
    text = "Você tem uma roseira. Em que gostaria de ajuda?"
    history = [SimpleNamespace(role="assistant", status="completed", text=text)]
    previous = Memory(intent="plant_care", plant_name="roseira", pending_field="care_goal")
    current = previous.model_copy(
        update={"slots": {"care_goal": "Quero cuidados gerais"}, "pending_field": None}
    )
    assert (
        replay_reason(text, "Quero cuidados gerais", current, previous, history)
        == "repeated_after_new_information"
    )


@pytest.mark.parametrize(
    "field,value,text",
    [
        (
            "care_goal",
            "cuidados gerais",
            "Você quer cuidados gerais ou poda? Se quiser, posso ajudar.",
        ),
        ("environment", "interno", "Ela fica dentro ou fora de casa? Isso ajuda a orientar."),
        ("plant_name", "roseira", "Qual é o nome da planta? Pode me contar."),
        (
            "watering",
            "a cada semana",
            "Com que frequência você costuma regar? Vou considerar isso.",
        ),
    ],
)
def test_question_before_a_final_sentence_still_respects_known_answers(field, value, text):
    memory = Memory(slots={field: value})
    assert not merge_semantics(memory, SemanticReply(text=text))


def send(client, auth, cid, text):
    response = client.post(
        f"/api/assistant/conversations/{cid}/messages",
        headers=auth["one"],
        json={"text": text, "request_id": str(uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("plant", ["roseira", "Lavanda", "begônia", "samambaia"])
def test_plant_introduction_and_repeated_introduction_never_replay_welcome(
    client, auth, monkeypatch, plant
):
    monkeypatch.setattr(engine, "generate_ai", lambda *args: SemanticReply(text=WELCOME))
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    send(client, auth, cid, "Olá")
    for _ in range(2):
        answer = send(client, auth, cid, "tenho uma " + plant)
        assert not greeting_only(answer["text"])
        assert plant.lower() in answer["text"].lower()
        assert "cuidados gerais" in answer["text"]
        assert "nome da planta" not in answer["text"]
        assert answer["meta"]["fallback"] and not answer["meta"]["research"]["needed"]
    data = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()
    assert data["memory"]["plant_name"].lower() == plant.lower()
    assert data["memory"]["pending_field"] == "care_goal"
    cared = send(client, auth, cid, "Quero cuidados gerais")
    assert not greeting_only(cared["text"])
    assert cared["meta"]["fallback"]


def test_short_answer_does_not_replay_previous_care_response(client, auth, monkeypatch):
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    previous = send(client, auth, cid, "Tenho uma Lavanda")
    monkeypatch.setattr(engine, "generate_ai", lambda *args: SemanticReply(text=previous["text"]))
    answer = send(client, auth, cid, "Ela fica dentro de casa")
    assert answer["text"] != previous["text"]
    assert "interno" in answer["text"] and "nome da planta" not in answer["text"]


def test_a_valid_repeated_introduction_keeps_the_unanswered_goal(client, auth, monkeypatch):
    monkeypatch.setattr(
        engine,
        "generate_ai",
        lambda *args: SemanticReply(text="Você tem uma roseira. Em que gostaria de ajuda?"),
    )
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    for _ in range(2):
        send(client, auth, cid, "tenho uma roseira")
        memory = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()[
            "memory"
        ]
        assert memory["pending_field"] == "care_goal"
    send(client, auth, cid, "Quero cuidados gerais")
    memory = client.get(f"/api/assistant/conversations/{cid}", headers=auth["one"]).json()["memory"]
    assert memory["slots"]["care_goal"] == "Quero cuidados gerais"
    assert memory["plant_name"] == "roseira"


def test_owning_the_users_plant_is_rejected_in_the_real_message_flow(client, auth, monkeypatch):
    monkeypatch.setattr(
        engine,
        "generate_ai",
        lambda *args: SemanticReply(
            text="Oi! Tenho uma roseira. Como posso ajudar com seu espaço verde?"
        ),
    )
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    for _ in range(2):
        answer = send(client, auth, cid, "tenho uma roseira")
        assert "cuidados gerais" in answer["text"]
        assert "Tenho uma roseira" not in answer["text"]
        assert answer["meta"]["fallback"]
    continued = send(client, auth, cid, "Como regar a minha roseira?")
    assert "Tenho uma roseira" not in continued["text"] and continued["meta"]["fallback"]


def test_welcome_from_research_synthesis_is_also_rejected(client, auth, monkeypatch):
    def researched(*args):
        reply = SemanticReply(text=WELCOME)
        reply._searched_web = True
        return reply, {"status": "found", "confidence": "medium", "providers": []}

    monkeypatch.setattr(engine, "research_reply", researched)
    cid = client.post("/api/assistant/conversations", headers=auth["one"]).json()["id"]
    answer = send(client, auth, cid, "Como cuidar da minha roseira?")
    assert not greeting_only(answer["text"])
    assert "roseira" in answer["text"].lower() and answer["meta"]["fallback"]
