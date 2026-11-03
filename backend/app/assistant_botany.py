"""Small, source-backed reference library and checks on local answer usefulness.

These records are hypotheses, independent of the shop catalogue and live search.
Adding aliases does not require another dialogue-specific branch.
"""

import re

from .assistant_language import identification_request, name_key, negated

GROUP_REFERENCE = {
    "title": "RHS — cuidados de cactos e suculentas",
    "url": "https://www.rhs.org.uk/plants/types/cacti-succulents/houseplants/growing-guide",
}
IDENTITY_REFERENCES = (
    {
        "label": "Crassula ovata 'Gollum'",
        "family": "Crassulaceae",
        "popular_name": "orelha-de-Shrek",
        "aliases": (r"orelhas? (?:de|do) sh(?:e)?rek", r"gollum"),
        "features": "folhas grossas, tubulares, com pontinhas que lembram pequenas ventosas",
        "question": "As folhas dela são tubulares, com uma pequena abertura arredondada na ponta?",
        "source": {
            "title": "NC State — Crassula ovata e suas variedades",
            "url": "https://plants.ces.ncsu.edu/plants/crassula-ovata/",
        },
    },
    {
        "label": "Crassula ovata",
        "family": "Crassulaceae",
        "popular_name": "planta-jade",
        "aliases": (r"planta jade", r"arvore de jade"),
        "features": "folhas ovais e carnosas, com ramos que engrossam com o tempo",
        "question": "Ela tem folhas ovais e grossas, em ramos que parecem uma pequena árvore?",
        "source": {
            "title": "NC State — Crassula ovata",
            "url": "https://plants.ces.ncsu.edu/plants/crassula-ovata/",
        },
    },
    {
        "label": "Sedum morganianum",
        "family": "Crassulaceae",
        "popular_name": "rabo-de-burro",
        "aliases": (r"rabo de burro", r"cauda de burro", r"donkey s tail", r"burro s tail"),
        "features": "ramos pendentes cobertos por pequenas folhas carnosas, formando caudas",
        "question": "Os ramos caem para fora do vaso e ficam cobertos por pequenas folhas grossas?",
        "source": {
            "title": "NC State — Sedum morganianum",
            "url": "https://plants.ces.ncsu.edu/plants/sedum-morganianum/",
        },
    },
)


def reference_for(memory, question):
    q = name_key(question)
    if (
        re.search(r"\bsuculentas?\b", q)
        and re.search(r"\bcactos?\b", q)
        and re.search(r"\b(?:igual|iguais|mesm\w*|diferenc\w*|disting\w*|compar\w*)\b", q)
    ):
        return {"kind": "comparison", "sources": [GROUP_REFERENCE]}
    describing = bool(re.search(r"\b(?:parece|lembra|formato|conhecid\w*|chamad\w*)\b", q))
    contextual = bool(memory.slots.get("description") or memory.identity_hypothesis)
    if (
        memory.intent != "identification"
        and not describing
        and not identification_request(question, contextual)
    ):
        return None
    clues = name_key(memory.slots.get("description", "") + " " + question)
    candidates = []
    for record in IDENTITY_REFERENCES:
        for alias in record["aliases"]:
            hits = list(re.finditer(r"\b(?:" + alias + r")\b", clues))
            if any(
                not negated(clues[: hit.start()])
                and not re.search(
                    r"\b(?:nao|nunca) (?:parece|lembra)(?: com)?(?: (?:uma?|a|o))?\s*$",
                    clues[: hit.start()],
                )
                for hit in hits
            ):
                candidates.append(record)
                break
    # Even a familiar nickname can be ambiguous. Never select among two clues.
    if len(candidates) != 1:
        return None
    record = candidates[0]
    return {"kind": "identification", **record, "sources": [record["source"]]}


def supported_answer(reference, memory):
    if reference["kind"] == "comparison":
        return (
            "Não exatamente 🌿 Suculentas armazenam água nas folhas ou caules; cactos pertencem à família Cactaceae. "
            "Muitos cactos são suculentos, mas uma suculenta não é necessariamente um cacto. Os cuidados variam conforme a planta.\n\n"
            "Para começar, confira a umidade da terra e a drenagem do vaso antes de regar. Muitas espécies preferem intervalos "
            "entre regas, enquanto cactos de floresta, como a flor-de-maio, precisam de condições diferentes. "
            "Não existe uma frequência de rega ou quantidade de sol que sirva para todas. Como são as folhas da planta que você quer cuidar?"
        )
    label = reference["label"]
    hypothesis = memory.identity_hypothesis
    already = hypothesis.get("label") == label
    if already:
        return (
            f"O nome provável é **{label}** ({reference['popular_name']}). "
            "Essa é a hipótese baseada no apelido e na descrição; não confirma a identidade da sua planta. "
            f"Os sinais que ajudam a conferir são {reference['features']}."
        )
    opening = "Pelo apelido que você descreveu, uma possibilidade é"
    return (
        f"{opening} **{label}**, associada ao nome **{reference['popular_name']}** 🌱. "
        f"Ela costuma apresentar {reference['features']}.\n\n"
        "A descrição ajuda, mas não confirma a espécie nem a variedade da sua planta. "
        + (
            "Como você relatou um problema, vamos considerar também a rega, a luz e o estado atual dela. "
            if memory.slots.get("symptoms")
            else ""
        )
        + reference["question"]
    )


def substantive_reply(text, question):
    """Reject echoes and capability promises, whatever the subject of the turn."""
    q = name_key(text)
    user = name_key(question)
    if q in {user, "sim " + user, "sim", "nao", "claro"}:
        return False
    # A capability promise followed by another vague sentence is still not an
    # answer. Genuine instructions after an introduction remain acceptable.
    first = re.split(r"[.!?]", text, maxsplit=1)[0]
    rest = text[len(first) :].strip(" .!?")
    first_key = name_key(first)
    promise = bool(
        re.fullmatch(
            r"(?:(?:sim|claro|com certeza) )?(?:eu )?(?:posso|vou|consigo) "
            r"(?:ajudar|te ajudar|ajudar voce|ajudar a|ajudar voce a|ajudar a voce a)? ?"
            r"(?:determinar|descobrir|identificar|entender|explicar|responder|dizer)? ?"
            r"(?:qual e|qual e o nome|o nome|como cuidar|sobre)? ?(?:da |a |sua |essa |esta )?"
            r"(?:planta|isso|duvida|pergunta)?",
            first_key,
        )
    )
    if not promise:
        return True
    return bool(
        rest
        and re.search(
            r"\b(?:confira|verifique|observe|retire|evite|precisa|armazena|pertence|diferenca|porque|por exemplo|escoa|drenagem|substrato)\b",
            name_key(rest),
        )
    )


def follows_reference(text, reference):
    if not reference:
        return True
    q = name_key(text)
    if reference["kind"] == "identification":
        families = re.findall(r"\bfam[ií]lia\s+([A-Z][a-z]{2,})", text)
        return (
            name_key(reference["label"]) in q
            and bool(
                re.search(
                    r"\b(?:possibilidade|hipotese|nome provavel|pode ser (?!confirmad\w*|identificad\w*)|provavelmente|talvez)\b",
                    q,
                )
            )
            and all(family == reference["family"] for family in families)
            and not re.search(
                r"^(?:sim )?a (?:especie|planta) que (?:voce |vc )?(?:descreveu|tem|ganhou) e\b", q
            )
            and not re.search(r"\b(?:com certeza|identificacao confirmada|sem duvida)\b", q)
        )
    return (
        bool(
            re.search(
                r"\b(?:nao exatamente|nao (?:sao |e |sao exatamente )?(?:iguais|igual)|diferentes|diferenca)\b",
                q,
            )
        )
        and bool(re.search(r"\b(?:especie|especies|variam|varia|depende|diferentes)\b", q))
        and bool(re.search(r"\b(?:familia|cactaceae)\b", q))
        and not re.search(
            r"\b(?:sim.{0,15}igual|umidade regular|todas.{0,25}(?:sol pleno|mesma rega))\b", q
        )
    )
