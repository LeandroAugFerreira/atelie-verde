"""Shared, conservative language parsing for retrieval and session state.

Names come from the catalogue or are explicitly reported. Similar spelling only
produces a confirmation candidate, never an automatic botanical identification.
"""

import itertools
import re
from difflib import SequenceMatcher

from .assistant_observations import care_observations, reported_group
from .assistant_text import understood_text
from .business import normalized

INTRO = re.compile(
    r"\b(?:cuid(?:ar|o|ados)\s+(?:de|da|do|das|dos|com|para|sobre|dessa|desse|desta|deste|daquela|daquele)\b\s*|"
    r"(?:cultivar|plantar|adubar|regar|podar|replantar|transplantar)\b\s*|"
    r"(?:tenho|possuo|ganhei|comprei)\b\s*|é\s+|e\s+(?=(?:um|uma|a|o)\b)|"
    r"minha\s+|minhas\s+|meu\s+|meus\s+)",
    re.I,
)
STOP = re.compile(
    r"\s+(?:mas|porém|porem|porque|que|não|nao|está|esta|estão|estao|"
    r"agora|ainda|então|entao|ontem|hoje|parece|parecem|lembra|lembram|parecida|parecido|igual|semelhante|fica|ficam|ficou|ficaram|vive|vivem|recebe|pega|tem|possui|apresenta|anda|melhorou|morreu|floresceu|brotou|precisa|precisam|preciso|quero|como|com|sem|no|na|num|numa|em|durante|desde|por|para|ha|há)\b",
    re.I,
)
NON_NAMES = {
    "vc",
    "diga",
    "diz",
    "conte",
    "explique",
    "sabe",
    "saber",
    "parece",
    "lembra",
    "dela",
    "dele",
    "e",
    "ou",
    "planta",
    "plantas",
    "nome",
    "especie",
    "ela",
    "ele",
    "elas",
    "eles",
    "isso",
    "nao",
    "sei",
    "sim",
    "dentro",
    "fora",
    "casa",
    "grandes",
    "pequenas",
    "medio",
    "mais",
    "menos",
    "muito",
    "muita",
    "pouco",
    "pouca",
    "demais",
    "toxica",
    "toxico",
    "venenosa",
    "venenoso",
    "conhecida",
    "conhecido",
    "bastante",
    "recortadas",
    "serrilhadas",
    "lisas",
    "flores",
    "amarelas",
    "obrigado",
    "obrigada",
    "ola",
    "oi",
    "todo",
    "todos",
    "dia",
    "dias",
    "sol",
    "luz",
    "foto",
    "fotos",
    "duvida",
    "duvidas",
    "problema",
    "problemas",
    "ideia",
    "pergunta",
    "pedido",
    "orcamento",
    "projeto",
    "jardim",
    "varanda",
    "vaso",
    "vasos",
    "conta",
    "cliente",
    "fornecedor",
    "sem",
    "bom",
    "boa",
    "uma",
    "um",
    "gato",
    "cachorro",
    "crianca",
    "mae",
    "pai",
    "filho",
    "amigo",
    "bonita",
    "bonito",
    "me",
    "eu",
    "voce",
    "nos",
    "tudo",
    "bem",
    "ajuda",
    "ajude",
    "pode",
    "posso",
    "que",
    "qual",
    "como",
    "quanto",
    "quando",
    "onde",
    "outra",
    "outras",
    "umidade",
    "rega",
    "adubacao",
    "substrato",
    "terra",
    "folhas",
    "caule",
    "raiz",
    "melhor",
    "melhores",
    "ideal",
    "ideais",
    "adequada",
    "adequadas",
    "apartamento",
    "espaco",
    "ambiente",
    "local",
    "flor",
    "arvore",
    "arvores",
    "muda",
    "mudas",
    "suculenta",
    "suculentas",
    "cacto",
    "cactos",
}


def name_key(text):
    return " ".join(re.findall(r"[a-z0-9]+", normalized(understood_text(text))))


def negated(prefix):
    prefix = name_key(prefix)
    return bool(
        re.search(
            r"\b(?:nao|nunca|nem|sem)\s*(?:(?:esta|estao|tem|tenho|possuo|ganhei|comprei|"
            r"fica|ficam|ficou|pega|recebe|apresenta|e|mais|uma?|a|o|as|os)\s*){0,5}$",
            prefix,
        )
    )


def reported_plants(text, allow_bare=False):
    text = understood_text(text).strip()
    # Apposition introduces the identity after a generic noun, not a new plant:
    # "Tenho uma planta, uma roseira" / "minha planta é uma roseira".
    text = re.sub(r"\bplantas?\s*[,;:]\s*(?=(?:uma?|a|o)\s+)", "planta, é ", text, flags=re.I)
    matches = list(INTRO.finditer(text))
    chunks = [
        re.split(
            r"[.,;?!]",
            text[m.end() : matches[i + 1].start() if i + 1 < len(matches) else None],
            maxsplit=1,
        )[0]
        for i, m in enumerate(matches)
        if not negated(text[: m.start()])
    ]
    if not matches and allow_bare and not recommendation_request(text) and len(text.split()) <= 4:
        chunks = [text]
    names = []
    for chunk in chunks:
        for part in re.split(r"\s+(?:e|ou)\s+", chunk, flags=re.I):
            if STOP.match(" " + part.strip()):
                continue
            part = STOP.split(part, maxsplit=1)[0].strip(" .!?,;\"'")
            part = re.sub(
                r"^(?:(?:uma?|a|o|as|os|minhas?|meus?|duas|dois|algumas?|varias?|várias?|"
                r"\d+|linda|pequena|grande|nova)\s+)+",
                "",
                part,
                flags=re.I,
            )
            key = name_key(part)
            generic_plant = (
                key.split()[0]
                in {
                    "planta",
                    "plantas",
                    "flor",
                    "flores",
                    "arvore",
                    "arvores",
                    "muda",
                    "mudas",
                    "suculenta",
                    "suculentas",
                    "cacto",
                    "cactos",
                }
                if key
                else False
            )
            compound_plant = (
                generic_plant
                and len(key.split()) > 1
                # Compound names retain a connector or hyphen. A generic noun
                # followed by a temporal/adjectival clause is not an identity.
                and ("-" in part or key.split()[1] in {"de", "do", "da"})
            )
            if (
                not key
                or len(key) < 3
                or (key.split()[0] in NON_NAMES and not compound_plant)
                or len(key.split()) > 5
                or len(part) > 70
                or any(c in part for c in "@/:0123456789")
            ):
                continue
            if key not in {name_key(n) for n in names}:
                names.append(part)
    return names[:4]


def explicit_plant(text, allow_bare=True):
    names = reported_plants(text, allow_bare)
    return names[0] if len(names) == 1 else None


def name_variants(name, plural=False):
    tokens = name_key(name).split()
    if not plural:
        return [" ".join(tokens)]
    options = []
    for token in tokens:
        forms = [token]
        if token not in {"de", "do", "da", "dos", "das", "sao", "paz"}:
            if token.endswith("m"):
                forms.append(token[:-1] + "ns")
            elif token.endswith(("a", "e", "i", "o", "u")):
                forms.append(token + "s")
        options.append(forms)
    return [" ".join(words) for words in itertools.product(*options)][:32]


def catalogue_mentions(text, rows, fields=("name", "scientific_name")):
    query = name_key(text)
    spans = []
    for row in rows:
        for field in fields:
            for alias in name_variants(getattr(row, field, ""), plural=field == "name"):
                if len(alias) < 3:
                    continue
                for match in re.finditer(r"\b" + re.escape(alias) + r"\b", query):
                    if not negated(query[: match.start()]):
                        spans.append((match.start(), match.end(), row))
    chosen = []
    # A long compound name wins over an overlapping short name.
    for start, end, row in sorted(spans, key=lambda s: (-(s[1] - s[0]), s[0])):
        if any(start < old_end and end > old_start for old_start, old_end, _ in chosen):
            continue
        chosen.append((start, end, row))
    result = []
    for _, _, row in sorted(chosen, key=lambda s: s[0]):
        if row not in result:
            result.append(row)
    return result


def spelling_candidates(name, rows):
    query = name_key(name)
    if len(query) < 5:
        return []
    ranked = []
    for row in rows:
        score = max(
            (
                SequenceMatcher(None, query, alias).ratio()
                for alias in [name_key(row.name), name_key(row.scientific_name)]
                if alias and alias[0] == query[0]
            ),
            default=0,
        )
        if score >= 0.83:
            ranked.append((score, row))
    ranked.sort(key=lambda p: p[0], reverse=True)
    return [row for score, row in ranked[:3] if score >= ranked[0][0] - 0.04]


def is_question(text):
    return "?" in text or bool(
        re.search(
            r"^(?:como|qual|quais|quanto\w*|por que|porque|posso|devo|com que)\b|\b(?:gostaria de|quero)\s+saber\b",
            name_key(text),
        )
    )


def identification_request(text, has_context=False):
    q = name_key(text)
    return bool(
        re.search(r"\b(?:identific\w*|qual (?:e )?(?:o nome|a especie|a planta)|que planta e)\b", q)
        or (
            has_context
            and re.fullmatch(
                r"(?:(?:voce|vc) )?(?:sabe qual e|qual e|qual seria|me diga|diga|me diz|diz|me conte|pode me dizer|entao me diga)(?: a planta)?",
                q,
            )
        )
    )


def recommendation_request(text):
    q = name_key(text)
    return bool(
        re.search(r"\b(?:recomend\w*|indica\w*|indique\w*|escolher|combinam)\b", q)
        or re.search(
            r"\b(?:qual|quais|que)\b.*\b(?:plantas?|especies?)\b.*\b(?:para|combina\w*)\b", q
        )
        or re.search(r"\b(?:melhor\w*|ideal|ideais|adequad\w*)\s+(?:plantas?|especies?)\b", q)
    )


def missed_watering(text):
    q = name_key(text)
    forgotten = re.finditer(
        r"\b(?:esqueci|esquecemos|esqueceu|esquecido)\s+(?:de\s+)?(?:regar|molhar)\b", q
    )
    return any(not negated(q[: match.start()]) for match in forgotten) or bool(
        re.search(
            r"\b(?:nao reguei|nao molhei|sem regar|sem molhar|sem rega|sem agua)\b(?!\s+(?:muito|demais|em excesso)\b)",
            q,
        )
    )


def unknown_fields(text, pending=None):
    q = name_key(text)
    fields = []
    for field, pattern in {
        "plant_name": r"(?:nao sei|nao lembro|nao conheco|nao faco ideia).*(?:nome|especie|qual planta)",
        "photo": r"(?:nao tenho|nao consigo enviar|sem) (?:uma )?foto",
        "lighting": r"(?:nao sei|nao lembro).*(?:quanta luz|quanto sol|luminosidade)",
        "watering": r"(?:nao sei|nao lembro).*(?:ultima rega|quando reguei|costumo regar)",
    }.items():
        if re.search(pattern, q):
            fields.append(field)
    if pending and q in {
        "nao",
        "nao sei",
        "nao lembro",
        "nao conheco",
        "nao faco ideia",
        "nao sei dizer",
    }:
        fields.append(pending)
    return list(dict.fromkeys(fields))


SYMPTOMS = r"\b(?:murch\w*|amarel\w*|manchas?|bichinhos?|pragas?|morrendo|apodrec\w*|fungos?|secando|raiz podre|caule mole)\b"


def current_symptoms(text):
    q = name_key(text)
    if re.search(r"\b(?:mas|porem|agora)\b.*(?:melhorou|esta verde|brotou|folha nova|recuper)", q):
        q = re.split(r"\b(?:mas|porem|agora)\b", q)[-1]
    return any(not negated(q[: m.start()]) for m in re.finditer(SYMPTOMS, q))


def field_values(text):
    # Preserve a declarative prefix in "fica fora, como cuidar?", but never turn
    # "ela deve ficar fora?" into an asserted fact.
    statement = re.split(
        r"\b(?:como|qual|quais|quanto\w*|por que|posso|devo|o que (?:eu )?(?:faço|faco|fazer))\b",
        text,
        maxsplit=1,
        flags=re.I,
    )[0]
    if is_question(statement):
        return {}
    q = name_key(statement)
    values = {}
    group = reported_group(statement)
    if group:
        values["plant_group"] = group
    description = re.search(r"\b(?:parece(?: com)?|lembra|tem formato de)\s+(.+)", statement, re.I)
    if description:
        values["description"] = description.group(0)[:180]
    observations = care_observations(statement)
    if observations.get("low_light"):
        values["lighting"] = "pouca luz"
    elif observations.get("no_direct_sun"):
        values["lighting"] = "relato de ausência de sol direto"
    if observations.get("excess_watering"):
        values["watering"] = "relato de rega excessiva"
    if observations.get("wet_soil"):
        values["soil_moisture"] = "encharcado"
    for field, labels in {
        "environment": {
            "dentro": "interno",
            "interno": "interno",
            "sala": "interno",
            "escritorio": "interno",
            "apartamento": "interno",
            "fora": "externo",
            "externo": "externo",
            "quintal": "externo",
        },
        "lighting": {
            "sol direto": "sol direto",
            "sol pleno": "sol pleno",
            "luz indireta": "claridade indireta",
            "claridade indireta": "claridade indireta",
            "pouca luz": "pouca luz",
        },
        "container": {
            "vaso": "vaso",
            "vasos": "vaso",
            "canteiro": "canteiro",
            "diretamente no solo": "solo",
        },
    }.items():
        found = []
        for marker, label in labels.items():
            for match in re.finditer(r"\b" + re.escape(marker) + r"\b", q):
                if not negated(q[: match.start()]):
                    found.append((match.start(), label))
        if found:
            values[field] = " / ".join(dict.fromkeys(label for _, label in sorted(found)))
    # An explicit lack of direct sun must not become an affirmative "sol direto".
    if observations.get("no_direct_sun") and not observations.get("low_light"):
        if values.get("lighting") in {None, "sol direto", "sol pleno"}:
            values["lighting"] = "relato de ausência de sol direto"
    if (
        missed_watering(statement) or re.search(r"\b(?:rego|reguei|regava|molho)\b", q)
    ) and re.search(r"\b(?:dia|dias|semana|semanas|vez|vezes|diariamente|ontem|hoje)\b", q):
        values["watering"] = statement[:180].strip(" .,;")
    if re.search(r"\bfolhas? (?:grandes?|pequenas?|medias?)\b", q):
        values["leaf_size"] = statement[:180].strip(" .,;")
    if re.search(r"\b(?:recort\w*|serrilhad\w*|folhas? lisas?)\b", q):
        values["leaf_shape"] = statement[:180].strip(" .,;")
    if re.search(r"\b(?:nao tem|nao possui|sem) flores\b", q):
        values["flowers"] = "não possui flores"
    elif re.search(r"\b(?:tem|possui) flores\b", q):
        values["flowers"] = "possui flores"
    if re.search(r"\b(?:flores?|rosa)\s+(?:vermelh\w*|branc\w*|amarel\w*|rox\w*|cor de rosa)\b", q):
        values["flower_color"] = statement[:180].strip(" .,;")
    if current_symptoms(text):
        values["symptoms"] = text[:180]
    return values


def selection(text, choices, aliases=None):
    q = name_key(text)
    if re.search(r"\b(?:nao sei se|talvez|acho que)\b", q):
        return None
    for index, label in enumerate(["primeira", "segunda", "terceira", "quarta"]):
        if q in {label, "a " + label, "a " + label + " planta", str(index + 1)}:
            return choices[index] if index < len(choices) else None
    if len(choices) == 1 and q in {"sim", "isso", "isso mesmo", "correto", "essa mesma"}:
        return choices[0]
    for name in choices:
        labels = [name, (aliases or {}).get(name_key(name), "")]
        for label in labels:
            if not label:
                continue
            match = re.search(r"\b" + re.escape(name_key(label)) + r"\b", q)
            if match and not negated(q[: match.start()]):
                return name
    return None
