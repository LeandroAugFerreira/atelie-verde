from sqlalchemy import select

from .models import CatalogVersion, Service

VERSION = "landscape-services-2026-10-05-v1"
SOURCES = [
    {
        "title": "University of Minnesota Extension · processo de projeto",
        "url": "https://extension.umn.edu/garden-and-home/yard-and-garden/lawns-and-landscapes-in-minnesota",
    },
    {
        "title": "RHS · levantamento do jardim",
        "url": "https://www.rhs.org.uk/garden-inspiration/design/get-to-know-your-garden",
    },
    {
        "title": "GARDENA · referência de planejamento visual",
        "url": "https://www.gardena.com/ca-en/c/discover/mygarden-planning-tools/garden-planner",
    },
]


def details(service):
    common = {
        "steps": [
            "Envie a solicitação com informações do local.",
            "A equipe avalia o escopo e apresenta a proposta.",
            "Após aprovação, o atendimento é combinado com o cliente.",
        ],
        "preparation": [
            "Endereço do local e área aproximada.",
            "Fotos gerais e dos pontos que precisam de atenção.",
            "Objetivos, restrições de acesso e disponibilidade.",
        ],
        "documents": ["Orçamento e escopo aprovado", "Registro de atendimento e orientações"],
        "includes": [],
        "deliverables": [],
        "sources": [],
    }
    if service.category == "Manutenção":
        pruning = "poda" in service.name.lower()
        common["includes"] = (
            [
                "Avaliação das plantas e definição da intervenção.",
                "Poda de formação, limpeza ou manutenção conforme o diagnóstico.",
                "Organização dos resíduos e orientações de cuidado após o serviço.",
            ]
            if pruning
            else [
                "Inspeção do jardim e identificação das necessidades.",
                "Limpeza de canteiros, manejo de plantas espontâneas e acabamento.",
                "Avaliação de rega, adubação e podas, conforme o escopo aprovado.",
            ]
        )
        common["deliverables"] = [
            "Plano do atendimento e registro do que foi realizado",
            "Orientações de manutenção e próximos cuidados",
        ]
    elif service.category == "Implantação":
        common["includes"] = [
            "Conferência do terreno e preparação dos canteiros.",
            "Organização de substratos, espécies e materiais do planejamento.",
            "Plantio, acabamento e orientação para o estabelecimento das plantas.",
        ]
        common["deliverables"] = [
            "Jardim implantado conforme o escopo",
            "Lista de espécies e instruções para o período inicial",
        ]
    elif service.category == "Irrigação":
        common["includes"] = [
            "Levantamento dos pontos de água, setores e necessidades de rega.",
            "Proposta de distribuição e instalação do sistema contratado.",
            "Testes de funcionamento e orientação de programação e manutenção.",
        ]
        common["deliverables"] = [
            "Esquema dos setores e componentes",
            "Orientações de funcionamento e manutenção",
        ]
    elif service.category == "Consultoria":
        common["includes"] = [
            "Avaliação de luminosidade, solo, drenagem e condições de cultivo.",
            "Orientação sobre espécies, implantação e rotina de cuidados.",
            "Priorização de melhorias compatíveis com o espaço e os objetivos.",
        ]
        common["deliverables"] = [
            "Diagnóstico e recomendações para o espaço",
            "Lista de ações prioritárias e orientações de cultivo",
        ]
    else:
        virtual = service.delivery_mode == "Virtual"
        common["includes"] = [
            "Levantamento remoto com medidas, fotos e documentos enviados pelo cliente."
            if virtual
            else "Visita ao local para levantamento de medidas, condições de cultivo e necessidades.",
            "Briefing sobre estilo, uso do espaço, manutenção e orçamento.",
            "Estudo de distribuição de áreas e seleção de espécies.",
            "Revisão do planejamento com o paisagista e preparação dos documentos de entrega.",
        ]
        common["preparation"] += [
            "Largura, comprimento e orientação do terreno.",
            "Informações sobre sol, solo, drenagem e elementos existentes.",
            "Espécies desejadas e referências de estilo.",
        ]
        common["deliverables"] = [
            "Planta 2D do planejamento",
            "Lista de espécies e materiais",
            "Memorial com condições do local e orientações",
            "Arquivos e documentos do projeto aprovado",
        ]
        common["documents"] = [
            "Fotos e levantamento do local",
            "Planta ou croqui existente em PDF",
            "Proposta, memorial e planta de entrega",
        ]
        common["sources"] = SOURCES
    return common


def sync_offers(db):
    if db.get(CatalogVersion, VERSION):
        return
    for name, mode, price, description in [
        (
            "Paisagista virtual",
            "Virtual",
            90000,
            "Planejamento remoto a partir das medidas, condições do local, fotos e espécies enviadas pelo cliente.",
        ),
        (
            "Paisagista presencial",
            "Presencial",
            180000,
            "Levantamento do local com visita e planejamento paisagístico acompanhado por um profissional.",
        ),
    ]:
        if not db.scalar(select(Service.id).where(Service.name == name)):
            db.add(
                Service(
                    name=name,
                    description=description,
                    price_cents=price,
                    unit="projeto",
                    category="Projeto",
                    duration="Prazo definido na proposta",
                    responsible="Equipe de paisagismo Ateliê Verde",
                    delivery_mode=mode,
                    demo_asset="landscape",
                )
            )
    db.add(CatalogVersion(version=VERSION))
    db.commit()
