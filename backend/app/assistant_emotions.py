"""Conservative visual reactions: empathy, never a botanical diagnosis."""

import re

from .assistant_language import current_symptoms, missed_watering, negated
from .assistant_observations import care_observations
from .business import normalized

EXPRESSIONS = {
    "neutral",
    "welcome",
    "happy",
    "excited",
    "concerned",
    "thinking",
    "curious",
    "surprised",
    "sad",
    "confident",
    "relieved",
    "confused",
    "explaining",
    "greeting",
    "serious",
    "angry",
    "sleepy",
    "shy",
    "skeptical",
    "delighted",
    "celebrating",
}


def reaction(question, facts=None, memory=None):
    q = normalized(question)
    active_clause = re.split(r"\b(?:mas|porem|agora)\b", q)[-1]
    denied_action = bool(
        re.search(
            r"\b(?:nao|nunca)\s+(?:(?:vou|pretendo)\s+)?(?:usar|uso|usei|colocar|coloco|regar|rego|reguei|adubar|adubo|molhar|molho)\b",
            active_clause,
        )
    )
    observed = care_observations(question)
    if observed.get("excess_watering") or observed.get("wet_soil"):
        return {"initial": "concerned", "processing": "thinking", "final": "serious"}
    # Combine report/event semantics with known care, previous state and verified
    # system data. These rules remain available without a model or internet.
    if re.search(r"\b(?:fofo|querido|adoro voce|gosto de voce)\b", q):
        return {"initial": "shy", "processing": "thinking", "final": "shy"}
    if q.strip(" !.") in {"boa noite", "voce ainda esta acordado", "ja esta tarde"}:
        return {"initial": "sleepy", "processing": "thinking", "final": "sleepy"}
    dangerous = re.search(r"\b(?:agua sanitaria|detergente|desinfetante)\b", q)
    if dangerous and not denied_action and not negated(q[: dangerous.start()]):
        planned = bool(re.search(r"\b(?:vou|pretendo)\b", q))
        return {
            "initial": "angry" if planned else "serious",
            "processing": "thinking",
            "final": "serious",
        }
    excessive = re.search(r"\b(?:cinco|5|dez|10)\s+vezes\s+(?:por|ao)\s+dia\b", q)
    if excessive and not denied_action and re.search(r"\b(?:reg\w*|molh\w*|adub\w*)\b", q):
        return {"initial": "surprised", "processing": "thinking", "final": "serious"}
    if not denied_action and re.search(r"\badub\w*\b.*\btodos os dias\b", q):
        return {"initial": "serious", "processing": "thinking", "final": "serious"}
    if (
        (memory and memory.last_expression in {"concerned", "serious", "sad"})
        and re.search(r"\b(?:recuperou|recuperada|funcionou|deu certo)\b", q)
        and not current_symptoms(question)
    ):
        return {"initial": "happy", "processing": "thinking", "final": "celebrating"}
    if re.search(r"\b(?:projeto finalizado|orcamento aprovado|servico concluido)\b", q):
        return {"initial": "happy", "processing": "thinking", "final": "celebrating"}
    project = (facts or {}).get("project")
    if (
        project
        and project.status in {"Finalizado", "Aprovado"}
        and (memory and memory.intent in {"project", "quote"})
    ):
        return {"initial": "happy", "processing": "thinking", "final": "celebrating"}
    if re.search(r"\bfloresc\w*\b", q) and not current_symptoms(question):
        return {"initial": "happy", "processing": "thinking", "final": "delighted"}
    if memory and memory.phase == "identifying" and "nao sei" in q:
        return {"initial": "thinking", "processing": "thinking", "final": "thinking"}
    if re.search(r"\b(?:contraditorio|nunca recebe luz.*dez anos)\b", q):
        return {"initial": "skeptical", "processing": "thinking", "final": "thinking"}
    if facts and facts.get("species") and any(w in q for w in ["nao reguei", "nao molhei"]):
        low_water = all(normalized(s.watering) == "baixa" for s in facts["species"])
        one_day = any(w in q for w in ["ontem", "hoje", "um dia", "1 dia"])
        symptoms = current_symptoms(question)
        if low_water and one_day and not symptoms:
            return {"initial": "concerned", "processing": "thinking", "final": "relieved"}
    # Recovery and negated symptoms take precedence over historical problem words.
    if (
        any(
            w in q
            for w in [
                "melhorou",
                "nao esta mais",
                "nao esta murch",
                "ja nao",
                "voltou a",
                "agora esta verde",
                "folha nova",
                "brotou",
            ]
        )
        and any(w in q for w in ["antes", "mas", "murch", "morr", "amarel", "recuper", "melhorou"])
        and not current_symptoms(question)
    ):
        return {
            "initial": "surprised" if "brotou" in q else "relieved",
            "processing": "thinking",
            "final": "relieved",
        }
    losses = re.finditer(
        r"\b(?:morreu|nao resistiu|perdi minha planta|perdi minha arvore|jardim foi destruido)\b", q
    )
    if any(not negated(q[: loss.start()]) for loss in losses):
        return {"initial": "sad", "processing": "thinking", "final": "sad"}
    if current_symptoms(question):
        return {"initial": "concerned", "processing": "thinking", "final": "concerned"}
    if missed_watering(question):
        return {"initial": "concerned", "processing": "thinking", "final": "concerned"}
    if any(w in q for w in ["primeira vez", "de repente", "fora de epoca", "varios brotos"]):
        return {"initial": "surprised", "processing": "thinking", "final": "excited"}
    if any(
        w in q
        for w in ["nao sei", "nao faco ideia", "identificar", "qual planta", "ganhei uma planta"]
    ):
        return {"initial": "curious", "processing": "thinking", "final": "curious"}
    if any(w in q for w in ["melhor e pior", "nao entendi", "contraditorio"]):
        return {"initial": "confused", "processing": "thinking", "final": "curious"}
    if any(
        w in q
        for w in [
            "nao reguei",
            "nao molhei",
            "sem agua",
            "sem rega",
            "toxic",
            "venenos",
            "gato comeu",
            "cachorro comeu",
            "reguei demais",
        ]
    ):
        return {"initial": "concerned", "processing": "thinking", "final": "concerned"}
    if any(w in q for w in ["obrigad", "valeu", "floresceu", "deu certo", "funcionou", "adorei"]):
        return {"initial": "happy", "processing": "neutral", "final": "happy"}
    if q.strip(" !.") in {"oi", "ola", "bom dia", "boa tarde", "boa noite"}:
        return {"initial": "greeting", "processing": "neutral", "final": "greeting"}
    return {
        "initial": "neutral",
        "processing": "thinking",
        "final": "confident" if facts and facts.get("species") else "explaining",
    }


def expression(question, facts):
    return reaction(question, facts)["final"]
