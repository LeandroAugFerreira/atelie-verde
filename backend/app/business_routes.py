import re
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import BigInteger, case, cast, func, select
from sqlalchemy.orm import Session

from . import business
from .clock import BUSINESS_TIMEZONE
from .database import get_db
from .models import AuditEvent, Product, Project, StockMove, Supplier, User
from .schemas import ActiveInput, PricingInput, SupplierInput
from .security import admin

router = APIRouter()


@router.get("/admin/data-quality")
def data_quality(db: Session = Depends(get_db), actor=Depends(admin)):
    from .quality import check_data

    return check_data(db)


@router.get("/projects/{id}/stock-usage")
def project_stock_usage(
    id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    actor=Depends(admin),
):
    if not db.get(Project, id):
        raise HTTPException(404, "Projeto não encontrado.")
    condition = (StockMove.project_id == id) & (StockMove.quantity < 0)
    total, units, cost, unknown = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(-StockMove.quantity), 0),
            func.coalesce(
                func.sum(cast(-StockMove.quantity, BigInteger) * StockMove.unit_cost_cents), 0
            ),
            func.coalesce(func.sum(case((StockMove.unit_cost_cents.is_(None), 1), else_=0)), 0),
        ).where(condition)
    ).one()
    query = (
        select(StockMove, Product.name, Product.unit, User.name)
        .join(Product, Product.id == StockMove.product_id)
        .join(User, User.id == StockMove.actor_id)
        .where(condition)
        .order_by(StockMove.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return {
        "total": total,
        "units": units,
        "cost_cents": cost,
        "uncosted_moves": unknown,
        "items": [
            {
                **business.snapshot(move),
                "product_name": name,
                "unit": unit,
                "actor_name": actor_name,
                "total_cost_cents": -move.quantity * move.unit_cost_cents
                if move.unit_cost_cents is not None
                else None,
            }
            for move, name, unit, actor_name in db.execute(query)
        ],
    }


@router.get("/suppliers")
def suppliers(
    q: str = "",
    category: str = "",
    active: bool | None = None,
    db: Session = Depends(get_db),
    actor=Depends(admin),
):
    query = select(Supplier).order_by(Supplier.name)
    if category:
        query = query.where(Supplier.category == category)
    if active is not None:
        query = query.where(Supplier.active == active)
    return [
        business.snapshot(row)
        for row in db.scalars(query)
        if business.normalized(q)
        in business.normalized(
            " ".join(
                [
                    row.name,
                    row.trade_name,
                    row.code,
                    row.document or "",
                    row.city,
                    row.email,
                    row.contact_name,
                ]
            )
        )
        or (
            bool(re.fullmatch(r"[\d./\-\s]+", q))
            and len(re.sub(r"\D", "", q)) >= 3
            and re.sub(r"\D", "", q) in (row.document or "")
        )
    ]


@router.post("/suppliers", status_code=201)
def create_supplier(body: SupplierInput, db: Session = Depends(get_db), actor=Depends(admin)):
    return business.snapshot(business.save_supplier(db, body, actor))


@router.put("/suppliers/{id}")
def edit_supplier(
    id: int, body: SupplierInput, db: Session = Depends(get_db), actor=Depends(admin)
):
    row = db.get(Supplier, id)
    if not row:
        raise HTTPException(404, "Fornecedor não encontrado.")
    return business.snapshot(business.save_supplier(db, body, actor, row))


@router.patch("/suppliers/{id}/status")
def supplier_status(
    id: int, body: ActiveInput, db: Session = Depends(get_db), actor=Depends(admin)
):
    row = db.get(Supplier, id)
    if not row:
        raise HTTPException(404, "Fornecedor não encontrado.")
    before = business.snapshot(row)
    row.active = body.active
    business.audit(db, actor, "Fornecedor", row, before, "Ativar" if body.active else "Inativar")
    business.commit(db)
    return business.snapshot(row)


@router.post("/admin/pricing/preview")
def pricing_preview(body: PricingInput, actor=Depends(admin)):
    return business.pricing(body)


@router.get("/audit-events")
def audit_events(
    entity: str = "",
    q: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    actor=Depends(admin),
):
    query = select(AuditEvent)
    if entity:
        query = query.where(AuditEvent.entity == entity)
    if q:
        query = query.where(AuditEvent.action.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    users = {u.id: u.name for u in db.scalars(select(User))}
    return {
        "total": total,
        "items": [
            {**business.snapshot(row), "actor_name": users.get(row.actor_id, "")}
            for row in db.scalars(query.order_by(AuditEvent.id.desc()).offset(offset).limit(limit))
        ],
    }


@router.get("/stock-history")
def stock_history(
    product_id: int | None = None,
    supplier_id: int | None = None,
    kind: str = "",
    start: date | None = None,
    end: date | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    actor=Depends(admin),
):
    query = select(StockMove)
    if start and end and end < start:
        raise HTTPException(422, "O fim do período deve ser igual ou posterior ao início.")
    if product_id:
        query = query.where(StockMove.product_id == product_id)
    if supplier_id:
        query = query.where(StockMove.supplier_id == supplier_id)
    if kind == "Entrada":
        query = query.where(StockMove.quantity > 0)
    if kind == "Saída":
        query = query.where(StockMove.quantity < 0)
    if start:
        lower = (
            datetime.combine(start, time.min, BUSINESS_TIMEZONE)
            .astimezone(timezone.utc)
            .isoformat()
        )
        query = query.where(StockMove.created_at >= lower)
    if end:
        upper = (
            datetime.combine(end + timedelta(days=1), time.min, BUSINESS_TIMEZONE)
            .astimezone(timezone.utc)
            .isoformat()
        )
        query = query.where(StockMove.created_at < upper)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    names = {p.id: p.name for p in db.scalars(select(Product))}
    actors = {u.id: u.name for u in db.scalars(select(User))}
    return {
        "total": total,
        "items": [
            {
                **business.snapshot(row),
                "product_name": names.get(row.product_id, ""),
                "actor_name": actors.get(row.actor_id, ""),
            }
            for row in db.scalars(query.order_by(StockMove.id.desc()).offset(offset).limit(limit))
        ],
    }
