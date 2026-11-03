"""Typed session memory and a small, extensible dialogue policy for offline continuity."""

import re

from pydantic import BaseModel, Field, PrivateAttr

from .assistant_language import (
    catalogue_mentions,
    current_symptoms,
    explicit_plant,
    field_values,
    identification_request,
    is_question,
    missed_watering,
    name_key,
    recommendation_request,
    reported_plants,
    unknown_fields,
)
from .assistant_observations import GROUPS, care_observations, reported_group
from .business import normalized

FIELDS = (
    "plant_selection",
    "product_name",
    "plant_name",
    "photo",
    "leaf_size",
    "leaf_shape",
    "flowers",
    "environment",
    "lighting",
    "watering",
    "symptoms",
    "soil_moisture",
    "container",
    "flower_color",
    "care_goal",
    "plant_group",
    "description",
)
FIELD_LABELS = {
    "plant_selection": "planta escolhida",
    "environment": "ambiente",
    "lighting": "luminosidade",
    "watering": "rotina de rega",
    "leaf_size": "tamanho das folhas",
    "leaf_shape": "formato das folhas",
    "flowers": "flores",
    "symptoms": "sintomas",
    "soil_moisture": "umidade do substrato",
    "photo": "foto",
    "plant_name": "nome da planta",
    "container": "local de plantio",
    "flower_color": "cor das flores",
}
COMMERCIAL = {
    "product",
    "price",
    "stock",
    "service",
    "quote",
    "project",
    "company",
    "customers",
    "schedule",
    "orders",
    "identity",
}
QUESTIONS = {
    "care_goal": "Você quer ajuda com cuidados gerais, poda, adubação, floração ou percebeu algum problema?",
    "plant_selection": "Qual dessas plantas você quer cuidar primeiro?",
    "product_name": "Qual produto você quer consultar? O nome ou o SKU já ajuda a localizar os dados da loja.",
    "plant_name": "Você sabe o nome da planta? Se não souber, podemos seguir pelas características.",
    "photo": "Pode enviar uma foto como referência? A identificação deste atendimento segue pela descrição, sem análise automática da imagem. Se preferir, me conte como são as folhas.",
    "leaf_size": "As folhas são grandes, pequenas ou de tamanho médio?",
    "leaf_shape": "As folhas são lisas, recortadas ou serrilhadas?",
    "flowers": "Ela tem flores?",
    "environment": "Ela fica dentro ou fora de casa?",
    "lighting": "O local recebe sol direto, claridade indireta ou pouca luz?",
    "watering": "Com que frequência você costuma regar?",
    "symptoms": "Qual mudança você percebeu na planta?",
    "soil_moisture": "O substrato costuma continuar úmido por vários dias?",
}


class Memory(BaseModel):
    version: int = 1
    intent: str = "general"
    phase: str = "starting"
    species_id: int | None = None
    product_id: int | None = None
    plant_name: str | None = None
    plant_choices: list[str] = Field(default_factory=list)
    slots: dict[str, str] = Field(default_factory=dict)
    known_unknowns: list[str] = Field(default_factory=list)
    asked: list[str] = Field(default_factory=list)
    pending_field: str | None = None
    pending_question: str | None = None
    last_answered: str | None = None
    research_key: str | None = None
    research_context: dict = Field(default_factory=dict)
    identity_hypothesis: dict = Field(default_factory=dict)
    last_expression: str = "neutral"
    turn: int = 0


class SemanticReply(BaseModel):
    _provider: str = PrivateAttr(default="local")
    _sources: list = PrivateAttr(default_factory=list)
    _images: list = PrivateAttr(default_factory=list)
    _searched_web: bool = PrivateAttr(default=False)
    _hypothesis: dict = PrivateAttr(default_factory=dict)
    model_config = {"extra": "ignore"}
    text: str = Field(min_length=1, max_length=4000)
    intent: str | None = Field(default=None, max_length=40)
    updates: dict[str, str] = Field(default_factory=dict)
    known_unknowns: list[str] = Field(default_factory=list, max_length=10)
    question_field: str | None = None
    initial_expression: str | None = None
    final_expression: str | None = None


def declared_plant(text):
    """Keep the compatibility entry point backed by the shared conservative parser."""
    return explicit_plant(text, allow_bare=False)


def intent_of(text, memory):
    q = normalized(text).strip(" .!?")
    if q in {"quem e voce", "quem e vc", "quem e o rafinha", "o que voce faz", "o que vc faz"}:
        return "identity"
    if re.fullmatch(
        r"(?:(?:meu|minha|o|a)\s+)?(?:projeto finalizado|orcamento aprovado|servico concluido)", q
    ):
        return "casual"
    if re.search(
        r"(?:nao esta(?: mais)?|ja nao esta)\s+(?:murch|amarel|secando)", q
    ) and not current_symptoms(text):
        return "casual"
    if not current_symptoms(text) and re.search(
        r"\b(?:agora esta verde|melhorou|se recuperou)\b", q
    ):
        return "casual"
    rules = [
        (
            "customers",
            (
                "meus clientes",
                "mostrar clientes",
                "mostre clientes",
                "cadastro de clientes",
                "do cliente",
                "da cliente",
            ),
        ),
        (
            "schedule",
            (
                "agenda",
                "agendamento",
                "proximo servico",
                "proxima visita",
                "meus compromissos",
                "servico marcado",
                "servicos esta semana",
            ),
        ),
        ("orders", ("meus pedidos", "minhas compras")),
        (
            "company",
            ("telefone", "endereco da loja", "horario", "email da loja", "frete", "entrega"),
        ),
        ("price", ("preco", "quanto custa", "qual o valor")),
        ("stock", ("estoque", "tem disponivel", "tem esse produto", "tem fertilizante")),
        ("product", ("comprar", "vender", "adicionar ao carrinho")),
        ("quote", ("orcamento", "contratar")),
        ("service", ("voces fazem", "servicos", "voces oferecem", "projeto de jardim")),
        (
            "project",
            (
                "meu projeto",
                "meus projetos",
                "quais projetos",
                "qual projeto",
                "mostrar projetos",
                "liste projetos",
                "projetos em",
                "projetos atrasados",
                "meu planejamento",
                "metragem",
                "planejar meu jardim",
            ),
        ),
        ("toxicity", ("toxic", "venenos", "gato comeu", "cachorro comeu", "ingeriu")),
        ("identification", ("identificar", "que planta", "qual planta", "nao sei o nome")),
        (
            "problem",
            (
                "murch",
                "amarel",
                "manchas",
                "bichinhos",
                "praga",
                "morrendo",
                "apodrec",
                "fungo",
                "caule mole",
            ),
        ),
        ("watering", ("regar", "reguei", "rego", "rega", "molhei", "agua")),
        ("lighting", ("luminos", "sol pleno", "sombra", "luz")),
        ("plant_care", ("cuidar", "cuidados", "substrato", "adubar", "plantar")),
    ]
    if re.fullmatch(
        r"(?:oi|ola|bom dia|boa tarde|boa noite)(?:[\s,]+rafinha)?(?:[\s,]+(?:tudo bem|como vai|como voce esta|como vc esta))?",
        q,
    ):
        return "greeting"
    for kind, words in rules:
        if kind == "identification" and (
            care_observations(text).get("excess_watering")
            or care_observations(text).get("wet_soil")
        ):
            return "problem"
        if kind == "identification" and missed_watering(text):
            return "problem"
        if kind == "identification" and recommendation_request(text):
            return "recommendation"
        if kind == "identification" and (
            identification_request(
                text,
                bool(
                    memory.plant_name
                    or memory.slots.get("description")
                    or memory.identity_hypothesis
                ),
            )
            or (field_values(text).get("description") and not memory.plant_name)
        ):
            return "problem" if current_symptoms(text) else "identification"
        if any(w in q for w in words):
            if kind == "problem" and not current_symptoms(text):
                continue
            return kind
    if any(
        w in q
        for w in ["obrigad", "valeu", "floresceu", "melhorou", "morreu", "perdi minha planta"]
    ):
        return "casual"
    if declared_plant(text) or (
        re.search(r"\b(?:tenho uma?|e uma?)\b", q) and explicit_plant(text)
    ):
        return "plant_care"
    if recommendation_request(text):
        return "recommendation"
    return memory.intent if memory.intent != "starting" else "general"


def unknown_answer(q):
    return q.strip(" .!?") in {"nao", "nao sei", "nao lembro", "nao conheco"} or any(
        w in q
        for w in [
            "nao sei o",
            "nao sei qual",
            "nao faco ideia",
            "nao lembro",
            "nao conheco",
            "nao tenho foto",
            "sem foto",
            "nao consigo enviar",
        ]
    )


def read_memory(previous):
    """Repair old generic/predicate identities without discarding care reports."""
    memory = Memory.model_validate(previous or {}).model_copy(deep=True)
    if memory.plant_name and name_key(memory.plant_name) in GROUPS and not memory.species_id:
        memory.slots["plant_group"] = GROUPS[name_key(memory.plant_name)]
        memory.slots.pop("plant_name", None)
        memory.plant_name = None
    elif (
        memory.plant_name
        and not memory.species_id
        and not reported_plants("Tenho uma " + memory.plant_name)
    ):
        memory.plant_name = None
        memory.slots.pop("plant_name", None)
        memory.known_unknowns = list(dict.fromkeys([*memory.known_unknowns, "plant_name"]))
    return memory


def advance(previous, text, facts):
    memory = read_memory(previous)
    if facts.get("recommendations") and (
        memory.intent != "recommendation" or recommendation_request(text)
    ):
        # Options for a new space are not the previously discussed owned plant.
        memory = Memory(intent="recommendation", turn=memory.turn)
    memory.turn += 1
    pending_before = memory.pending_field
    memory.last_answered = None
    q = name_key(text)
    intent = intent_of(text, memory)
    if facts.get("recommendations"):
        intent = "recommendation"
    values = field_values(text)
    # A care question can introduce its subject without asserting a species.
    if group := reported_group(text):
        values.setdefault("plant_group", group)
    if values.get("plant_group") and not memory.plant_name:
        memory.pending_field = None
        memory.known_unknowns = list(dict.fromkeys([*memory.known_unknowns, "plant_name"]))
    if facts.get("recommendations"):
        values = {**facts.get("recommendation_preferences", {}), **values}
    mentioned = facts.get("mentioned_species", catalogue_mentions(text, facts["species"]))
    if (
        values.get("plant_group")
        and not mentioned
        and not declared_plant(text)
        and (
            memory.plant_name
            or memory.slots.get("plant_group") not in {None, values["plant_group"]}
        )
    ):
        memory.plant_name = None
        memory.species_id = None
        memory.slots = {}
        memory.asked = []
        memory.pending_field = None
        memory.research_key = None
        memory.research_context = {}
        memory.identity_hypothesis = {}
        memory.known_unknowns = ["plant_name"]
    reported = reported_plants(
        text,
        allow_bare=(
            memory.pending_field == "plant_name"
            or (not memory.pending_field and not values and not is_question(text))
        ),
    )
    declared = declared_plant(text)
    if declared and name_key(declared) not in {name_key(name) for name in reported}:
        reported = [declared, *reported]
    names = []
    for name in reported:
        exact = catalogue_mentions(name, mentioned)
        label = exact[0].name if len(exact) == 1 else name
        if name_key(label) not in {name_key(n) for n in names}:
            names.append(label)
    for species in mentioned:
        if name_key(species.name) not in {name_key(n) for n in names}:
            names.append(species.name)
    candidates = facts.get("identity_candidates", [])
    explicit_identity = (
        intent not in COMMERCIAL and not facts.get("recommendations") and bool(names)
    )
    if explicit_identity:
        if memory.identity_hypothesis:
            memory.identity_hypothesis = {}
            memory.research_context = {}
            memory.slots.pop("plant_group", None)
        replacing = memory.plant_name and (
            len(names) != 1 or name_key(names[0]) != name_key(memory.plant_name)
        )
        if replacing:
            memory.slots = {}
            memory.known_unknowns = []
            memory.asked = []
            memory.species_id = None
            memory.product_id = None
            memory.research_key = None
            memory.research_context = {}
            memory.identity_hypothesis = {}
        memory.pending_field = None
        memory.plant_choices = [s.name for s in candidates] or (names if len(names) > 1 else [])
        memory.plant_name = names[0] if len(names) == 1 else None
        if memory.plant_choices:
            memory.species_id = None
            memory.slots.pop("plant_name", None)
        elif memory.plant_name:
            memory.slots["plant_name"] = memory.plant_name
        if intent in {"identification", "general", "greeting"}:
            intent = "plant_care"
    elif facts.get("selection_confirmed"):
        memory.plant_choices = []
        memory.pending_field = None
    if intent in COMMERCIAL or intent in {"greeting", "casual"}:
        memory.pending_field = None
    memory.intent = intent
    if memory.pending_field == "care_goal" and (
        values
        or re.search(
            r"\b(?:cuidar|cuidados?|poda\w*|adub\w*|flora\w*|problema\w*|reg\w*|murch\w*)\b", q
        )
    ):
        memory.slots["care_goal"] = text[:180]
        memory.pending_field = None
    if len(facts["species"]) == 1 and not memory.plant_choices and not facts.get("recommendations"):
        species = facts["species"][0]
        memory.species_id = species.id
        memory.plant_name = species.name
        memory.slots["plant_name"] = species.name
        if memory.pending_field == "plant_name":
            memory.pending_field = None
    field = memory.pending_field
    if pending_before == "product_name" and intent in {"price", "stock", "product"}:
        if unknown_fields(text, pending_before):
            memory.known_unknowns = list(dict.fromkeys([*memory.known_unknowns, pending_before]))
        else:
            memory.slots["product_name"] = text[:180]
        memory.last_answered = pending_before
        memory.pending_field = None
    if intent not in COMMERCIAL:
        unknown = unknown_fields(text, field)
        if field == "lighting" and q in {"sim", "nao", "isso", "isso mesmo"}:
            previous_question = normalized(memory.pending_question or "")
            if "sol direto" in previous_question and not re.search(
                r"\b(?:ou|qual|quanto|quantas)\b", previous_question
            ):
                values[field] = "sol direto" if q != "nao" else "sem sol direto"
                unknown = [f for f in unknown if f != field]
        if field == "flowers" and q in {"nao", "nao tem", "sem flores"}:
            values[field] = "não possui flores"
            unknown = [f for f in unknown if f != field]
        if (
            field
            in {"leaf_size", "leaf_shape", "soil_moisture", "lighting", "watering", "symptoms"}
            and not is_question(text)
            and not explicit_identity
        ):
            appropriate = {
                "leaf_size": r"^(?:grandes?|pequenas?|medias?|mais ou menos)$",
                "leaf_shape": r"\b(?:lis\w*|recort\w*|serrilh\w*)\b",
                "soil_moisture": r"\b(?:umid\w*|sec\w*|molhad\w*|sim|nao|bastante|muito|pouco|varios dias|alguns dias)\b",
                "lighting": r"\b(?:sol|luz|claridade|sombra|horas?)\b",
                "watering": r"\b(?:dia|dias|vez|vezes|semanas?|mes|ontem|hoje|sim|nao)\b",
                "symptoms": r"\b(?:folh\w*|raiz|caule|ponta|manch\w*|estranh\w*)\b",
            }[field]
            if field not in unknown and re.search(appropriate, q):
                values.setdefault(field, text[:180])
        for key in unknown:
            if key not in values and not (key == "plant_name" and memory.plant_name):
                memory.slots.pop(key, None)
                memory.known_unknowns = list(dict.fromkeys([*memory.known_unknowns, key]))
        memory.slots.update(values)
        answered = field if field in values or field in unknown else next(iter(values), None)
        if answered and not explicit_identity and not is_question(text):
            memory.last_answered = answered
        if field in values or field in unknown:
            memory.pending_field = None
        if not current_symptoms(text) and re.search(
            r"\b(?:melhorou|se recuperou|brotou|agora esta verde|nao esta(?: mais)? (?:murch\w*|morrendo|amarel\w*|secando))\b",
            q,
        ):
            memory.slots.pop("symptoms", None)
    memory.known_unknowns = [f for f in memory.known_unknowns if f not in memory.slots]
    if (
        not memory.plant_name
        and "plant_name" in memory.known_unknowns
        and not memory.slots.get("plant_group")
    ):
        memory.intent = "identification"
        memory.phase = "identifying"
    return memory


def next_field(memory):
    if memory.plant_choices:
        return "plant_selection"
    if (
        memory.pending_field
        and memory.pending_field not in memory.slots
        and memory.pending_field not in memory.known_unknowns
    ):
        return memory.pending_field
    sequence = (
        ["plant_name", "photo", "leaf_size", "leaf_shape", "flowers", "environment", "lighting"]
        if not memory.plant_name
        else ["environment", "lighting", "watering"]
    )
    if memory.intent in {"problem", "toxicity"}:
        sequence = ["plant_name", "symptoms", "soil_moisture", "watering", "environment"]
    return next(
        (
            f
            for f in sequence
            if f not in memory.slots and f not in memory.known_unknowns and f not in memory.asked
        ),
        None,
    )


def ask(memory, field):
    if (
        not field
        or field in memory.slots
        or field in memory.known_unknowns
        or field in memory.asked
    ):
        return ""
    memory.pending_field = field
    memory.pending_question = QUESTIONS.get(field)
    memory.asked.append(field)
    if field == "plant_selection":
        if len(memory.plant_choices) == 1:
            return "Você quis dizer " + memory.plant_choices[0] + "?"
        return "Você quer seguir com qual planta: " + ", ".join(memory.plant_choices) + "?"
    return QUESTIONS[field]


def merge_semantics(memory, reply):
    candidate_field = reply.question_field
    questions = re.findall(r"[^.!?\n]*\?", reply.text)
    question_text = normalized(questions[-1] if questions else reply.text.rsplit(".", 1)[-1])
    if "?" in reply.text and not candidate_field:
        for field, words in {
            "care_goal": [
                "tipo de ajuda",
                "em que gostaria de ajuda",
                "quer cuidados gerais",
                "quer ajuda com cuidados gerais",
            ],
            "plant_name": ["nome da planta", "qual e a planta", "qual planta"],
            "environment": ["dentro ou fora"],
            "watering": ["frequencia", "costuma regar"],
            "photo": ["enviar uma foto"],
            "flowers": ["tem flores", "possui flores", "floresce"],
            "leaf_size": ["folhas grandes", "folhas pequenas", "tamanho das folhas"],
            "leaf_shape": ["formato das folhas", "são recortadas", "são lisas", "serrilhadas"],
            "lighting": ["recebe sol", "luminosidade", "claridade"],
            "soil_moisture": ["continua umido", "ficar umido"],
            "symptoms": [
                "como ela esta",
                "como a planta esta",
                "folhas estao",
                "folhas firmes",
                "folhas moles",
            ],
        }.items():
            if any(normalized(word) in question_text for word in words):
                candidate_field = field
                break
        if not candidate_field and re.search(
            r"\b(?:recebe|pega|tem|bate)\b.*\b(?:sol|luz|claridade)\b", question_text
        ):
            candidate_field = "lighting"
    refinement = (
        candidate_field == "symptoms"
        and bool(
            re.search(
                r"\b(?:firmes|moles|translucid\w*|enrugad\w*|amarelad\w*|escur\w*|caindo)\b",
                question_text,
            )
        )
        and question_text != normalized(memory.pending_question or "")
    )
    if (
        candidate_field
        and not refinement
        and (
            candidate_field not in FIELDS
            or candidate_field in memory.slots
            or candidate_field in memory.known_unknowns
            or candidate_field in memory.asked
        )
    ):
        return False
    for key, value in reply.updates.items():
        if (
            key in FIELDS
            and key != "plant_name"
            and isinstance(value, str)
            and 0 < len(value) <= 180
            and "<" not in value
        ):
            memory.slots[key] = value
    for field in reply.known_unknowns:
        if field in FIELDS and field not in memory.slots:
            memory.known_unknowns = list(dict.fromkeys([*memory.known_unknowns, field]))
    if reply.intent and re.fullmatch(r"[a-z_]{2,40}", reply.intent):
        memory.intent = reply.intent
    if candidate_field:
        if refinement:
            memory.pending_field = candidate_field
        else:
            ask(memory, candidate_field)
        memory.pending_question = reply.text.rsplit(".", 1)[-1]
    return True
