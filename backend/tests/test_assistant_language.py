"""Regression families: phrasing, grounded names, ambiguity and relative answers."""

from types import SimpleNamespace

import pytest
from app.assistant_emotions import reaction
from app.assistant_knowledge import grounded_text
from app.assistant_language import catalogue_mentions, field_values, reported_plants
from app.assistant_state import Memory, SemanticReply, advance, intent_of, merge_semantics


@pytest.mark.parametrize(
    "plant",
    ["roseira", "Calathea orbifolia", "planta-jade", "lírio-da-paz", "zamioculca", "cacto-colunar"],
)
@pytest.mark.parametrize(
    "template",
    [
        "tenho uma {p} e não sei como cuidar",
        "minha {p} está murchando",
        "ganhei uma {p}, como cuidar?",
        "quero cuidar da minha {p}",
        "não sei cuidar de {p}",
        "é {p}",
        "tenho duas {p}",
        "tenho uma {p} com folhas amarelas",
        "oi, tenho uma {p} no quintal",
        "minha {p} fica fora e não sei cuidar",
        "como regar uma {p}?",
        "quero cuidados com {p}",
        "Tenho uma planta, uma {p}",
        "Minha planta: uma {p}",
    ],
)
def test_names_survive_different_sentence_structures(plant, template):
    assert reported_plants(template.format(p=plant)) == [plant]


@pytest.mark.parametrize(
    "pronoun", ["dela", "dele", "delas", "deles", "dessa", "desse", "desta", "deste"]
)
def test_pronouns_do_not_split_into_phantom_plant_names(pronoun):
    assert reported_plants(f"não sei cuidar {pronoun}") == []
    assert reported_plants(f"ganhei uma roseira e não sei cuidar {pronoun}") == ["roseira"]


def test_function_words_do_not_match_prefixes_of_other_words():
    assert reported_plants("tenho uma roseira e umidade alta") == ["roseira"]


@pytest.mark.parametrize(
    "text",
    [
        "gostaria de saber qual é a melhor planta para apartamento",
        "qual é a espécie ideal para dentro de casa?",
        "Quais plantas combinam com meu espaço?",
        "Indique plantas para apartamento",
    ],
)
def test_recommendation_is_not_a_reported_plant(text):
    assert reported_plants(text, allow_bare=True) == []
    assert intent_of(text, Memory()) == "recommendation"


@pytest.mark.parametrize(
    "text,plant",
    [
        (
            "esqueci de regar a minha planta durante uma semana, o que eu faço, é uma orquidea",
            "orquidea",
        ),
        ("esqueci de molhar minha violeta por cinco dias", "violeta"),
        ("não reguei minha roseira há uma semana", "roseira"),
        ("minha planta ficou sem regar, é uma begônia", "begônia"),
    ],
)
def test_missed_watering_has_one_identity_and_a_concerned_reaction(text, plant):
    assert reported_plants(text) == [plant]
    assert intent_of(text, Memory()) == "problem"
    assert reaction(text)["final"] == "concerned"


def test_mixed_report_and_question_keeps_the_declared_watering_history():
    text = "esqueci de regar a minha planta durante uma semana, o que eu faço, é uma orquidea"
    assert "uma semana" in field_values(text)["watering"]


def test_plant_description_completes_the_same_session_without_claiming_a_cultivar():
    before = Memory(
        intent="plant_care",
        plant_name="roseira",
        slots={"plant_name": "roseira"},
        pending_field="environment",
        asked=["environment"],
        research_key="source-key",
    )
    text = "se trata de rosa vermelha, plantada em vaso e fica no meu apartamento"
    after = advance(before.model_dump(), text, {"species": []})
    assert after.plant_name == "roseira" and after.research_key == "source-key"
    assert after.slots["environment"] == "interno" and after.slots["container"] == "vaso"
    assert "rosa vermelha" in after.slots["flower_color"]
    assert after.last_answered == "environment"


def test_natural_sun_question_preserves_the_pending_field_for_a_short_answer():
    memory = Memory(plant_name="roseira", intent="plant_care", slots={"plant_name": "roseira"})
    assert merge_semantics(
        memory, SemanticReply(text="Ela recebe algumas horas de sol direto por dia?")
    )
    assert memory.pending_field == "lighting"
    after = advance(memory.model_dump(), "Sim", {"species": []})
    assert after.slots["lighting"] == "sol direto" and after.pending_field is None


def test_yes_does_not_choose_between_lighting_alternatives():
    memory = Memory(plant_name="roseira", intent="plant_care", slots={"plant_name": "roseira"})
    assert merge_semantics(
        memory, SemanticReply(text="O local recebe sol direto, claridade indireta ou pouca luz?")
    )
    after = advance(memory.model_dump(), "Sim", {"species": []})
    assert "lighting" not in after.slots


@pytest.mark.parametrize("text,accepted", [
    ("Custa R$24,90.", True), ("Custa R$ 24,90; temos esse item.", True),
    ("Custa R$ 25,90.", False), ("Custa R$ 24.", False), ("Custa R$ -24,90.", False),
])
def test_natural_price_formatting_does_not_change_registered_amounts(text, accepted):
    facts = {"products": [SimpleNamespace(price_cents=2490)], "services": []}
    assert grounded_text(text, facts) is accepted


def test_multiple_reported_names_with_a_pronoun_have_no_extra_entity():
    assert reported_plants(
        "eu ganhei uma roseira e uma espada de são jorge e não sei cuidar dela"
    ) == ["roseira", "espada de são jorge"]


@pytest.mark.parametrize(
    "text",
    [
        "Tenho uma dúvida",
        "Me ajuda",
        "Meu gato comeu folhas da planta",
        "É bonita",
        "Minha planta está murchando",
        "Tenho um orçamento",
        "Não tenho uma roseira",
    ],
)
def test_non_botanical_phrases_do_not_become_names(text):
    assert not reported_plants(text, allow_bare=True)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Minha planta não fica dentro, fica fora", {"environment": "externo"}),
        ("Não recebe sol direto, só luz indireta", {"lighting": "claridade indireta"}),
        ("Ela precisa de sol direto?", {}),
        ("Ela deve ficar fora?", {}),
        ("Fica fora, como cuidar?", {"environment": "externo"}),
    ],
)
def test_assertions_and_questions_have_different_effects(text, expected):
    assert field_values(text) == expected


@pytest.mark.parametrize("text", ["Não sei cuidar", "Não sei como regar", "Não lembro os cuidados"])
def test_unknown_care_does_not_mark_the_identity_unknown(text):
    before = Memory(intent="plant_care", pending_field="plant_name", asked=["plant_name"])
    after = advance(before.model_dump(), text, {"species": []})
    assert after.pending_field == "plant_name" and "plant_name" not in after.known_unknowns
    assert after.last_answered is None


@pytest.mark.parametrize(
    "text,intent,pose",
    [
        ("Obrigado, mas minha planta está murchando", "problem", "concerned"),
        ("Floresceu pela primeira vez, mas tem manchas", "problem", "concerned"),
        ("Não está murchando, mas tem folhas amarelas", "problem", "concerned"),
        ("Antes estava amarela, mas agora está verde", "casual", "relieved"),
        ("Não tem manchas", "plant_care", "explaining"),
    ],
)
def test_symptom_negation_and_compound_messages(text, intent, pose):
    assert intent_of(text, Memory(intent="plant_care")) == intent
    assert reaction(text)["final"] == pose


def test_catalogue_aliases_are_grounded_and_longest_compound_wins():
    rows = [
        SimpleNamespace(id=1, name="Rosa", scientific_name="Rosa"),
        SimpleNamespace(id=2, name="Rosa-do-deserto", scientific_name="Adenium obesum"),
        SimpleNamespace(id=3, name="Lírio-da-paz", scientific_name="Spathiphyllum wallisii"),
        SimpleNamespace(id=4, name="Lavanda", scientific_name="Lavandula dentata"),
    ]
    for text, ids in [
        ("rosas do deserto", [2]),
        ("lirios da paz", [3]),
        ("Tenho lavandas", [4]),
        ("Adenium obesum", [2]),
        ("Não tenho lavanda, tenho rosa-do-deserto", [2]),
        ("lavandaria", []),
        ("cuidar de rosa e lavanda", [1, 4]),
    ]:
        assert [row.id for row in catalogue_mentions(text, rows)] == ids
