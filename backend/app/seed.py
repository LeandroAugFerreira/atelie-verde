from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .models import (
    Appointment,
    Ledger,
    Order,
    Product,
    Project,
    ProjectEvent,
    Quote,
    Review,
    Service,
    Species,
    StockMove,
    User,
)
from .security import passwords


def seed(db):
    if db.scalar(select(User.id).limit(1)):
        return
    admin = User(
            name="Leandro",
        email="admin@atelieverde.local",
        password_hash=passwords.hash("AtelieVerde@2026"),
        role="admin",
    )
    db.add(admin)
    names = [
        "Rafael",
        "Rafael Almeida",
        "Mariana Silva",
        "Pedro Santos",
        "Juliana Lima",
        "Fernanda Costa",
        "Ricardo Pereira",
        "André Santos",
        "Patrícia Lima",
        "Roberto Nunes",
    ]
    clients = [
        User(
            name=name,
            email="cliente@atelieverde.local" if i == 0 else f"cliente{i + 1}@atelieverde.local",
            password_hash=passwords.hash("AtelieVerde@2026"),
            phone=f"(11) 98800-100{i}",
            city=[
                "São Paulo - SP",
                "Rio de Janeiro - RJ",
                "Belo Horizonte - MG",
                "Curitiba - PR",
                "Porto Alegre - RS",
            ][i % 5],
            address=f"Rua das Flores, {100 + i * 20} · São Paulo, SP",
            notes="Prefere atendimento pela manhã. Interesse em novos projetos para a área externa.",
            created_at=(datetime.now(timezone.utc) - timedelta(days=i * 25 + 2)).isoformat(),
        )
        for i, name in enumerate(names)
    ]
    db.add_all(clients)
    species_data = [
        (
            "Hibisco",
            "Hibiscus rosa-sinensis",
            "Sol pleno",
            "Moderada",
            "Grande",
            "Externo",
            "Média",
            "Flores / cerca viva",
            "Flores de cores intensas. Referência demonstrativa: porte adulto de 2 a 4 m.",
        ),
        (
            "Lavanda",
            "Lavandula dentata",
            "Sol pleno",
            "Baixa",
            "Pequeno",
            "Externo",
            "Baixa",
            "Flores / aromáticas",
            "Folhagem perfumada e flores delicadas para jardins ensolarados.",
        ),
        (
            "Zamioculca",
            "Zamioculcas zamiifolia",
            "Meia-sombra",
            "Baixa",
            "Médio",
            "Interno",
            "Baixa",
            "Folhagem / ornamental",
            "Folhas verdes brilhantes para ambientes com iluminação indireta.",
        ),
        (
            "Espada-de-são-jorge",
            "Dracaena trifasciata",
            "Meia-sombra",
            "Baixa",
            "Médio",
            "Ambos",
            "Baixa",
            "Folhagem / ornamental",
            "Folhagem vertical que cria ritmo na composição.",
        ),
        (
            "Costela-de-adão",
            "Monstera deliciosa",
            "Meia-sombra",
            "Moderada",
            "Grande",
            "Ambos",
            "Média",
            "Folhagem / tropical",
            "Folhas recortadas e presença marcante em composições tropicais.",
        ),
        (
            "Ixora",
            "Ixora coccinea",
            "Sol pleno",
            "Moderada",
            "Médio",
            "Externo",
            "Média",
            "Flores / cerca viva",
            "Inflorescências agrupadas para bordaduras e maciços.",
        ),
        (
            "Echeveria",
            "Echeveria elegans",
            "Sol pleno",
            "Baixa",
            "Pequeno",
            "Ambos",
            "Baixa",
            "Folhagem / suculentas",
            "Rosetas compactas para vasos e pequenos espaços.",
        ),
        (
            "Lírio-da-paz",
            "Spathiphyllum wallisii",
            "Sombra",
            "Frequente",
            "Pequeno",
            "Interno",
            "Média",
            "Flores / ornamental",
            "Folhagem elegante e inflorescências claras.",
        ),
        (
            "Alecrim",
            "Salvia rosmarinus",
            "Sol pleno",
            "Baixa",
            "Pequeno",
            "Externo",
            "Baixa",
            "Aromáticas / horta",
            "Arbusto aromático para jardins sensoriais e hortas.",
        ),
        (
            "Agapanto",
            "Agapanthus africanus",
            "Sol pleno",
            "Moderada",
            "Médio",
            "Externo",
            "Baixa",
            "Flores / bordadura",
            "Hastes florais para bordas e canteiros.",
        ),
        (
            "Jasmim-manga",
            "Plumeria rubra",
            "Sol pleno",
            "Moderada",
            "Grande",
            "Externo",
            "Média",
            "Flores / ornamental",
            "Flores perfumadas para composições externas.",
        ),
        (
            "Palmeira-ráfis",
            "Rhapis excelsa",
            "Meia-sombra",
            "Moderada",
            "Grande",
            "Interno",
            "Baixa",
            "Folhagem / ornamental",
            "Folhas em leque para vasos e espaços protegidos.",
        ),
        (
            "Buxinho",
            "Buxus sempervirens",
            "Sol pleno",
            "Moderada",
            "Médio",
            "Externo",
            "Média",
            "Cerca viva / ornamental",
            "Arbusto de folhagem compacta para delimitações.",
        ),
        (
            "Rosa-do-deserto",
            "Adenium obesum",
            "Sol pleno",
            "Baixa",
            "Pequeno",
            "Externo",
            "Média",
            "Flores / ornamental",
            "Flores coloridas e formas marcantes para vasos.",
        ),
        (
            "Lantana",
            "Lantana camara",
            "Sol pleno",
            "Baixa",
            "Pequeno",
            "Externo",
            "Baixa",
            "Flores / bordadura",
            "Canteiros e áreas de cor.",
        ),
    ]
    species = [
        Species(
            **dict(
                zip(
                    [
                        "name",
                        "scientific_name",
                        "light",
                        "watering",
                        "size",
                        "environment",
                        "difficulty",
                        "use",
                        "description",
                    ],
                    s,
                )
            )
        )
        for s in species_data
    ]
    db.add_all(species)
    db.flush()
    assets = {
        0: "hibiscus",
        1: "lavender",
        2: "zamioculca",
        3: "sword",
        4: "monstera",
        6: "succulent",
        7: "peace",
        9: "agapanthus",
        10: "jasmine",
        11: "palm",
        12: "boxwood",
        13: "desert",
        14: "lantana",
    }
    for i, s in enumerate(species):
        s.demo_asset = assets.get(i, "monstera")
        s.height = "2 a 4 m" if i == 0 else s.size
        s.watering_frequency = "Conforme umidade do solo e avaliação técnica"
        s.care = "Avalie iluminação, drenagem, clima e umidade do solo. Adapte rega e adubação às condições do local. Dados de referência para demonstração; valide com um profissional."
    product_data = [
        ("Costela-de-adão", "Plantas", 8990, 18, 5, 4),
        ("Zamioculca", "Plantas", 6990, 24, 5, 2),
        ("Lavanda", "Plantas", 2490, 4, 5, 1),
        ("Espada-de-são-jorge", "Plantas", 3990, 32, 5, 3),
        ("Hibisco", "Plantas", 3290, 12, 4, 0),
        ("Echeveria", "Plantas", 1890, 40, 5, 6),
        ("Jasmim-manga", "Plantas", 7990, 15, 5, 10),
        ("Palmeira-ráfis", "Plantas", 12990, 16, 5, 11),
        ("Buxinho", "Plantas", 4490, 20, 5, 12),
        ("Rosa-do-deserto", "Plantas", 6990, 3, 10, 13),
        ("Vaso de cerâmica areia", "Vasos", 7990, 14, 4, None),
        ("Vaso terracota 25 cm", "Vasos", 4290, 22, 5, None),
        ("Substrato orgânico 5 kg", "Substratos", 2990, 3, 5, None),
        ("Fertilizante NPK 500 g", "Fertilizantes", 2290, 16, 5, None),
        ("Tesoura de poda", "Ferramentas", 5990, 8, 3, None),
        ("Regador verde 2 L", "Acessórios", 3490, 2, 3, None),
    ]
    products = [
        Product(
            name=n,
            category=c,
            price_cents=p,
            stock=s,
            low_stock=minimum,
            species_id=species[i].id if i is not None else None,
            sku=f"{c[:2].upper()}-{index + 1:03d}",
            location=f"{chr(65 + index % 4)}{index % 3 + 1} - {c}",
            demo_asset=species[i].demo_asset
            if i is not None
            else {
                "Vasos": "pots",
                "Substratos": "substrate",
                "Fertilizantes": "fertilizer",
                "Ferramentas": "tools",
                "Acessórios": "accessories",
            }[c],
            description=f"{n}. Selecionado para cuidar do seu espaço verde.",
        )
        for index, (n, c, p, s, minimum, i) in enumerate(product_data)
    ]
    db.add_all(products)
    services = [
        Service(name=n, description=d, price_cents=p, unit=u)
        for n, d, p, u in [
            (
                "Manutenção de jardins",
                "Cuidado contínuo com gramado, canteiros e saúde das plantas.",
                1800,
                "m²",
            ),
            ("Poda", "Poda de formação e limpeza com avaliação do local.", 18000, "visita"),
            (
                "Implantação de jardins",
                "Preparação do solo, plantio e acabamento do jardim.",
                8500,
                "m²",
            ),
            ("Irrigação", "Planejamento e instalação de irrigação para o seu jardim.", 4500, "m²"),
            (
                "Consultoria",
                "Orientação sobre espécies e cuidados para o seu ambiente.",
                25000,
                "visita",
            ),
            (
                "Projeto paisagístico",
                "Composição de espécies, materiais e organização do espaço.",
                150000,
                "projeto",
            ),
        ]
    ]
    db.add_all(services)
    db.flush()
    for i, s in enumerate(services):
        s.demo_asset = [
            "maintenance",
            "pruning",
            "installation",
            "irrigation",
            "consulting",
            "landscape",
        ][i]
        s.category = [
            "Manutenção",
            "Manutenção",
            "Implantação",
            "Irrigação",
            "Consultoria",
            "Projeto",
        ][i]
        s.duration = ["3 horas", "4 horas", "3 dias", "6 horas", "2 horas", "5 dias"][i]
        s.responsible = [
            "Mariana Costa",
            "Carlos Lima",
            "Rafael Mendes",
            "João Pereira",
            "Juliana Alves",
            "Fernanda Rocha",
        ][i]
    today = datetime.now(timezone.utc).date()
    projects = [
        Project(
            name=n,
            customer_id=clients[i].id,
            address=clients[i].address,
            area=a,
            status=s,
            budget_cents=b,
            start_date=(today - timedelta(days=10)).isoformat(),
            end_date=(today + timedelta(days=25)).isoformat(),
            description=d,
            plants=[{"species_id": species[j].id, "quantity": q} for j, q in plants],
            materials=[
                {"name": "Substrato orgânico", "quantity": 10, "unit_price_cents": 2990},
                {"name": "Pedriscos decorativos", "quantity": 8, "unit_price_cents": 3500},
            ],
            services=[{"name": "Preparo e plantio", "quantity": a, "unit_price_cents": 5000}],
            tasks=[
                {
                    "title": "Visita técnica e levantamento",
                    "date": (today - timedelta(days=8)).isoformat(),
                    "done": True,
                },
                {
                    "title": "Definição de espécies e materiais",
                    "date": today.isoformat(),
                    "done": s in ("Execução", "Finalizado", "Manutenção"),
                },
                {
                    "title": "Plantio e acabamento",
                    "date": (today + timedelta(days=20)).isoformat(),
                    "done": s in ("Finalizado", "Manutenção"),
                },
            ],
        )
        for n, i, a, s, b, d, plants in [
            (
                "Projeto Residencial – Jardim Frontal",
                0,
                85,
                "Execução",
                1875000,
                "Projeto de paisagismo para residência unifamiliar com jardim frontal, valorizando a fachada e criando um ambiente acolhedor e harmonioso.",
                [(0, 6), (1, 12), (12, 8), (11, 3), (14, 10)],
            ),
            (
                "Varanda viva · Pinheiros",
                1,
                18,
                "Planejamento",
                640000,
                "Vasos, aromas e texturas para transformar a varanda.",
                [(1, 6), (6, 10), (8, 4)],
            ),
            (
                "Jardim de entrada · Moema",
                2,
                42,
                "Aprovado",
                980000,
                "Bordaduras floridas e uma entrada acolhedora.",
                [(0, 8), (5, 10), (9, 12)],
            ),
            (
                "Área externa · Alto de Pinheiros",
                3,
                120,
                "Manutenção",
                2450000,
                "Manutenção periódica dos canteiros e da irrigação.",
                [(0, 12), (4, 8)],
            ),
            (
                "Pátio comercial · Vila Madalena",
                4,
                60,
                "Orçamento",
                1250000,
                "Paisagismo para um espaço de encontro.",
                [(3, 20), (2, 10)],
            ),
        ]
    ]
    db.add_all(projects)
    db.flush()
    for p in projects:
        p.plants = [
            {
                **plant,
                "application": [
                    "Canteiros frontais",
                    "Bordaduras e caminhos",
                    "Cercas vivas e delimitações",
                    "Pontos de destaque",
                    "Canteiros e áreas de cor",
                ][i % 5],
            }
            for i, plant in enumerate(p.plants)
        ]
    for p in projects:
        db.add(ProjectEvent(project_id=p.id, status=p.status, actor_id=admin.id))
    quote_statuses = [
        "Solicitado",
        "Em análise",
        "Enviado",
        "Aprovado",
        "Rejeitado",
        "Em análise",
        "Solicitado",
        "Enviado",
        "Solicitado",
        "Em análise",
    ]
    for i, c in enumerate(clients):
        db.add(
            Quote(
                customer_id=c.id,
                service_id=services[i % 6].id,
                area=120 + i * 30,
                address=c.address,
                description="Gostaria de um projeto paisagístico para a área externa, com espaços de convivência e plantas de baixa manutenção.",
                status=quote_statuses[i],
                amount_cents=1245000 + i * 150000,
                plants=[
                    {"species_id": species[2].id, "quantity": 6, "application": "Vasos"},
                    {"species_id": species[7].id, "quantity": 8, "application": "Bordaduras"},
                ],
                materials=[
                    {"name": "Substrato premium", "quantity": 10, "unit_price_cents": 2990},
                    {"name": "Vaso de cerâmica", "quantity": 4, "unit_price_cents": 7990},
                ],
            )
        )
    for month in range(5, -1, -1):
        for j in range(3):
            p = products[(month + j) % len(products)]
            quantity = 2 + j
            created = (datetime.now(timezone.utc) - timedelta(days=month * 30 + j * 3)).isoformat()
            order = Order(
                customer_id=clients[j].id,
                items=[
                    {
                        "product_id": p.id,
                        "name": p.name,
                        "quantity": quantity,
                        "price_cents": p.price_cents,
                    }
                ],
                total_cents=quantity * p.price_cents,
                created_at=created,
            )
            db.add(order)
            db.flush()
            db.add(
                Ledger(
                    direction="Receita",
                    source="Loja",
                    customer_id=clients[j].id,
                    order_id=order.id,
                    counterparty=clients[j].name,
                    description=f"Pedido #{order.id}",
                    due_date=created[:10],
                    amount_cents=order.total_cents,
                    status="Pago",
                    paid_date=created[:10],
                    created_at=created,
                )
            )
            db.add(
                StockMove(
                    product_id=p.id,
                    quantity=-quantity,
                    reason=f"Pedido demonstrativo #{order.id}",
                    actor_id=admin.id,
                    created_at=created,
                )
            )
    for p in products:
        sold = sum(
            o.quantity * -1
            for o in db.scalars(select(StockMove).where(StockMove.product_id == p.id))
        )
        db.add(
            StockMove(
                product_id=p.id,
                quantity=p.stock + sold,
                reason="Carga inicial demonstrativa",
                actor_id=admin.id,
                created_at=(datetime.now(timezone.utc) - timedelta(days=190)).isoformat(),
            )
        )
    for m in range(9):
        d = (today - timedelta(days=m * 30)).isoformat()
        db.add(
            Ledger(
                direction="Receita",
                source="Serviços",
                customer_id=clients[m % len(clients)].id,
                counterparty=clients[m % len(clients)].name,
                description="Manutenção de jardim",
                due_date=d,
                amount_cents=135000 + m * 10000,
                status="Pago",
                paid_date=d,
            )
        )
        db.add(
            Ledger(
                direction="Receita",
                source="Projetos",
                customer_id=clients[m % len(clients)].id,
                counterparty=clients[m % len(clients)].name,
                description="Parcela do projeto paisagístico",
                due_date=d,
                amount_cents=320000 + m * 12000,
                status="Pago",
                paid_date=d,
            )
        )
        db.add(
            Ledger(
                direction="Despesa",
                source="Outros",
                counterparty="Viveiro Verde",
                description="Compra de plantas e insumos",
                due_date=d,
                amount_cents=168000 + m * 4000,
                status="Pago",
                paid_date=d,
            )
        )
    for i in range(5):
        due = (today + timedelta(days=i * 3 - 4)).isoformat()
        db.add(
            Ledger(
                direction="Receita",
                source="Projetos",
                customer_id=clients[i].id,
                counterparty=clients[i].name,
                description="Projeto de jardim residencial",
                due_date=due,
                amount_cents=125000 + i * 35000,
            )
        )
        db.add(
            Ledger(
                direction="Despesa",
                source="Outros",
                counterparty=[
                    "Viveiro Verde",
                    "Terra Boa Insumos",
                    "Ferramentas Pro",
                    "AgroDistribuidora",
                    "Energia Elétrica",
                ][i],
                description=[
                    "Compra de plantas e mudas",
                    "Substratos e adubos",
                    "Equipamentos de jardinagem",
                    "Fertilizantes e defensivos",
                    "Conta de energia - Sede",
                ][i],
                due_date=due,
                amount_cents=64000 + i * 12000,
            )
        )
    monday = today - timedelta(days=today.weekday())
    for day in range(5):
        for j in range(4):
            service = services[(day + j) % 6]
            db.add(
                Appointment(
                    service_id=service.id,
                    customer_id=clients[(day + j) % len(clients)].id,
                    title=[
                        "Visita técnica",
                        "Poda de árvores",
                        "Manutenção de jardins",
                        "Instalação de irrigação",
                    ][j],
                    date=(monday + timedelta(days=day)).isoformat(),
                    start_time=["08:00", "10:00", "13:30", "15:30"][j],
                    end_time=["09:00", "12:00", "15:00", "17:00"][j],
                    responsible=service.responsible,
                    status="Concluído" if day < today.weekday() else "Agendado",
                    address=clients[(day + j) % len(clients)].address,
                    amount_cents=service.price_cents,
                )
            )
    for i in range(4):
        db.add(
            Review(
                product_id=products[i].id,
                customer_id=clients[i].id,
                rating=5 if i % 2 else 4,
                comment="Planta bem cuidada e atendimento atencioso. Recomendo!",
            )
        )
    db.commit()
