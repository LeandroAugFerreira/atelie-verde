"""Reported care and broad plant groups, separated from species identification."""

import re

from .assistant_text import understood_text
from .business import normalized

GROUPS = {"suculenta": "suculenta", "suculentas": "suculenta", "cacto": "cacto", "cactos": "cacto"}


def reported_group(text):
    q = normalized(understood_text(text))
    match = re.search(
        r"\b(?:tenho|ganhei|comprei|e|minha|minhas?|meus?|regar|cuidar (?:de|da|do))\s+(?:(?:uma?|a|o|as|os)\s+)?(suculentas?|cactos?)\b(?!-)",
        q,
    )
    if not match or re.search(
        r"\b(?:nao|nunca)\s*$|\b(?:nao sei se|talvez|acho que)\b", q[: match.start()]
    ):
        return None
    return GROUPS.get(match.group(1))


def care_observations(text):
    # Questions about a possible action are not assertions that it happened.
    q = normalized(
        re.split(r"\b(?:como|devo|posso|qual|por que)\b", text, maxsplit=1, flags=re.I)[0]
    )
    result = {}
    excess = re.search(
        r"\b(?:reguei|rego|regava|molhei|molho|coloquei agua)\b.{0,35}\b(?:muito|demais|em excesso|excessiva\w*)\b",
        q,
    )
    if excess and not re.search(r"\bnao\s+(?:reguei|rego|molhei|molho)\b", excess.group()):
        prefix = q[max(0, excess.start() - 12) : excess.start()]
        if not re.search(r"\b(?:nao|nunca)\s*$", prefix):
            result["excess_watering"] = True
    wet = re.search(
        r"\b(?:substrato|terra|solo|vaso)\b.{0,25}\b(?:encharcad\w*|muito molhad\w*)\b", q
    )
    if wet and not re.search(r"\b(?:nao|nunca)\b", wet.group()):
        result["wet_soil"] = True
    if re.search(
        r"\b(?:nao|nunca)\s+(?:deixei|deixo|deixava|coloquei|coloco|recebe|recebeu|pega|pegou|fica|ficou|tem)\b.{0,25}\bsol\b|\bsem sol\b",
        q,
    ):
        result["no_direct_sun"] = True
    light = re.search(r"\b(?:sem luz|pouca luz|escuro|escura)\b", q)
    if light and not re.search(r"\b(?:nao|nunca)\b", q[max(0, light.start() - 15) : light.start()]):
        result["low_light"] = True
    return result


GENERAL_MOISTURE_GUIDANCE = {
    "text": "Excesso de umidade pode prejudicar raízes. Conferir umidade e drenagem ajuda antes de regar novamente; não presumir podridão ou recomendar uma rotina única para todas as espécies.",
    "source": {
        "title": "RHS — umidade excessiva e drenagem",
        "url": "https://www.rhs.org.uk/problems/oedema",
    },
}
