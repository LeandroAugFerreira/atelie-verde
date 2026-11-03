"""Illustrative references for demo projects; uploaded photos remain separate."""

from sqlalchemy import select

from .models import CatalogVersion, Project

VERSION = "atelie-verde-project-references-2026-10-04-v1"
REFERENCES = {
    "Projeto Residencial – Jardim Frontal": (
        "jardim-frontal",
        "Jardim frontal com hibiscos, lavandas, buxinhos e palmeiras-ráfis.",
    ),
    "Varanda viva · Pinheiros": (
        "varanda-pinheiros",
        "Varanda de apartamento com vasos, ervas aromáticas e folhagens.",
    ),
    "Jardim de entrada · Moema": (
        "entrada-moema",
        "Entrada residencial com bordaduras floridas e caminho de acesso.",
    ),
    "Área externa · Alto de Pinheiros": (
        "area-externa",
        "Área externa com gramado, canteiros e irrigação por aspersão.",
    ),
    "Pátio comercial · Vila Madalena": (
        "patio-comercial",
        "Pátio comercial com vegetação e espaço de encontro.",
    ),
}


def sync_project_references(db):
    if db.get(CatalogVersion, VERSION):
        return False
    for project in db.scalars(select(Project)):
        reference = REFERENCES.get(project.name)
        if reference and not project.reference_image_url:
            slug, description = reference
            project.reference_image_url = f"/projects/{slug}.png"
            project.reference_image_note = (
                f"{description} Referência visual ilustrativa criada com IA; "
                "não representa uma fotografia da obra executada."
            )
    db.add(CatalogVersion(version=VERSION))
    db.commit()
    return True
