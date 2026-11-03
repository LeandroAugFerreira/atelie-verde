"""Completa vínculos vazios dos clientes fictícios sem duplicar movimentações."""

from datetime import date, timedelta

from sqlalchemy import select

from . import business
from .clock import today
from .models import (
    Appointment,
    CatalogVersion,
    Ledger,
    Project,
    ProjectEvent,
    Service,
    Species,
    User,
)
from .schemas import LandscapeBrief, ProjectInput

VERSION = "demo-customer-activity-2026-10-12-v1"
STAGES = ["Orçamento", "Aprovado", "Planejamento", "Execução", "Finalizado", "Manutenção"]
SCENARIOS = [
    (
        "Pátio de folhagens",
        6,
        4,
        "Meia-sombra",
        "patio-comercial",
        ["Jiboia", "Zamioculca", "Lírio-da-paz"],
    ),
    (
        "Jardim com bordaduras",
        8,
        5,
        "Sol pleno",
        "jardim-frontal",
        ["Hibisco", "Lavanda", "Buxinho"],
    ),
    (
        "Varanda em vasos",
        4,
        3,
        "Meia-sombra",
        "varanda-pinheiros",
        ["Jiboia", "Zamioculca", "Lírio-da-paz"],
    ),
    (
        "Área de convivência",
        7,
        5,
        "Misto",
        "patio-comercial",
        ["Areca-bambu", "Agapanto", "Buxinho"],
    ),
    (
        "Horta compacta",
        3,
        2,
        "Sol pleno",
        "varanda-pinheiros",
        ["Manjericão", "Alecrim", "Hortelã"],
    ),
]


def free_slot(db, day, responsible):
    for hour in range(8, 17, 2):
        start, end = f"{hour:02}:00", f"{hour + 2:02}:00"
        if not db.scalar(
            select(Appointment.id).where(
                Appointment.date == day,
                Appointment.responsible == responsible,
                Appointment.status != "Cancelado",
                Appointment.start_time < end,
                Appointment.end_time > start,
            )
        ):
            return start, end
    return None


def seed_customer_activity(db):
    counts = {"projetos": 0, "servicos": 0, "recebimentos": 0}
    if db.get(CatalogVersion, VERSION):
        return counts
    admin = db.scalar(
        select(User).where(User.email == "admin@atelieverde.local", User.role == "admin")
    )
    emails = [
        f"cliente{suffix}@{domain}"
        for suffix in ["", *range(2, 11)]
        for domain in ["atelieverde.local", "greenscape.local"]
    ]
    clients = list(
        db.scalars(
            select(User)
            .where(User.role == "customer", User.email.in_(emails), User.active.is_(True))
            .order_by(User.id)
        )
    )
    species = {row.name: row.id for row in db.scalars(select(Species).order_by(Species.id))}
    services = list(
        db.scalars(select(Service).where(Service.active.is_(True)).order_by(Service.id))
    )
    if not admin or not clients or not species or not services:
        return counts
    for index, customer in enumerate(clients):
        paid = list(
            db.scalars(
                select(Ledger).where(
                    Ledger.customer_id == customer.id,
                    Ledger.direction == "Receita",
                    Ledger.status == "Pago",
                )
            )
        )
        if not db.scalar(select(Project.id).where(Project.customer_id == customer.id)):
            name, width, length, light, image, preferred = SCENARIOS[index % len(SCENARIOS)]
            selected = [name for name in preferred if name in species] or list(species)[:3]
            plants = [
                {
                    "species_id": species[name],
                    "quantity": 3 + i,
                    "application": "Vasos e canteiros do planejamento fictício",
                }
                for i, name in enumerate(selected)
            ]
            project_payments = [row for row in paid if row.source == "Projetos"]
            if project_payments:
                dates = [
                    date.fromisoformat(row.paid_date) for row in project_payments if row.paid_date
                ] or [today()]
                start, finish = min(dates) - timedelta(days=14), max(dates)
                budget, status = sum(row.amount_cents for row in project_payments), "Finalizado"
            else:
                start, finish = today() + timedelta(days=3), today() + timedelta(days=24)
                budget, status = 240000, "Orçamento"
            brief = LandscapeBrief(
                width=width,
                length=length,
                light=light,
                drainage="Boa",
                maintenance="Baixa",
                soil="Condições ilustrativas a confirmar em visita",
                objective="Organizar um espaço verde funcional e acolhedor.",
                notes="Projeto e valores fictícios para explorar o perfil do cliente.",
                plantings=[
                    {
                        **plant,
                        "x": width * (i + 1) / (len(plants) + 1),
                        "y": length * 0.25,
                        "diameter": min(width, length) * 0.18,
                    }
                    for i, plant in enumerate(plants)
                ],
                zones=[
                    {
                        "name": "Canteiro principal",
                        "kind": "Canteiro",
                        "x": 0,
                        "y": 0,
                        "width": width,
                        "length": length * 0.5,
                    },
                    {
                        "name": "Circulação",
                        "kind": "Caminho",
                        "x": 0,
                        "y": length * 0.6,
                        "width": width,
                        "length": length * 0.2,
                    },
                ],
            )
            fields = ProjectInput(
                name=f"{name} · demonstração",
                customer_id=customer.id,
                address=customer.address or "Rua das Flores, 100 · Endereço demonstrativo",
                area=width * length,
                budget_cents=budget,
                start_date=start,
                end_date=finish,
                description="Exemplo fictício vinculado ao cliente, com espécies, materiais, cronograma e planta 2D.",
                plants=plants,
                materials=[
                    {
                        "name": "Substrato e preparo dos vasos",
                        "quantity": 5,
                        "unit_price_cents": 2990,
                    },
                    {"name": "Vasos e acabamento", "quantity": 3, "unit_price_cents": 5500},
                ],
                services=[
                    {
                        "name": "Planejamento e acompanhamento",
                        "quantity": 1,
                        "unit_price_cents": 60000,
                    }
                ],
                tasks=[
                    {
                        "title": title,
                        "date": start + (finish - start) * fraction,
                        "done": status == "Finalizado",
                    }
                    for title, fraction in [
                        ("Levantamento do espaço", 0),
                        ("Escolha de espécies", 0.3),
                        ("Preparação e implantação", 0.7),
                        ("Revisão e orientações", 1),
                    ]
                ],
            ).model_dump(mode="json")
            project = Project(
                **fields,
                status=status,
                delivery_mode="Presencial",
                brief=brief.model_dump(mode="json"),
                brief_revision=1,
                reference_image_url=f"/projects/{image}.png",
                reference_image_note="Imagem ilustrativa de um projeto fictício.",
            )
            db.add(project)
            db.flush()
            for stage in STAGES[: STAGES.index(status) + 1]:
                db.add(ProjectEvent(project_id=project.id, status=stage, actor_id=admin.id))
            business.audit(
                db, admin, "Projeto demonstrativo", project, action="Completar perfil demonstrativo"
            )
            counts["projetos"] += 1
        if not db.scalar(select(Appointment.id).where(Appointment.customer_id == customer.id)):
            payments = [row for row in paid if row.source == "Serviços"]
            service = next(
                (
                    row
                    for row in services
                    if row.category == ("Manutenção" if payments else "Consultoria")
                ),
                services[0],
            )
            day = (
                date.fromisoformat(payments[-1].paid_date) - timedelta(days=1)
                if payments
                else today() - timedelta(days=3)
            )
            slot = free_slot(db, day.isoformat(), service.responsible)
            while slot is None:
                day -= timedelta(days=1)
                slot = free_slot(db, day.isoformat(), service.responsible)
            amount = sum(row.amount_cents for row in payments) if payments else service.price_cents
            appointment = Appointment(
                service_id=service.id,
                customer_id=customer.id,
                title=f"{payments[-1].description if payments else service.name} · demonstração",
                date=day.isoformat(),
                start_time=slot[0],
                end_time=slot[1],
                responsible=service.responsible,
                status="Concluído",
                address=customer.address or "Endereço de demonstração",
                amount_cents=amount,
            )
            db.add(appointment)
            business.audit(
                db,
                admin,
                "Agenda demonstrativa",
                appointment,
                action="Completar perfil demonstrativo",
            )
            counts["servicos"] += 1
            if not payments and amount > 0:
                receipt = Ledger(
                    direction="Receita",
                    source="Serviços",
                    customer_id=customer.id,
                    counterparty=customer.name,
                    description=f"{service.name} · demonstração · atendimento #{appointment.id}",
                    due_date=day.isoformat(),
                    paid_date=(day + timedelta(days=1)).isoformat(),
                    amount_cents=amount,
                    status="Pago",
                )
                db.add(receipt)
                business.audit(
                    db,
                    admin,
                    "Recebimento demonstrativo",
                    receipt,
                    action="Completar perfil demonstrativo",
                )
                counts["recebimentos"] += 1
    db.add(CatalogVersion(version=VERSION))
    business.commit(db)
    return counts
