"""Factual sufficiency depends on the requested subject, not just a populated card."""

import re

from .business import normalized

ASPECT_FIELDS = {
    "watering": ["watering_frequency", "watering"],
    "lighting": ["light"],
    "propagation": ["propagation"],
    "substrate": ["substrate"],
    "pruning": ["care"],
    "season": ["care"],
    "toxicity": ["precautions"],
    "problem": ["care", "precautions"],
    "plant_care": ["care", "light", "watering"],
}
MARKERS = {
    "pruning": ["poda", "podar", "cortar"],
    "season": ["epoca", "estacao", "primavera", "inverno", "verao", "outono", "periodo"],
    "toxicity": ["toxic", "venenos", "ingest", "oxalato", "irritacao"],
    "pesticides": ["defensiv", "dosagem", "agrotoxic", "inseticid"],
}


def aspect(question, memory):
    q = normalized(question)
    if re.search(
        r"\b(?:atualmente|mais recente|surto|alerta atual|ultimas recomendacoes|doenca atual|ocorrendo.*atualmente)\b",
        q,
    ):
        return "current"
    if any(w in q for w in MARKERS["pesticides"]):
        return "pesticides"
    if any(w in q for w in ["propaga", "multiplicar", "muda", "estaquia", "enxert", "sementes"]):
        return "propagation"
    if any(w in q for w in ["substrato", "solo", "terra para"]):
        return "substrate"
    if any(w in q for w in ["epoca", "qual mes", "quando podar", "qual estacao"]):
        return "season"
    if any(w in q for w in MARKERS["pruning"]):
        return "pruning"
    return memory.intent if memory.intent in ASPECT_FIELDS else "plant_care"


def sufficient(species, topic, question):
    if topic in {"current", "pesticides"}:
        return False
    fields = ASPECT_FIELDS.get(topic, ["care"])
    values = " ".join(getattr(species, field, "") or "" for field in fields)
    if topic == "problem":
        q = normalized(question)
        specific = [w for w in ["fungo", "acaro", "praga", "bichinhos", "doenca"] if w in q]
        if not specific:
            return bool(getattr(species, "light", "") and getattr(species, "watering", ""))
        return all(w in normalized(values) for w in specific)
    if not values.strip():
        return False
    if topic in MARKERS:
        return any(marker in normalized(values) for marker in MARKERS[topic])
    return True


def public_query(text):
    if re.search(
        r"https?://|@|\d{8,}|\b(?:sk-|tvly-)|\b(?:cliente|fornecedor|cpf|cnpj|telefone|pedido|orcamento|agenda|financeiro|senha|token|api_key|api|credenciais|chaves|segredos)\b",
        normalized(text),
    ):
        return None
    # Public botanical questions only; commercial/person-specific intents never reach this.
    return " ".join(re.findall(r"[A-Za-zÀ-ÿ]+", text))[:180]
