"""Read-only, authorized retrieval shared by catalogue and local inference."""

import re
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import select

from .assistant_language import (
    catalogue_mentions,
    recommendation_request,
    reported_plants,
    spelling_candidates,
)
from .assistant_observations import reported_group
from .assistant_text import understood_text
from .business import normalized
from .models import Article, Product, Project, Quote, Service, Species
from .plant_groups import plant_groups


def money(cents):
    return f"R$ {cents / 100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def source_list(rows):
    found = {}
    for row in rows:
        for source in row.sources or []:
            if isinstance(source, dict):
                url = source.get("url", "")
                if urlparse(url).scheme in {"http", "https"} and urlparse(url).netloc:
                    found[url] = {
                        "title": source.get("title") or source.get("name") or "Fonte botânica",
                        "url": url,
                    }
    return list(found.values())[:6]


def action(kind, row, label):
    return {"kind": kind, "id": row.id, "label": label}


def retrieve(db, user, question, context, history, reported_name=None):
    question = understood_text(question)
    query = normalized(question)
    ctx = context or {}
    selected, articles, services, project = [], [], [], None
    effective = dict(ctx)
    if ctx:
        cls = {
            "species": Species,
            "product": Product,
            "article": Article,
            "project": Project,
            "quote": Quote,
        }[ctx["kind"]]
        row = db.get(cls, ctx["id"])
        if not row or (cls in {Project, Quote} and row.customer_id != user.id):
            raise HTTPException(404, "Contexto não encontrado.")
        if cls is Product and not row.active:
            raise HTTPException(404, "Produto indisponível.")
        if cls is Species:
            selected = [row]
        elif cls is Product and row.species_id:
            selected = [db.get(Species, row.species_id)]
        elif cls is Article:
            articles = [row]
            selected = [db.get(Species, row.species_id)]
        elif cls in {Project, Quote}:
            project = row
            selected = [db.get(Species, p["species_id"]) for p in row.plants[:4]]
    species = list(db.scalars(select(Species).order_by(Species.name)))
    direct = catalogue_mentions(question, species)
    reported = reported_plants(question, allow_bare=bool(reported_name))
    group_report = reported_group(question)
    if group_report and not reported and not direct and not project:
        selected, ctx, effective = [], {}, {}
    candidates = spelling_candidates(reported_name, species) if reported_name and not direct else []
    uncertain = direct and re.search(
        r"\b(?:acho que e|parece ser|talvez seja|nao sei se e|pode ser uma?)\b", query
    )
    if uncertain:
        candidates = direct
    if direct and not project and {s.id for s in direct} != {s.id for s in selected if s}:
        ctx = {}
        effective = {}
    if direct and not ctx:
        selected = direct[:4]
    elif direct and project:
        selected = [s for s in direct if any(p.get("species_id") == s.id for p in project.plants)][
            :4
        ] or selected
    if not selected and not ctx and not reported and not group_report:
        # A follow-up can reuse the most recent grounded species, never another user's context.
        if any(w in query for w in ["essa", "dela", "regar", "rega", "adubar", "luz", "poda"]):
            for msg in reversed(history):
                previous = msg.context or {}
                if previous.get("kind") == "species":
                    candidate = db.get(Species, previous.get("id"))
                    if candidate:
                        selected = [candidate]
                    break
    group_tokens = [
        ("cacto", "cacto"),
        ("frutifer", "frutifer"),
        ("suculenta", "suculenta"),
        ("folhagen", "folhagen"),
        ("flor", "flor"),
        ("palmeira", "palmeira"),
        ("samambaia", "samambaia"),
        ("trepadeira", "trepadeira"),
        ("cerca viva", "cerca viva"),
        ("aromatic", "aromatic"),
        ("tempero", "tempero"),
        ("ornamental", "ornamenta"),
    ]
    wanted = [group for token, group in group_tokens if token in query]
    recommendations = False
    recommendation_preferences = {}
    if recommendation_request(question) and not reported and not project:
        selected = []
        ctx = {}
        effective = {}
    if (
        not selected
        and not reported
        and not candidates
        and not group_report
        and (
            recommendation_request(question)
            or normalized(question).strip(" .!?")
            in {"suculentas", "cactos", "frutiferas", "folhagens"}
            or any(
                w in query
                for w in [
                    "combinam",
                    "escolher",
                    "indicar",
                    "recomend",
                ]
            )
        )
    ):

        def matches(s):
            groups = normalized(" ".join(plant_groups(s)))
            return (
                (not wanted or any(group in groups for group in wanted))
                and ("pequeno" not in query or "pequeno" in normalized(s.size))
                and (
                    "baixa manutencao" not in query
                    or normalized(s.difficulty) in {"facil", "baixa"}
                )
                and ("cacto" not in query or "cacto" in groups)
                and ("frutifer" not in query or "frutifer" in groups)
                and ("suculenta" not in query or "suculenta" in groups)
                and ("sol pleno" not in query or normalized(s.light) == "sol pleno")
                and ("sol direto" not in query or "sol pleno" in normalized(s.light))
                and ("sombra" not in query or "sombra" in normalized(s.light))
                and (
                    "claridade indireta" not in query
                    and "luz indireta" not in query
                    or "sombra" in normalized(s.light)
                    or "indireta" in normalized(s.light)
                )
                and (
                    not any(w in query for w in ["interno", "apartamento", "dentro de casa"])
                    or "interno" in normalized(s.environment)
                )
            )

        selected = [s for s in species if matches(s)][:4]
        recommendations = bool(selected)
        if any(w in query for w in ["interno", "apartamento", "dentro de casa"]):
            recommendation_preferences["environment"] = "interno"
    if uncertain:
        selected = []
    selected = [s for s in selected if s]
    if len(selected) == 1 and not ctx:
        effective = {"kind": "species", "id": selected[0].id, "label": selected[0].name}
    if selected and not articles:
        articles = list(
            db.scalars(
                select(Article).where(Article.species_id.in_([s.id for s in selected])).limit(2)
            )
        )
    if any(
        w in query for w in ["servico", "orcamento", "paisag", "jardim", "consultoria", "poda"]
    ) and (not project or any(w in query for w in ["servico", "contratar", "consultoria"])):
        active = list(db.scalars(select(Service).where(Service.active).order_by(Service.id)))
        services = [s for s in active if normalized(s.name) in query]
        if not services and any(w in query for w in ["planejar", "projeto"]):
            services = [s for s in active if s.category == "Projeto"][:3]
        if not services:
            services = [
                s
                for s in active
                if ("virtual" in query and s.delivery_mode == "Virtual")
                or ("poda" in query and "poda" in normalized(s.name))
                or ("jardim" in query and "manutencao" in normalized(s.name))
                or (any(w in query for w in ["planejar", "projeto"]) and s.category == "Projeto")
                or ("consultoria" in normalized(s.name))
            ][:3]
    products = (
        list(
            db.scalars(
                select(Product)
                .where(Product.active, Product.species_id.in_([s.id for s in selected]))
                .limit(4)
            )
        )
        if selected
        else []
    )
    # Explicit product context also supports products without a botanical species.
    if ctx.get("kind") == "product":
        products = [db.get(Product, ctx["id"])]
    if ctx.get("kind") == "product":
        effective["label"] = products[0].name
    elif ctx.get("kind") == "article":
        effective["label"] = articles[0].title
    elif project:
        effective["label"] = getattr(project, "name", "Levantamento do orçamento")
    elif selected and ctx:
        effective["label"] = selected[0].name
    records = {
        "reported_group": group_report,
        "species": [
            {
                k: getattr(s, k)[:600]
                for k in [
                    "name",
                    "scientific_name",
                    "light",
                    "watering_frequency",
                    "watering",
                    "environment",
                    "difficulty",
                    "care",
                    "substrate",
                    "propagation",
                    "precautions",
                ]
            }
            for s in selected
        ],
        "guides": [
            {"title": a.title, "summary": a.summary[:600], "sections": a.sections[:3]}
            for a in articles
        ],
        "products": [
            {"name": p.name, "price": money(p.price_cents), "stock": p.stock} for p in products
        ],
        "services": [
            {
                "name": s.name,
                "description": s.description[:600],
                "reference_price": money(s.price_cents),
                "mode": s.delivery_mode,
            }
            for s in services
        ],
    }
    if project:
        brief = project.brief or {}
        records["planning"] = {
            "area": project.area,
            "status": project.status,
            "light": brief.get("light"),
            "maintenance": brief.get("maintenance"),
            "width": brief.get("width"),
            "length": brief.get("length"),
        }
    actions = [action("open_species", s, f"Conhecer {s.name}") for s in selected[:2]]
    actions += [action("open_article", a, a.title) for a in articles[:2]]
    if any(w in query for w in ["comprar", "preco", "estoque", "disponivel", "quanto", "valor"]):
        actions += [action("open_product", p, f"Ver {p.name} na loja") for p in products[:2]]
    actions += [action("open_service", s, s.name) for s in services[:2]]
    if services and any(w in query for w in ["orcamento", "contratar", "solicitar"]):
        actions += [action("request_quote", services[0], "Solicitar orçamento")]
    return {
        "records": records,
        "species": selected,
        "articles": articles,
        "services": services,
        "products": products,
        "sources": source_list(selected + articles),
        "actions": actions,
        "context": effective,
        "project": project,
        "mentioned_species": direct,
        "identity_candidates": candidates,
        "recommendations": recommendations,
        "recommendation_preferences": recommendation_preferences,
    }


def catalog_answer(question, facts):
    q = normalized(question)
    selected, products, services = facts["species"], facts["products"], facts["services"]
    if facts["project"] and any(
        w in q for w in ["metragem", "dimens", "medida", "levantamento", "area", "planejamento"]
    ):
        project = facts["project"]
        brief = project.brief or {}
        dimensions = (
            f" Medidas registradas: {brief['width']:g} × {brief['length']:g} m."
            if brief.get("width") and brief.get("length")
            else " As medidas ainda precisam ser completadas no planejador."
        )
        return f"Seu levantamento tem {project.area:g} m².{dimensions}\n\nLuminosidade: {brief.get('light') or 'a avaliar'}. Manutenção: {brief.get('maintenance') or 'a definir'}.\n\nAs mudanças devem ser revisadas no planejador antes da proposta. Qual informação você quer completar?"
    if products and any(
        w in q for w in ["preco", "estoque", "disponivel", "quanto", "valor", "comprar"]
    ):
        return "Confira os dados atuais da loja:\n\n" + "\n".join(
            f"• {p.name}: {money(p.price_cents)}; {p.stock} unidade(s) disponíveis."
            for p in products
        )
    if services and (
        not selected
        or any(w in q for w in ["servico", "orcamento", "contratar", "paisag", "consultoria"])
    ):
        return (
            "Estes serviços podem ajudar:\n\n"
            + "\n\n".join(
                f"• {s.name} ({s.delivery_mode.lower()}): {s.description or 'Consulte os detalhes do serviço.'}\nValor de referência: {money(s.price_cents)}; a proposta depende da avaliação do espaço."
                for s in services
            )
            + "\n\nAbra o serviço para conferir as entregas e solicitar um orçamento."
        )
    if len(selected) > 1:
        return (
            (
                "Estas são as espécies selecionadas no seu levantamento:\n\n"
                if facts["project"]
                else "Estas espécies do catálogo podem ser um ponto de partida:\n\n"
            )
            + "\n".join(
                f"• {s.name}: {s.light}; {s.environment}; manutenção {s.difficulty.lower()}."
                for s in selected
            )
            + (
                "\n\nAbra as fichas para conferir os cuidados específicos. A revisão das escolhas é feita com o paisagista."
                if facts["project"]
                else "\n\nSão opções iniciais, ainda sujeitas à avaliação do espaço. Quanto sol o local recebe por dia?"
            )
        )
    if selected:
        s = selected[0]
        topic = facts.get("_topic", "")
        if topic == "propagation":
            detail = (
                s.propagation
                or "O catálogo ainda não traz instruções verificadas de propagação para esta espécie."
            )
        elif topic in {"pruning", "season"}:
            detail = (
                s.care
                or "O catálogo ainda não traz orientação específica de poda para esta espécie."
            )
        elif topic == "toxicity":
            detail = (
                s.precautions
                or "O catálogo ainda não traz informação verificada de toxicidade para esta espécie."
            )
        elif any(w in q for w in ["nome cientifico", "nome botanico"]):
            detail = f"Nome botânico cadastrado: {s.scientific_name}."
        elif any(w in q for w in ["rega", "regar", "agua"]):
            detail = f"Rega: {(s.watering_frequency or s.watering).rstrip('. ')}."
        elif any(w in q for w in ["luz", "sol", "sombra"]):
            detail = f"Luminosidade: {s.light}. Ambiente: {s.environment}."
        elif any(w in q for w in ["solo", "substrato", "plantar", "plantio"]):
            detail = (
                s.substrate
                or s.care
                or "O catálogo ainda não traz instruções específicas de substrato para esta espécie."
            )
        else:
            detail = f"Luz: {s.light}.\nRega: {(s.watering_frequency or s.watering).rstrip('. ')}.\nAmbiente: {s.environment}.\n\n{s.care}"
        if s.precautions:
            detail += f"\n\nCuidados adicionais: {s.precautions}"
        return f"Vamos cuidar de {s.name} 🌿\n\n{detail}\n\nVocê cultiva essa planta em vaso ou diretamente no solo?"
    if facts["articles"]:
        a = facts["articles"][0]
        return f"No guia “{a.title}”, você encontra:\n\n{a.summary}\n\nAbra o guia abaixo para acompanhar as etapas."
    if facts["project"]:
        return f"Seu levantamento tem {facts['project'].area:g} m². Posso ajudar a revisar luminosidade, plantas e manutenção. As mudanças são feitas no planejador e revisadas antes da proposta. Qual parte você quer entender?"
    if any(w in q for w in ["ola", "oi", "bom dia", "ajuda", "obrigad"]):
        return "Estou por aqui para ajudar 🌿 Posso consultar cuidados das plantas, guias e serviços do Ateliê Verde. Qual planta ou espaço você quer cuidar?"
    return "Para orientar você com os dados do catálogo, preciso identificar a planta. Qual é o nome dela? Se não souber, a consultoria pode ajudar a avaliar seu caso."


def grounded_text(text, facts):
    if not isinstance(text, str) or not text.strip() or len(text) > 4000 or "<" in text:
        return False
    allowed = {p.price_cents for p in facts["products"]} | {
        s.price_cents for s in facts["services"]
    }
    amounts = re.findall(r"R\$\s*(\d+(?:\.\d{3})*(?:,\d{2})?)\b", text)
    if text.count("R$") != len(amounts):
        return False
    for amount in amounts:
        reais, _, cents = amount.replace(".", "").partition(",")
        if int(reais) * 100 + int(cents or 0) not in allowed:
            return False
    return True
