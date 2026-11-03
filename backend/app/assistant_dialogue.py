"""Checks that a generated reply continues the current conversational turn."""

import re
from difflib import SequenceMatcher

from .assistant_language import field_values, missed_watering, name_key

GREETING_PARTS = (
    r"(?:oi|ola|bom dia|boa tarde|boa noite)(?: tudo bem)?",
    r"(?:(?:oi|ola) )?que bom (?:ter|ver) voce (?:por |de novo por )?aqui",
    r"seja bem vind[oa](?: ao atelie verde)?",
    r"como (?:posso|podemos) (?:te )?ajudar(?: voce)?(?: (?:hoje|com seu espaco verde|com suas plantas|com seu jardim))?",
    r"(?:estou|estamos) (?:aqui|por aqui) para (?:te )?ajudar(?: voce)?",
)


def greeting_only(text):
    parts = [name_key(part) for part in re.split(r"[.!?;\n]+", text)]
    for part in parts:
        while part:
            matches = [re.match(pattern + r"(?= |$)", part) for pattern in GREETING_PARTS]
            length = max((match.end() for match in matches if match), default=0)
            if not length:
                return False
            # Consume the longest phrase once. A model repeating greetings
            # cannot cause exponential backtracking in a nested expression.
            part = part[length:].lstrip()
    return bool(any(parts))


def replay_reason(text, question, memory, previous, history):
    if memory.intent != "greeting" and greeting_only(text):
        return "greeting_instead_of_continuation"
    if memory.intent == "greeting" or re.search(
        r"\b(?:repita|repetir|diga novamente)\b", name_key(question)
    ):
        return None
    plant = memory.plant_name or memory.slots.get("plant_group")
    if plant:
        name = re.escape(name_key(plant))
        own_plant = r"(?:eu )?(?:tenho|ganhei|comprei|possuo) (?:uma? |a |o |minha |meu )?" + name
        acknowledgement = (
            r"(?:claro |entendi |entao |sim )?"
            r"(?:(?:voce|vc) (?:tem|ganhou|possui) (?:uma? |a |o )?|"
            r"(?:sua planta e|estamos falando de|estamos falando da|essa e) )" + name
        )
        parts = [part.strip() for part in re.split(r"[.!?;\n]+", text) if name_key(part)]
        if any(re.fullmatch(own_plant, name_key(part)) for part in parts):
            return "claimed_user_plant_as_own"
        if parts and all(
            greeting_only(part) or re.fullmatch(acknowledgement, name_key(part)) for part in parts
        ):
            return "greeting_with_only_subject_echo"
    # A change in conditions or subject needs a new answer. Identical answers
    # remain legitimate for an explicit repeat or an unchanged factual query.
    new_information = (
        field_values(question)
        or missed_watering(question)
        or memory.intent != previous.intent
        or memory.slots != previous.slots
        or memory.known_unknowns != previous.known_unknowns
    )
    if not new_information:
        return None
    previous_reply = next(
        (m.text for m in reversed(history) if m.role == "assistant" and m.status == "completed"),
        None,
    )
    if (
        previous_reply
        and SequenceMatcher(None, name_key(previous_reply), name_key(text)).ratio() >= 0.88
    ):
        return "repeated_after_new_information"
    return None
