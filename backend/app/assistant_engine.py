"""Hybrid orchestration: read-only tools, typed state, local semantics and factual provenance."""

import logging
import re
import time
from datetime import timedelta

from sqlalchemy import select

from . import assistant_runtime
from .assistant_ai import generate as generate_ai
from .assistant_botany import follows_reference, reference_for, substantive_reply, supported_answer
from .assistant_budget import Budget
from .assistant_dialogue import replay_reason
from .assistant_emotions import EXPRESSIONS, reaction
from .assistant_hybrid_search import research_reply
from .assistant_installation import settings as research_settings
from .assistant_knowledge import action, catalog_answer, money, retrieve
from .assistant_language import (
    catalogue_mentions,
    current_symptoms,
    field_values,
    is_question,
    missed_watering,
    name_key,
    reported_plants,
    selection,
)
from .assistant_observations import GENERAL_MOISTURE_GUIDANCE, care_observations
from .assistant_request import cloud_permitted
from .assistant_research import BOTANICAL_NAMES, cache_get, canonical, source_summary
from .assistant_research import research as research
from .assistant_routing import aspect, public_query
from .assistant_state import (
    COMMERCIAL,
    FIELD_LABELS,
    Memory,
    SemanticReply,
    advance,
    ask,
    declared_plant,
    intent_of,
    merge_semantics,
    next_field,
    read_memory,
)
from .assistant_text import understood_text
from .assistant_web_search import explicit_search, identification_clues, should_search_web
from .business import normalized
from .clock import today
from .models import Appointment, Order, Product, Project, Quote, Service, Setting, User

logger = logging.getLogger("rafinha")
PUBLIC_COMMERCE = {"product", "price", "stock", "service"}


def decide_web(memory, facts):
    return should_search_web(memory, facts)


def commercial_facts(db, question, memory, facts):
    q = normalized(question)
    if memory.intent == "customers":
        rows = (
            list(
                db.scalars(
                    select(User).where(User.role == "customer", User.active).order_by(User.name)
                )
            )
            if facts.get("_actor_role") == "admin"
            else []
        )
        if any(w in q for w in ["telefone", "email", "e-mail"]):
            rows = catalogue_mentions(question, rows, fields=("name", "customer_code"))
            facts["records"]["customer_contact_query"] = True
        facts["records"]["customers"] = [
            {"name": u.name, "city": u.city, "phone": u.phone, "email": u.email} for u in rows[:10]
        ]
    if memory.intent == "schedule":
        query = select(Appointment).where(
            Appointment.date >= today().isoformat(), Appointment.status != "Cancelado"
        )
        if facts.get("_actor_role") != "admin":
            query = query.where(Appointment.customer_id == facts["_owner_id"])
        if "hoje" in q:
            query = query.where(Appointment.date == today().isoformat())
        elif "esta semana" in q:
            week_end = today() + timedelta(days=6 - today().weekday())
            query = query.where(Appointment.date <= week_end.isoformat())
        rows = list(db.scalars(query.order_by(Appointment.date, Appointment.start_time).limit(5)))
        facts["records"]["schedule"] = [
            {
                "title": a.title,
                "date": a.date,
                "start": a.start_time,
                "end": a.end_time,
                "status": a.status,
            }
            for a in rows
        ]
    if memory.intent == "orders":
        rows = list(
            db.scalars(
                select(Order)
                .where(Order.customer_id == facts["_owner_id"])
                .order_by(Order.id.desc())
                .limit(5)
            )
        )
        facts["records"]["orders"] = [
            {"code": str(o.id), "status": o.status, "total": money(o.total_cents)} for o in rows
        ]
    if (
        memory.intent == "project"
        and not facts["project"]
        and any(
            w in q
            for w in [
                "meu projeto",
                "meus projetos",
                "quais",
                "qual projeto",
                "mostrar",
                "liste",
                "andamento",
                "atrasad",
            ]
        )
    ):
        query = select(Project)
        if facts.get("_actor_role") != "admin":
            query = query.where(Project.customer_id == facts["_owner_id"])
        if "atrasad" in q:
            query = query.where(
                Project.end_date != "",
                Project.end_date < today().isoformat(),
                Project.status.in_(["Aprovado", "Planejamento", "Execução"]),
            )
        elif "andamento" in q:
            query = query.where(Project.status.in_(["Aprovado", "Planejamento", "Execução"]))
        facts["records"]["projects_query"] = True
        rows = list(db.scalars(query.order_by(Project.id.desc()).limit(5)))
        facts["records"]["projects"] = [
            {"name": p.name, "status": p.status, "area": p.area, "value": money(p.budget_cents)}
            for p in rows
        ]
    if memory.intent == "quote" and "meu" in q:
        query = select(Quote)
        if facts.get("_actor_role") != "admin":
            query = query.where(Quote.customer_id == facts["_owner_id"])
        rows = list(db.scalars(query.order_by(Quote.id.desc()).limit(5)))
        facts["records"]["quotes"] = [
            {"code": q.code, "status": q.status, "value": money(q.amount_cents)} for q in rows
        ]
    if memory.intent in {"service", "quote", "project"} and not facts["project"]:
        all_services = list(db.scalars(select(Service).where(Service.active)))
        terms = [w.rstrip("s") for w in q.split() if len(w) > 3]
        scored = [
            (
                sum(
                    w in normalized(s.name + " " + s.category + " " + s.description) for w in terms
                ),
                s,
            )
            for s in all_services
        ]
        found = [
            s for score, s in sorted(scored, key=lambda pair: pair[0], reverse=True) if score > 0
        ][:3]
        exact = [s for s in all_services if normalized(s.name) in q]
        if exact:
            found = exact[:3]
        facts["services"] = found or all_services[:3]
        facts["species"] = []
        facts["products"] = []
        facts["articles"] = []
        facts["sources"] = []
        facts["records"] = {
            **{
                k: v
                for k, v in facts["records"].items()
                if k in {"projects", "quotes", "projects_query"}
            },
            "services": [
                {
                    "name": s.name,
                    "description": s.description[:400],
                    "price": money(s.price_cents),
                    "mode": s.delivery_mode,
                }
                for s in facts["services"]
            ],
        }
        facts["actions"] = [action("open_service", s, s.name) for s in facts["services"]]
        if memory.intent == "quote" and facts["services"]:
            facts["actions"].append(
                action("request_quote", facts["services"][0], "Solicitar orçamento")
            )
        facts["context"] = {}
    if memory.intent in {"product", "price", "stock"} and not facts["products"]:
        products = list(db.scalars(select(Product).where(Product.active)))
        if memory.product_id and (
            q.strip(" ?.") in {"tem estoque", "quanto custa", "qual o preco", "qual o valor"}
            or any(w in q.split() for w in ["esse", "essa", "ele", "ela"])
        ):
            previous = next((p for p in products if p.id == memory.product_id), None)
            if previous:
                facts["products"] = [previous]
        text = normalized(memory.slots.get("product_name", question))
        if "product_name" not in memory.slots:
            reported = re.search(
                r"(?:quanto custa|preco (?:do|da)|valor (?:do|da))\s+(.+)", normalized(question)
            )
            if reported and reported.group(1).strip(" ?.") not in {
                "esse produto",
                "este produto",
                "o produto",
                "isso",
                "esse",
                "essa",
                "ele",
                "ela",
            }:
                memory.slots["product_name"] = reported.group(1).strip(" ?.")[:180]
        exact = catalogue_mentions(text, products, fields=("name", "sku"))
        if exact:
            facts["products"] = exact[:3]
        elif "fertilizante" in q:
            facts["products"] = [p for p in products if p.category == "Fertilizantes"][:3]
        if facts["products"]:
            facts["records"]["products"] = [
                {"name": p.name, "price": money(p.price_cents), "stock": p.stock}
                for p in facts["products"]
            ]
            facts["actions"] = [
                action("open_product", p, "Ver " + p.name) for p in facts["products"]
            ]
    if len(facts["products"]) == 1:
        memory.product_id = facts["products"][0].id
        memory.slots["product_name"] = facts["products"][0].name
    if memory.intent == "stock" and any(
        w in q for w in ["quantas", "quantos", "total", "minimo", "abaixo"]
    ):
        rows = list(db.scalars(select(Product).where(Product.active)))
        if "plantas" in q:
            rows = [p for p in rows if p.category == "Plantas"]
        if any(w in q for w in ["minimo", "abaixo"]):
            facts["_private_query"] = True
            if facts.get("_actor_role") != "admin":
                facts["records"]["inventory_denied"] = True
            else:
                facts["records"]["low_inventory"] = [
                    {"name": p.name, "stock": p.stock, "minimum": p.low_stock}
                    for p in rows
                    if p.stock < p.low_stock or ("abaixo" not in q and p.stock == p.low_stock)
                ]
        else:
            facts["records"]["inventory_summary"] = {
                "units": sum(p.stock for p in rows),
                "products": len(rows),
            }
    if memory.intent in COMMERCIAL:
        facts["sources"] = []
    if memory.intent == "company":
        setting = db.get(Setting, 1)
        facts["records"] = {
            "company": {
                k: (setting.value if setting else {}).get(k, "")
                for k in ["name", "phone", "email", "address"]
            }
        }
        facts["actions"] = []
        facts["sources"] = []


def fallback(question, memory, facts, research_result):
    q = normalized(question)
    if facts["records"].get("inventory_denied"):
        return (
            "A consulta de estoque mínimo está disponível para o administrador. Posso conferir a disponibilidade dos produtos da loja para você.",
            "company",
        )
    if "low_inventory" in facts["records"]:
        rows = facts["records"]["low_inventory"]
        return (
            "Estes produtos precisam de atenção no estoque:\n\n"
            + "\n".join(
                f"• {r['name']}: {r['stock']} unidade(s), mínimo {r['minimum']}." for r in rows
            )
            if rows
            else "Nenhum produto ativo está no estoque mínimo ou abaixo dele."
        ), "company"
    if "inventory_summary" in facts["records"]:
        info = facts["records"]["inventory_summary"]
        return (
            f"O estoque atual tem {info['units']} unidade(s), distribuídas em {info['products']} produto(s) ativos.",
            "catalog",
        )
    if facts["records"].get("projects_query") and not facts["records"].get("projects"):
        return (
            "Não encontrei projetos que correspondam a essa consulta nos registros aos quais você tem acesso.",
            "company",
        )
    if memory.intent == "identity":
        return (
            "Eu sou o Rafinha 🌿, o assistente virtual do Ateliê Verde. Posso ajudar com plantas, cuidados, produtos, serviços e o acompanhamento das suas solicitações.",
            "general",
        )
    if memory.intent in {"customers", "schedule", "orders"}:
        kind = memory.intent
        if kind == "customers" and facts.get("_actor_role") != "admin":
            return (
                "A lista de clientes está disponível apenas para o administrador. Posso ajudar com seus próprios serviços e solicitações.",
                "company",
            )
        rows = facts["records"].get(kind, [])
        if not rows:
            return "Não encontrei essa informação cadastrada no sistema.", "company"
        if facts["records"].get("customer_contact_query"):
            field = "phone" if "telefone" in q else "email"
            return "\n".join(
                f"{r['name']}: {r[field] or 'não cadastrado'}." for r in rows
            ), "company"
        if kind == "schedule":
            return "Seus próximos compromissos:\n\n" + "\n".join(
                f"• {r['title']} · {r['date']} · {r['start']}–{r['end']} · {r['status']}"
                for r in rows
            ), "company"
        if kind == "orders":
            return "Seus pedidos cadastrados:\n\n" + "\n".join(
                f"• Pedido {r['code']} · {r['status']} · {r['total']}" for r in rows
            ), "company"
        return "Clientes cadastrados:\n\n" + "\n".join(
            f"• {r['name']}" + (f" · {r['city']}" if r["city"] else "") for r in rows
        ), "company"
    if facts["records"].get("projects"):
        return "Seus projetos cadastrados:\n\n" + "\n".join(
            f"• {r['name']} · {r['status']} · {r['area']:g} m² · {r['value']}"
            for r in facts["records"]["projects"]
        ), "company"
    if facts["records"].get("quotes"):
        return "Seus orçamentos cadastrados:\n\n" + "\n".join(
            f"• {r['code']} · {r['status']} · {r['value']}" for r in facts["records"]["quotes"]
        ), "company"
    if facts.get("_topic") == "current" and not research_result.get("documents"):
        return (
            "Não encontrei fontes atuais verificadas para essa informação. A base disponível não confirma o que está ocorrendo agora nessa região; não vou apresentar uma doença ou recomendação como confirmada. Podemos consultar uma referência técnica específica quando houver uma fonte confiável disponível.",
            "research_unavailable",
        )
    if facts.get("_requested_missing") and not research_result.get("documents"):
        labels = {
            "propagation": "propagação",
            "substrate": "substrato",
            "pruning": "poda",
            "season": "época de poda",
            "toxicity": "toxicidade",
            "pesticides": "controle técnico de pragas",
        }
        topic = facts.get("_topic")
        if topic in labels:
            return (
                f"Não encontrei orientação verificada sobre {labels[topic]} para {memory.plant_name}. A ficha atual não cobre esse ponto e a consulta externa não trouxe uma confirmação. Podemos conferir uma fonte técnica específica ou levar essa dúvida à consultoria.",
                "research_unavailable",
            )
    if any(w in q for w in ["gato comeu", "cachorro comeu", "ingeriu", "crianca comeu"]):
        return (
            "Procure orientação veterinária ou médica adequada agora, especialmente se houver sintomas. Não vou recomendar tratamentos caseiros. Se possível, leve uma foto ou amostra da planta para auxiliar o atendimento.",
            "care",
        )
    observed = facts.get("_observations", {})
    if missed_watering(question) and current_symptoms(question):
        prompt = ask(memory, "soil_moisture")
        if prompt:
            prompt = "A terra está seca ou ainda úmida?"
            memory.pending_question = prompt
        return (
            "A murcha pode ter diferentes causas, então vamos conferir antes de decidir a próxima rega.\n\n"
            "1. **Confira a umidade do substrato.** O relato de falta de rega ajuda, mas a aparência sozinha não confirma o que aconteceu.\n"
            "2. Se estiver em vaso, verifique se a água consegue escoar e retire água acumulada no pratinho.\n"
            "3. Observe se folhas e caule estão secos, moles ou mudando de cor. Esses sinais ajudam a escolher o próximo cuidado.\n\n"
            + (prompt or "Podemos acompanhar o que mudou desde o último cuidado."),
            "care",
        )
    if observed.get("excess_watering") or observed.get("wet_soil"):
        prompt = ask(memory, "soil_moisture")
        return (
            "Entendi: você relatou bastante água"
            + (" e ausência de sol direto" if observed.get("no_direct_sun") else "")
            + ". Isso merece atenção, mas não confirma uma doença.\n\n"
            + "1. **Confira a umidade antes de regar novamente.** Evite acrescentar água enquanto o substrato estiver muito molhado.\n"
            + "2. Verifique se o vaso escoa bem e se há água acumulada no pratinho.\n"
            + "3. A luz deve ser ajustada ao tipo de planta; falta de sol direto não significa necessariamente falta de claridade.\n\n"
            + (
                prompt
                or "Observe também se as folhas e o caule estão firmes ou apresentam mudanças; isso ajuda a avaliar o próximo cuidado."
            ),
            "care",
        )
    if memory.plant_choices and memory.intent not in COMMERCIAL:
        question_next = ask(memory, "plant_selection")
        prefix = (
            "Encontrei um nome parecido no catálogo, mas preciso confirmar antes de orientar. "
            if facts.get("identity_candidates")
            else "Você mencionou mais de uma planta. Podemos tratar uma por vez. "
        )
        return prefix + (
            question_next or "Pode escolher uma delas ou corrigir o nome informado."
        ), "identification"
    if facts.get("recommendations") and memory.intent not in COMMERCIAL:
        items = "\n".join(
            f"• {s.name}: {s.light}; {s.environment}; manutenção {s.difficulty.lower()}."
            for s in facts["species"]
        )
        return (
            "A melhor escolha depende da luz e do espaço disponível. Estas opções do catálogo podem ajudar:\n\n"
            + items
            + "\n\nAbra as fichas para comparar os cuidados e confirmar a adequação ao seu espaço."
            + ("\n\n" + question_next if (question_next := ask(memory, "lighting")) else ""),
            "catalog",
        )
    if facts.get("_dialogue_opening"):
        extra = ask(memory, "care_goal")
        if not extra and not memory.slots.get("care_goal"):
            extra = "Você quer cuidados gerais ou ajuda com algum problema nela?"
            memory.pending_field = "care_goal"
            memory.pending_question = extra
        opening = (
            f"Já estou considerando {memory.plant_name} 🌿. "
            if facts.get("_repeated_plant_introduction")
            else f"Claro 🌿 Vamos falar de {memory.plant_name}. "
        )
        return opening + (extra or "Me conte em que você gostaria de ajuda."), "care"
    if reference := facts.get("_botanical_support"):
        return supported_answer(reference, memory), "identification" if reference[
            "kind"
        ] == "identification" else "care"
    if (
        memory.slots.get("plant_group")
        and not memory.plant_name
        and memory.intent in {"general", "plant_care", "identification"}
    ):
        if memory.slots.get("description"):
            prompt = ask(memory, "photo")
            return (
                "Essa aparência é uma pista útil, mas ainda não confirma a espécie. "
                "Vou manter a descrição para continuarmos os cuidados. "
                + (prompt or "Como estão as folhas agora?"),
                "care",
            )
        prompt = ask(memory, "care_goal")
        return "Você já contou que é uma " + memory.slots[
            "plant_group"
        ] + ". Podemos começar pelos cuidados gerais sem confirmar a variedade. " + (
            prompt or "Me conte qual mudança você percebeu nela."
        ), "care"
    if memory.intent == "greeting":
        return "Oi! Que bom ter você por aqui 🌿 Como posso ajudar com seu espaço verde?", "general"
    if memory.intent == "casual":
        if any(
            event in q
            for event in ["projeto finalizado", "orcamento aprovado", "servico concluido"]
        ):
            return (
                "Que boa notícia! 🌿 Podemos conferir o acompanhamento e os próximos cuidados nos registros do sistema quando você quiser.",
                "general",
            )
        if any(w in q for w in ["morreu", "perdi", "nao resistiu"]):
            return (
                "Sinto pela perda da sua planta. Se quiser, podemos conversar sobre o que aconteceu e pensar nos próximos cuidados, sem atribuir uma causa sem avaliar.",
                "general",
            )
        if "floresc" in q:
            return (
                "Que alegria ver essa conquista! A primeira flor merece ser celebrada 🌸",
                "general",
            )
        if "melhor" in q or "brot" in q or reaction(question)["final"] == "relieved":
            return (
                "Que bom saber que ela está melhorando. Vamos continuar acompanhando com calma e manter os cuidados adequados à espécie.",
                "care",
            )
        return "Fico feliz em ajudar! Pode me contar quando surgir outra dúvida.", "general"
    if memory.intent == "company":
        info = facts["records"].get("company", {})
        key = (
            "phone"
            if "telefone" in q
            else "email"
            if "email" in q
            else "address"
            if "endereco" in q
            else None
        )
        return (
            f"O contato cadastrado é {info[key]}."
            if key and info.get(key)
            else "Essa informação ainda não está cadastrada nos dados da loja."
        ), "company"
    if memory.intent in {"price", "stock", "product"}:
        if facts["products"]:
            return "\n".join(
                f"{p.name}: {money(p.price_cents)}, com {p.stock} unidade(s) em estoque."
                for p in facts["products"]
            ), "catalog"
        if memory.slots.get("product_name"):
            return (
                f"Não localizei “{memory.slots['product_name']}” entre os produtos cadastrados da loja. Você pode conferir o nome ou escolher um item no catálogo.",
                "catalog",
            )
        prompt = ask(memory, "product_name")
        return (
            prompt or "Podemos seguir por um item do catálogo para conferir os dados da loja.",
            "catalog",
        )
    if memory.intent in {"service", "quote", "project"} and facts["services"]:
        return catalog_answer(question, facts), "services"
    if memory.last_answered and not is_question(question) and memory.intent not in COMMERCIAL:
        value = memory.slots.get(memory.last_answered)
        ack = {
            "environment": f"Certo, ela fica em ambiente {value}.",
            "lighting": f"Entendi, o local tem {value}.",
            "watering": "Entendi como está a rega.",
            "symptoms": "Entendi a mudança que você percebeu.",
        }.get(memory.last_answered, "Isso ajuda a entender as condições da sua planta.")
        if not value:
            ack = "Sem problema, vamos seguir com as informações que você consegue trazer."
        extra = ask(memory, next_field(memory))
        return ack + (
            " " + extra
            if extra
            else " Podemos comparar essas condições com a ficha e acompanhar as mudanças na planta."
        ), "web" if research_result.get("documents") else "care"
    if memory.intent == "recommendation":
        return (
            "Não encontrei opções cadastradas que correspondam a esse espaço. Quanto sol ou claridade o local recebe?",
            "catalog",
        )
    if research_result.get("documents"):
        summary = source_summary(research_result["documents"], facts.get("_topic", "plant_care"))
        if summary:
            extra = ask(memory, next_field(memory))
            scope = (
                " A referência é geral para o gênero; a variedade ainda não foi confirmada."
                if any(d.get("scope") == "genus" for d in research_result["documents"])
                else ""
            )
            return (
                f"Encontrei uma referência institucional relacionada a {memory.plant_name}. {summary}{scope}"
                + ("\n\n" + extra if extra else ""),
                "web",
            )
        extra = ask(memory, next_field(memory))
        return (
            f"A fonte encontrada é uma referência para {memory.plant_name}, mas não esclarece esse cuidado nas condições que você descreveu."
            + (
                " " + extra
                if extra
                else " Você percebeu alguma mudança nas folhas ou no substrato?"
            ),
            "web",
        )
    if not memory.plant_name:
        field = next_field(memory)
        question_next = ask(memory, field)
        if question_next:
            prefix = (
                "Sem problema — vamos pelas características. "
                if "plant_name" in memory.known_unknowns
                else "Vamos descobrir isso juntos. "
            )
            return prefix + question_next, "identification"
        if memory.pending_field == "plant_name":
            return (
                "Posso ajudar com os cuidados; ainda falta identificar a planta. Você pode responder à pergunta anterior ou descrever suas características.",
                "identification",
            )
        summary = "; ".join(f"{FIELD_LABELS.get(k, k)}: {v}" for k, v in memory.slots.items())
        return (
            f"Já registrei as pistas que você conseguiu trazer{': ' + summary if summary else ''}. Não vou afirmar a espécie com esses dados. Podemos comparar fichas do catálogo ou buscar uma avaliação na consultoria.",
            "identification",
        )
    if facts["species"] or facts["project"]:
        text = catalog_answer(question, facts)
        text = text.replace("\n\nVocê cultiva essa planta em vaso ou diretamente no solo?", "")
        field = next_field(memory)
        extra = ask(memory, field)
        return text + ("\n\n" + extra if extra else ""), "care"
    field = next_field(memory)
    question_next = ask(memory, field)
    prefix = (
        "Não consegui consultar fontes externas agora. "
        if research_result.get("status") == "unavailable"
        else "Ainda não encontrei informação suficiente para confirmar os cuidados dessa espécie. "
    )
    acknowledged = f"Entendi, você tem {memory.plant_name}. " if not memory.last_answered else ""
    return acknowledged + prefix + (
        question_next or "Podemos conferir novas pistas ou buscar uma avaliação na consultoria."
    ), "research_unavailable"


def respond(
    db,
    user,
    question,
    context,
    history,
    previous,
    cancelled=lambda: False,
    progress=lambda phase: None,
    started_at=None,
    input_images=None,
    stream_reply=lambda text, expression: None,
):
    started = started_at or time.monotonic()
    # Leave time for persistence, delivery and the text reveal animation.
    installation_policy = research_settings()
    chatgpt_only = assistant_runtime.chatgpt_mode()
    selected_connection = (
        assistant_runtime.connection() if chatgpt_only and cloud_permitted.get() else None
    )
    personal = selected_connection[1] if selected_connection else {}
    response_timeout = (
        personal.get("response_timeout", 30)
        if chatgpt_only
        else installation_policy["response_timeout"]
    )
    budget = Budget(
        seconds=response_timeout - (3 if response_timeout > 10 else 2), started_at=started
    )
    progress("context")
    previous_memory = read_memory(previous)
    previous = previous_memory.model_dump()
    question = understood_text(question)
    q = normalized(question)
    reset_identity = "planta" in q and any(w in q for w in ["outra", "nova", "desconhecida"])
    if reset_identity:
        previous_memory = Memory(intent="plant_care")
        previous = previous_memory.model_dump()
        if not chatgpt_only:
            history = []
    intent = intent_of(question, previous_memory)
    names = reported_plants(
        question,
        allow_bare=(
            previous_memory.pending_field == "plant_name"
            or (
                not previous_memory.pending_field
                and not is_question(question)
                and not field_values(question)
            )
        ),
    )
    declared_from_text = declared_plant(question)
    if declared_from_text and name_key(declared_from_text) not in {
        name_key(name) for name in names
    }:
        names = [declared_from_text, *names]
    declared = names[0] if len(names) == 1 else None
    picked = selection(question, previous_memory.plant_choices, BOTANICAL_NAMES)
    if (names or picked) and intent_of(question, Memory()) == "general":
        intent = "plant_care"
        previous_memory.intent = intent
        previous = previous_memory.model_dump()
    retrieval_question = picked or question
    if (
        previous_memory.intent == "recommendation"
        and not names
        and not picked
        and not is_question(question)
        and intent not in COMMERCIAL
        and (new_preferences := field_values(question))
    ):
        preferences = {**previous_memory.slots, **new_preferences}
        retrieval_question = "Recomende plantas para " + " ".join(
            preferences.get(field, "") for field in ["environment", "lighting"]
        )
    if picked:
        declared = picked
    changing_identity = bool(
        declared
        and intent not in COMMERCIAL
        and previous_memory.plant_name
        and normalized(previous_memory.plant_name) not in normalized(declared)
    )
    if changing_identity and not chatgpt_only:
        history = []
    group_only = bool(
        not declared
        and (
            field_values(question).get("plant_group")
            or (previous_memory.slots.get("plant_group") and not previous_memory.plant_name)
        )
    )
    # Validate supplied context before replacing it; a topic change must never
    # bypass ownership checks on a project or quote.
    facts = retrieve(
        db, user, retrieval_question, context, [] if group_only else history, reported_name=declared
    )
    if context and (
        reset_identity
        or changing_identity
        or picked
        or (declared and not facts["mentioned_species"])
    ):
        context = None
        facts = retrieve(db, user, retrieval_question, None, [], reported_name=declared)
    if (
        not context
        and not changing_identity
        and not declared
        and not names
        and not group_only
        and not previous_memory.plant_choices
        and previous_memory.species_id
        and intent not in (COMMERCIAL | {"recommendation"})
        and not facts["species"]
    ):
        facts = retrieve(
            db, user, question, {"kind": "species", "id": previous_memory.species_id}, history
        )
    facts["selection_confirmed"] = bool(picked)
    memory = advance(previous, question, facts)
    if picked:
        memory.plant_choices = []
        memory.pending_field = None
        memory.asked = [f for f in memory.asked if f != "plant_selection"]
        if len(facts["species"]) == 1:
            memory.species_id = facts["species"][0].id
            memory.plant_name = facts["species"][0].name
            memory.slots["plant_name"] = memory.plant_name
        else:
            memory.species_id = None
            memory.plant_name = picked
            memory.slots["plant_name"] = picked
        if memory.intent not in COMMERCIAL:
            memory.intent = "plant_care"
    if facts["species"] and memory.intent == "general":
        memory.intent = "plant_care"
    if intent_of(question, Memory()) == "general" and not facts["species"]:
        products = catalogue_mentions(
            question,
            list(db.scalars(select(Product).where(Product.active))),
            fields=("name", "sku"),
        )
        if products and any(
            name_key(question) == name_key(getattr(p, f)) for p in products for f in ("name", "sku")
        ):
            memory.intent = "product"
            memory.plant_name = None
            memory.slots.pop("plant_name", None)
    facts["_owner_id"] = user.id
    facts["_actor_role"] = user.role
    facts["_topic"] = aspect(question, memory)
    facts["_question"] = question
    facts["_observations"] = care_observations(question)
    facts["_dialogue_opening"] = bool(
        memory.plant_name
        and not memory.plant_choices
        and memory.intent == "plant_care"
        and not is_question(question)
        and not field_values(question)
        and not any(
            w in q
            for w in ["cuidar", "cuidado", "como", "nao sei", "poda", "adub", "florac", "problema"]
        )
        and (
            not previous_memory.plant_name
            or previous_memory.pending_field == "plant_name"
            or (
                name_key(memory.plant_name) == name_key(previous_memory.plant_name)
                and not memory.slots.get("care_goal")
            )
        )
    )
    facts["_force_web"] = explicit_search(question)
    facts["_repeated_plant_introduction"] = bool(
        facts["_dialogue_opening"]
        and previous_memory.plant_name
        and name_key(previous_memory.plant_name) == name_key(memory.plant_name)
    )
    commercial_facts(db, question, memory, facts)
    support = (
        reference_for(memory, question)
        if memory.intent not in COMMERCIAL
        and not memory.plant_choices
        and not facts.get("recommendations")
        else None
    )
    facts["_botanical_support"] = support
    if support:
        facts["records"]["botanical_reference"] = {
            "kind": support["kind"],
            "label": support.get("label"),
            "family": support.get("family"),
            "guidance": supported_answer(support, memory),
            "status": "hypothesis" if support["kind"] == "identification" else "general",
        }
    progress("catalog")
    needs_web, reason = decide_web(memory, facts)
    facts["_requested_missing"] = needs_web
    research_name = (
        facts["species"][0].scientific_name if len(facts["species"]) == 1 else memory.plant_name
    )
    if facts["_topic"] == "current":
        research_name = public_query(question)
    contextual_answer = memory.last_answered and not any(
        w in normalized(question) for w in ["como", "qual", "quanto", "por que", "?"]
    )
    previous_research = cache_get(db, memory.research_key) if memory.research_key else None
    if (
        contextual_answer
        and not facts["_force_web"]
        and not identification_clues(memory, facts)
        and reason != "specific_plant_problem_needs_evidence"
        and facts["_topic"] not in {"current", "toxicity", "pesticides"}
    ):
        needs_web, reason = False, "answered_context_field"
    urgent = any(
        w in normalized(question)
        for w in ["gato comeu", "cachorro comeu", "ingeriu", "crianca comeu"]
    )
    if urgent:
        needs_web, reason = False, "urgent_referral"
    if not chatgpt_only and (
        not installation_policy["search_enabled"]
        or (installation_policy["mode"] == "on_request" and not facts["_force_web"])
    ):
        needs_web, reason = False, "administrator_search_policy"
    if chatgpt_only:
        if facts["_force_web"] and memory.intent not in COMMERCIAL and not urgent:
            # ChatGPT can research multiple reported plants. A tentative local
            # name parser must not suppress the user's explicit search request.
            needs_web, reason = True, "explicit_botanical_research"
        if (
            input_images
            and facts["_topic"] not in {"toxicity", "pesticides", "current"}
            and not facts["_force_web"]
        ):
            needs_web, reason = False, "visual_analysis_first"
        if (
            reason == "unknown_species"
            and not facts["_force_web"]
            and facts["_topic"] not in {"toxicity", "pesticides", "current"}
        ):
            needs_web, reason = False, "chatgpt_general_knowledge"
        if (
            reason == "identification_clues_need_external_evidence"
            and support
            and support["kind"] == "identification"
            and not personal.get("web_images", True)
            and not facts["_force_web"]
            and facts["_topic"] not in {"toxicity", "pesticides", "current"}
        ):
            needs_web, reason = False, "internal_identification_reference"
        if not personal.get("web_enabled") or (
            personal.get("web_mode") == "on_request" and not facts["_force_web"]
        ):
            needs_web, reason = False, "chatgpt_search_not_requested"
        if not selected_connection:
            needs_web, reason = False, "chatgpt_not_connected"
    native_search = bool(needs_web and not urgent)
    if needs_web and not public_query(question):
        native_search = False
        needs_web, reason = False, "non_public_query"
    facts["_requested_missing"] = needs_web
    facts["_identification_lookup"] = identification_clues(memory, facts)
    if memory.research_context and not needs_web:
        facts["records"]["previous_web_research"] = memory.research_context
        facts["sources"] = memory.research_context.get("sources", [])[:5]
    logger.info("[RAF_INTERNET_DECISION] needs_web_search=%s reason=%s", needs_web, reason)
    if needs_web:
        progress("research")
    result = {
        "documents": [],
        "sources": [],
        "status": "pending" if native_search else "not_needed",
    }
    if contextual_answer and previous_research and previous_research.get("documents"):
        result = {**previous_research, "cache": "context"}
    if needs_web and result.get("documents") and memory.plant_name:
        memory.research_key = canonical(
            research_name,
            facts["_topic"],
        )
    if result["documents"]:
        facts["records"]["external"] = [
            {
                "source": d["title"],
                "excerpt": d["excerpt"][:1800],
                "scope": d.get("scope", "species"),
            }
            for d in result["documents"]
        ]
        facts["sources"] = result["sources"]
    elif facts.get("_requested_missing") and facts["_topic"] in {
        "propagation",
        "substrate",
        "pruning",
        "season",
        "toxicity",
        "pesticides",
        "current",
    }:
        facts["sources"] = []
    facts["records"]["requested_subject"] = {
        "topic": facts["_topic"],
        "verified_content_missing": bool(
            facts.get("_requested_missing") and not result["documents"]
        ),
    }
    facts["records"]["session"] = memory.model_dump()
    facts["records"]["care_observations"] = facts["_observations"]
    if facts["_observations"].get("excess_watering") or facts["_observations"].get("wet_soil"):
        facts["records"]["general_moisture_guidance"] = GENERAL_MOISTURE_GUIDANCE["text"]
        if GENERAL_MOISTURE_GUIDANCE["source"] not in facts["sources"]:
            facts["sources"].append(GENERAL_MOISTURE_GUIDANCE["source"])
    if facts["_dialogue_opening"]:
        facts["records"]["dialogue_goal"] = (
            "O cliente já informou a planta. Reconheça o nome e pergunte que tipo de ajuda deseja; não pergunte o nome de novo nem comece um questionário de cultivo."
        )
    facts["_budget"] = budget
    facts["_response_timeout"] = response_timeout
    facts["_owner_id"] = user.id
    facts["_cancelled"] = cancelled
    facts["_explicit_cloud"] = any(
        w in q for w in ["use chatgpt", "usar chatgpt", "com chatgpt", "use openai", "com openai"]
    )
    public_conversation = memory.intent in PUBLIC_COMMERCE and not facts.get("_private_query")
    facts["_allow_cloud"] = bool(chatgpt_only and selected_connection and cloud_permitted.get())
    facts["_input_images"] = input_images or []
    if selected_connection:
        facts["_connection_owner_id"] = selected_connection[0]
        facts["_connection_generation"] = personal["generation"]
    facts["_web_search_request"] = bool(chatgpt_only and native_search)
    facts["_web_images"] = personal.get("web_images", True) and facts["_identification_lookup"]
    reaction_meta = reaction(question, facts, memory)
    if urgent:
        reaction_meta = {"initial": "concerned", "processing": "thinking", "final": "concerned"}
    facts["_stream_reply"] = lambda text: stream_reply(text, reaction_meta["final"])
    progress("research" if native_search else "model")
    # The model handles botanical dialogue, including short follow-ups and
    # recommendations. Deterministic responses remain the offline fallback.
    # A bare presentation needs one contextual question, not factual inference.
    # Keep it reliable and quick even when the local model echoes the greeting.
    clear_guided_turn = bool(facts["_dialogue_opening"])
    if not native_search and (
        facts["_observations"].get("excess_watering") or facts["_observations"].get("wet_soil")
    ):
        # This reported situation has source-backed internal guidance. Do not
        # let a weak model reinterpret absent direct sun as low light, invent
        # a different plant, or recommend more water after excessive watering.
        clear_guided_turn = True
    if missed_watering(question) and current_symptoms(question) and not native_search:
        # This report is covered by conservative internal care guidance. A
        # small local model must not invent a moisture reading or a schedule.
        clear_guided_turn = True
    if (
        facts["_topic"] in {"current", "pesticides", "toxicity"}
        and not result["documents"]
        and not native_search
    ):
        clear_guided_turn = True
    hybrid_meta = {}
    semantic = None
    model_requested = (
        chatgpt_only
        and facts["_allow_cloud"]
        and not cancelled()
        and (memory.intent not in COMMERCIAL or public_conversation or memory.intent == "identity")
    )
    if model_requested:
        semantic = generate_ai(question, facts, history)
        if (
            not semantic
            and facts["_web_search_request"]
            and budget.remaining() > 0.5
            and assistant_runtime.connection()
            and not cancelled()
        ):
            # An unsupported search tool must not disable normal conversation.
            facts["_web_search_request"] = False
            facts["_web_search_failed"] = True
            progress("model")
            semantic = generate_ai(question, facts, history)
        if semantic and semantic._searched_web:
            result["status"] = "found"
            hybrid_meta = {
                "status": "found",
                "providers": [{"provider": "chatgpt", "status": "found"}],
                "confidence": "medium",
            }
    if not chatgpt_only and native_search and not memory.plant_choices and not cancelled():
        semantic, hybrid_meta = research_reply(
            db, question, facts, history, memory, budget, cancelled, progress
        )
        result["status"] = hybrid_meta["status"]
        result["cache"] = hybrid_meta.get("cache")
    if (
        not chatgpt_only
        and not semantic
        and (not native_search or hybrid_meta.get("status") in {"not_configured", "disabled"})
        and facts["_topic"] not in {"current", "pesticides", "toxicity"}
    ):
        semantic = (
            generate_ai(question, facts, history)
            if not clear_guided_turn
            and not memory.plant_choices
            and (memory.intent not in (COMMERCIAL | {"greeting"}) or public_conversation)
            and not urgent
            and not cancelled()
            else None
        )
    if isinstance(semantic, str):
        semantic = SemanticReply(text=semantic)
    if (
        semantic
        and semantic._provider != "chatgpt"
        and not semantic._searched_web
        and (
            not substantive_reply(semantic.text, question)
            or not follows_reference(semantic.text, support)
        )
    ):
        logger.info("[RAFINHA_LOCAL_REPLY] rejected=does_not_answer_question")
        semantic = None
    rejected_replay = (
        replay_reason(semantic.text, question, memory, previous_memory, history)
        if semantic and semantic._provider != "chatgpt"
        else None
    )
    if semantic and semantic._searched_web and rejected_replay == "repeated_after_new_information":
        # Fresh evidence may support an earlier answer. Empty welcomes and
        # subject echoes remain invalid regardless of where synthesis ran.
        rejected_replay = None
    if rejected_replay:
        logger.info("[RAFINHA_LOCAL_REPLY] rejected=%s", rejected_replay)
        semantic = None
    if semantic and not merge_semantics(memory, semantic):
        if semantic._provider != "chatgpt":
            semantic = None
    if support and not (semantic and (semantic._searched_web or semantic._provider == "chatgpt")):
        for source in support["sources"]:
            if source not in facts["sources"]:
                facts["sources"].append(source)
    searched_web = bool(semantic and semantic._searched_web)
    images = semantic._images if searched_web else []
    if searched_web:
        facts["sources"] = semantic._sources
        result["status"] = "found"
        memory.research_context = {
            "summary": semantic.text[:2500],
            "sources": semantic._sources[:5],
            "topic": facts["_topic"],
        }
        if semantic._hypothesis and identification_clues(memory, facts):
            memory.identity_hypothesis = semantic._hypothesis
    elif native_search and hybrid_meta.get("status") not in {"not_configured", "disabled"}:
        result["status"] = "unavailable"
    if semantic:
        if facts["_dialogue_opening"] and semantic._provider != "chatgpt":
            ask(memory, "care_goal")
            if not memory.slots.get("care_goal") and not memory.pending_field:
                memory.pending_field = "care_goal"
                memory.pending_question = (
                    "Você quer cuidados gerais ou ajuda com algum problema nela?"
                )
        text = semantic.text
        source_type = (
            "general"
            if (
                facts["_dialogue_opening"]
                or memory.intent in {"general", "greeting", "casual", "identity"}
            )
            and not searched_web
            else "web"
            if result["documents"] or searched_web
            else "services"
            if memory.intent == "service"
            else "catalog"
            if memory.intent in PUBLIC_COMMERCE
            else "care"
            if facts["species"] or memory.plant_name or memory.slots.get("plant_group")
            else "identification"
        )
        for key, attr in [("initial", "initial_expression"), ("final", "final_expression")]:
            value = getattr(semantic, attr, None)
            if value in EXPRESSIONS and not (
                reaction_meta["final"] == "relieved" and value == "concerned"
            ):
                reaction_meta[key] = value
    else:
        if chatgpt_only and model_requested:
            text = "O ChatGPT não conseguiu concluir esta resposta agora. Tente enviar sua mensagem novamente em alguns instantes."
            source_type = "connection"
            reaction_meta["final"] = "concerned"
        elif (
            chatgpt_only
            and memory.intent in {"general", "greeting", "casual"}
            and not (
                facts["species"] or memory.plant_name or memory.slots.get("plant_group") or support
            )
        ):
            text = "Sou o Rafinha 🌿. A conexão ChatGPT não está disponível nesta instalação neste momento. As informações cadastradas no catálogo continuam acessíveis; a conversa livre depende de conectar sua própria conta ChatGPT."
            source_type = "connection"
        else:
            text, source_type = fallback(question, memory, facts, result)
        if input_images and chatgpt_only:
            text = "Recebi sua imagem, mas a análise visual não ficou disponível nesta resposta. Ela precisa de uma conexão ChatGPT ativa. Podemos continuar pela descrição da planta."
            source_type = "identification"
    if (
        support
        and support["kind"] == "identification"
        and not searched_web
        and not (semantic and semantic._provider == "chatgpt")
    ):
        memory.identity_hypothesis = memory.identity_hypothesis or {
            "label": support["label"],
            "status": "hypothesis",
            "confidence": "medium",
            "origin": "internal",
        }
        # A hypothesis never becomes a confirmed catalogue or CRM identity.
        if memory.pending_field == "plant_name":
            memory.pending_field = None
            memory.pending_question = None
    if native_search and not searched_web and hybrid_meta.get("status") == "unavailable":
        text = (
            "Não consegui conferir fontes externas agora, mas posso continuar te ajudando 🌱\n\n"
            + text
        )
    if (
        reaction_meta["final"] == "concerned"
        and not semantic
        and source_type != "connection"
        and "com atenção" not in text
    ):
        text = "Vamos olhar isso com atenção 🌿 " + text
    memory.last_expression = reaction_meta["final"]
    if len(result["documents"]) == 1 and reaction_meta["final"] == "confident":
        reaction_meta["final"] = "curious"
        memory.last_expression = "curious"
    progress("reply")
    confidence = (
        hybrid_meta.get("confidence")
        if searched_web
        else (
            "high"
            if source_type in {"company", "catalog", "services"}
            else "medium"
            if facts["species"] or result["documents"] or memory.plant_name or searched_web
            else "low"
        )
    )
    memory.phase = "identifying" if source_type == "identification" else "discussing"
    logger.info(
        "[RAFINHA] intent=%s state=%s initial=%s final=%s origin=%s model=%s elapsed=%.2f",
        memory.intent,
        memory.phase,
        reaction_meta["initial"],
        reaction_meta["final"],
        source_type,
        "success" if semantic else "fallback",
        time.monotonic() - started,
    )
    return {
        "text": text[:4000],
        "mode": semantic._provider if semantic else "catalog",
        "sources": facts["sources"],
        "images": images,
        "actions": facts["actions"],
        "context": facts["context"],
        "memory": memory.model_dump(),
        "meta": {
            "image_analysis": {
                "submitted": len(input_images or []),
                "performed": bool(input_images and semantic and semantic._provider == "chatgpt"),
            },
            "confidence": confidence,
            "searched_web": searched_web,
            "images": images,
            "source_type": source_type,
            "expressions": reaction_meta,
            "research": {
                "needed": needs_web,
                "reason": reason,
                "status": result["status"],
                "cache": result.get("cache"),
                "providers": hybrid_meta.get("providers", []),
                "confidence": hybrid_meta.get("confidence"),
                "conflicting": hybrid_meta.get("conflicting", False),
            },
            "fallback": not bool(semantic) or semantic._provider == "catalog",
            "chatgpt_failed": bool(model_requested and not semantic),
        },
    }
