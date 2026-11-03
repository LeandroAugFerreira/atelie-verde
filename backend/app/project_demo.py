"""Add fictitious projects to the demo customer's portfolio exactly once."""

from datetime import timedelta

from sqlalchemy import select

from . import business
from .clock import today
from .models import CatalogVersion, Project, ProjectEvent, Species, User
from .schemas import LandscapeBrief, ProjectInput

VERSION = "demo-project-portfolio-2026-10-10-v1"
SCENARIOS = [
    (
        "Jardim de boas-vindas · demonstração",
        "Orçamento",
        "Presencial",
        6,
        5,
        480000,
        5,
        25,
        "entrada-moema",
        ["Hibisco", "Lavanda", "Buxinho"],
        "Sol pleno",
    ),
    (
        "Horta em vasos · demonstração",
        "Aprovado",
        "Virtual",
        3,
        2,
        135000,
        3,
        15,
        "varanda-pinheiros",
        ["Manjericão", "Alecrim", "Hortelã"],
        "Sol pleno",
    ),
    (
        "Varanda de folhagens · demonstração",
        "Planejamento",
        "Virtual",
        4,
        3,
        240000,
        -2,
        18,
        "varanda-pinheiros",
        ["Jiboia", "Zamioculca", "Lírio-da-paz"],
        "Meia-sombra",
    ),
    (
        "Jardim residencial · demonstração",
        "Execução",
        "Presencial",
        8,
        6,
        980000,
        -7,
        14,
        "jardim-frontal",
        ["Hibisco", "Agapanto", "Lavanda"],
        "Sol pleno",
    ),
    (
        "Pátio florido · demonstração",
        "Finalizado",
        "Presencial",
        6,
        4,
        460000,
        -45,
        -14,
        "patio-comercial",
        ["Ixora", "Lantana", "Buxinho"],
        "Sol pleno",
    ),
    (
        "Canteiros e irrigação · demonstração",
        "Manutenção",
        "Presencial",
        10,
        8,
        1250000,
        -60,
        30,
        "area-externa",
        ["Hibisco", "Agapanto", "Areca-bambu"],
        "Misto",
    ),
]
STAGES = ["Orçamento", "Aprovado", "Planejamento", "Execução", "Finalizado", "Manutenção"]


def seed_project_portfolio(db):
    if db.get(CatalogVersion, VERSION):
        return 0
    admin = db.scalar(
        select(User).where(User.email == "admin@atelieverde.local", User.role == "admin")
    )
    customer = db.scalar(
        select(User).where(
            User.email == "cliente@atelieverde.local",
            User.role == "customer",
            User.active.is_(True),
        )
    )
    if not admin or not customer:
        return 0
    species = {row.name: row.id for row in db.scalars(select(Species))}
    if not all(name in species for row in SCENARIOS for name in row[9]):
        return 0
    created = 0
    for name, status, delivery, width, length, budget, begin, end, image, names, light in SCENARIOS:
        if db.scalar(
            select(Project.id).where(Project.name == name, Project.customer_id == customer.id)
        ):
            continue
        start, finish = today() + timedelta(days=begin), today() + timedelta(days=end)
        plants = [
            {
                "species_id": species[n],
                "quantity": 3 + i,
                "application": "Vasos e canteiros planejados",
            }
            for i, n in enumerate(names)
        ]
        tasks = [
            {
                "title": title,
                "date": (start + (finish - start) * fraction).isoformat(),
                "done": status in {"Finalizado", "Manutenção"}
                or (status == "Execução" and fraction < 0.7),
            }
            for title, fraction in [
                ("Levantamento e medidas", 0),
                ("Escolha de espécies e materiais", 0.3),
                ("Preparação e implantação", 0.7),
                ("Revisão e orientações de cuidado", 1),
            ]
        ]
        brief = LandscapeBrief(
            width=width,
            length=length,
            light=light,
            soil="Condições ilustrativas a confirmar em uma visita",
            drainage="Boa",
            maintenance="Média",
            objective="Organizar um espaço verde funcional e acolhedor.",
            notes="Projeto fictício de demonstração. A composição e as medidas servem para explorar o portal.",
            plantings=[
                {
                    **plant,
                    "x": width * (i + 1) / 4,
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
            name=name,
            customer_id=customer.id,
            address=customer.address or "Rua do Jardim, 100 · São Paulo, SP",
            area=width * length,
            budget_cents=budget,
            start_date=start,
            end_date=finish,
            description=f"Exemplo fictício de paisagismo em etapa de {status.lower()}, com atendimento {delivery.lower()}. Espécies, custos planejados, cronograma e planta 2D disponíveis para explorar.",
            plants=plants,
            materials=[
                {
                    "name": "Substrato para vasos e canteiros",
                    "quantity": 8,
                    "unit_price_cents": 2990,
                },
                {"name": "Vasos e acabamento", "quantity": 5, "unit_price_cents": 5500},
            ],
            services=[
                {"name": "Planejamento e acompanhamento", "quantity": 1, "unit_price_cents": 60000}
            ],
            tasks=tasks,
        ).model_dump(mode="json")
        project = Project(
            **fields,
            status=status,
            delivery_mode=delivery,
            brief=brief.model_dump(mode="json"),
            brief_revision=1,
            reference_image_url=f"/projects/{image}.png",
            reference_image_note="Referência visual ilustrativa; não representa uma obra executada.",
        )
        db.add(project)
        db.flush()
        for stage in STAGES[: STAGES.index(status) + 1]:
            db.add(ProjectEvent(project_id=project.id, status=stage, actor_id=admin.id))
        business.audit(
            db, admin, "Projeto demonstrativo", project, action="Criar exemplo de portfólio"
        )
        created += 1
    db.add(CatalogVersion(version=VERSION))
    business.commit(db)
    return created
