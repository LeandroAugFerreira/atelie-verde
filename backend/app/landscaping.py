from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import business
from .database import get_db
from .models import Project, Quote, Service, Species
from .schemas import BriefUpdate
from .security import admin, current_user
from .transactions import locked

router = APIRouter()


def validate_brief(db, brief):
    for plant in brief.plantings:
        if not db.get(Species, plant.species_id):
            raise HTTPException(422, "Uma espécie do planejamento não está cadastrada.")


def plant_list(brief):
    return [
        {"species_id": p.species_id, "quantity": p.quantity, "application": p.application}
        for p in brief.plantings
    ]


@router.put("/quotes/{id}/brief")
def update_quote_brief(
    id: int, body: BriefUpdate, db: Session = Depends(get_db), user=Depends(current_user)
):
    row = locked(db, Quote, id)
    if user.role != "admin" and row.customer_id != user.id:
        raise HTTPException(404, "Solicitação não encontrada.")
    if row.status not in {"Solicitado", "Em análise"}:
        raise HTTPException(
            409, "O planejamento desta solicitação já foi enviado para proposta ou encerrado."
        )
    if db.get(Service, row.service_id).category != "Projeto":
        raise HTTPException(422, "O planejamento visual se aplica a projetos paisagísticos.")
    if row.brief_revision != body.expected_revision:
        raise HTTPException(409, "O planejamento mudou. Atualize antes de salvar.")
    validate_brief(db, body.brief)
    before = business.snapshot(row)
    row.brief = body.brief.model_dump(mode="json")
    if body.brief.objective:
        row.description = body.brief.objective
    row.brief_revision += 1
    if body.address is not None:
        row.address = body.address
    row.area = body.brief.width * body.brief.length
    row.plants = plant_list(body.brief)
    business.audit(db, user, "Orçamento", row, before, "Editar planejamento")
    business.commit(db)
    return business.snapshot(row)


@router.put("/projects/{id}/brief")
def update_project_brief(
    id: int, body: BriefUpdate, db: Session = Depends(get_db), user=Depends(admin)
):
    row = locked(db, Project, id)
    if row.status == "Finalizado":
        raise HTTPException(
            409,
            "O planejamento finalizado é um documento de entrega. Inicie uma revisão na manutenção.",
        )
    if row.brief_revision != body.expected_revision:
        raise HTTPException(409, "O planejamento mudou. Atualize antes de salvar.")
    validate_brief(db, body.brief)
    before = business.snapshot(row)
    row.brief = body.brief.model_dump(mode="json")
    if body.brief.objective:
        row.description = body.brief.objective
    row.brief_revision += 1
    if body.address is not None:
        row.address = body.address
    row.area = body.brief.width * body.brief.length
    row.plants = plant_list(body.brief)
    business.audit(db, user, "Projeto", row, before, "Editar planejamento")
    business.commit(db)
    return business.snapshot(row)
