"""Commercial rules shared by API, checkout and spreadsheet imports."""

import hashlib
import json
import secrets
import unicodedata
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from .models import (
    AuditEvent,
    BusinessSequence,
    Ledger,
    Product,
    Project,
    Species,
    StockMove,
    Supplier,
    User,
    now,
)
from .security import passwords
from .transactions import locked


def normalized(value):
    return " ".join(
        "".join(
            c for c in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(c)
        )
        .casefold()
        .split()
    )


def product_identity(name, brand, variant):
    return hashlib.sha256(
        json.dumps([normalized(v) for v in [name, brand, variant]], ensure_ascii=False).encode()
    ).hexdigest()


def validate_candidate(cls, values):
    try:
        return cls.model_validate(values)
    except ValidationError as error:
        raise HTTPException(422, error.errors(include_url=False)[0]["msg"])


def snapshot(row):
    return {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
        if c.name not in {"password_hash", "identity_key", "request_payload"}
    }


def audit(db, actor, entity, row, before=None, action="Criar"):
    db.flush()
    db.add(
        AuditEvent(
            actor_id=actor.id,
            entity=entity,
            entity_id=row.id,
            action=action,
            before=before or {},
            after=snapshot(row),
        )
    )


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Código, documento, e-mail ou identificação já cadastrado.")


def next_code(db, prefix):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    db.execute(
        insert(BusinessSequence)
        .values(prefix=prefix, value=0)
        .on_conflict_do_nothing(index_elements=["prefix"])
    )
    while True:
        value = db.scalar(
            update(BusinessSequence)
            .where(BusinessSequence.prefix == prefix)
            .values(value=BusinessSequence.value + 1)
            .returning(BusinessSequence.value)
        )
        code = f"{prefix}-{value:03d}"
        cls, column = {
            "PRD": (Product, Product.sku),
            "CLI": (User, User.customer_code),
            "FOR": (Supplier, Supplier.code),
        }[prefix]
        if not db.scalar(select(cls.id).where(column == code)):
            return code


def pricing(body):
    rates = {key: Decimal(str(value)) / 100 for key, value in body.tax_rates.items()}
    cost = Decimal(body.cost_cents)
    margin = cost * Decimal(str(body.markup_percent)) / 100
    icms = rates.get("icms", Decimal(0))
    detailed = (
        icms
        + (rates.get("pis", Decimal(0)) + rates.get("cofins", Decimal(0))) * (1 - icms)
        + rates.get("other", Decimal(0))
    )
    effective = rates.get("effective", rates.get("simples", detailed))
    if effective >= 1:
        raise HTTPException(422, "A carga tributária deve ser inferior a 100%.")
    base = (cost + margin) / (1 - effective)
    amounts = {}
    for key, rate in rates.items():
        tax_base = base * (1 - rates.get("icms", Decimal(0))) if key in {"pis", "cofins"} else base
        amounts[key] = tax_base * rate
    # IPI is modeled outside the commercial base; all values are pricing estimates.
    total = base * (1 + rates.get("ipi", Decimal(0)))

    def cents(value):
        return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    result = {
        "cost_cents": body.cost_cents,
        "markup_cents": cents(margin),
        "tax_cents": cents(total) - body.cost_cents - cents(margin),
        "taxes": {k: int(v) for k, v in amounts.items()},
        "effective_percent": float(effective * 100),
        "suggested_price_cents": cents(total),
        "formula": "(custo × (1 + margem/100)) ÷ (1 − carga/100) × (1 + IPI/100)",
    }
    if result["suggested_price_cents"] > 100000000:
        raise HTTPException(422, "Preço calculado excede o limite permitido.")
    if result["taxes"]:
        remaining = result["tax_cents"] - sum(result["taxes"].values())
        by_fraction = sorted(
            amounts, key=lambda key: amounts[key] - int(amounts[key]), reverse=True
        )
        for key in by_fraction[:remaining]:
            result["taxes"][key] += 1
    return result


def supplier_for(db, id, previous=None):
    if not id:
        return None
    row = db.get(Supplier, id)
    if not row or (not row.active and id != previous):
        raise HTTPException(422, "Selecione um fornecedor ativo.")
    return row


def save_product(db, body, actor, row=None, initial_reason="Estoque inicial"):
    before = snapshot(row) if row else None
    fields = body.model_dump(mode="json", exclude_unset=bool(row))
    if row and "stock" in fields and fields["stock"] != row.stock:
        raise HTTPException(422, "Altere o saldo pela movimentação de estoque.")
    fields.pop("stock", None)
    candidate = {**(before or {}), **fields}
    validated = validate_candidate(type(body), candidate)
    if validated.species_id and not db.get(Species, validated.species_id):
        raise HTTPException(422, "Espécie não encontrada.")
    supplier_for(db, validated.supplier_id, row.supplier_id if row else None)
    identity = product_identity(validated.name, validated.brand, validated.variant)
    # Legacy records without an identity key still participate in duplicate checks.
    for existing in db.scalars(
        select(Product).where(
            Product.id != (row.id if row else 0),
            (Product.identity_key == identity) | Product.identity_key.is_(None),
        )
    ):
        if (
            existing.identity_key
            or product_identity(existing.name, existing.brand, existing.variant)
        ) == identity:
            raise HTTPException(409, "Produto já cadastrado com este nome, marca e variação.")
    fields["identity_key"] = identity
    if "tax_rates" in fields:
        fields["tax_rates"] = {key: float(value) for key, value in fields["tax_rates"].items()}
    fields["sku"] = validated.sku or (row.sku if row else next_code(db, "PRD"))
    if validated.pricing_mode == "Custo + margem":
        fields["price_cents"] = pricing(validated)["suggested_price_cents"]
        if fields["price_cents"] <= 0:
            raise HTTPException(422, "O preço calculado deve ser positivo.")
    if row:
        for key, value in fields.items():
            setattr(row, key, value)
    else:
        row = Product(**fields, stock=0)
        db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "SKU, código de barras ou produto já cadastrado.")
    if not before and body.stock:
        change_stock(
            db,
            row.id,
            body.stock,
            initial_reason,
            actor,
            origin="Cadastro",
            destination=row.location or "Estoque",
        )
    audit(db, actor, "Produto", row, before, "Editar" if before else "Criar")
    return row


def change_stock(db, product_id, quantity, reason, actor, **details):
    balance = db.scalar(
        update(Product)
        .where(
            Product.id == product_id,
            Product.stock + quantity >= 0,
            Product.stock + quantity <= 1000000,
        )
        .values(stock=Product.stock + quantity)
        .returning(Product.stock)
    )
    if balance is None:
        raise HTTPException(409, "Saldo insuficiente ou limite de estoque excedido.")
    move = StockMove(
        product_id=product_id,
        quantity=quantity,
        reason=reason,
        actor_id=actor.id,
        balance_before=balance - quantity,
        balance_after=balance,
        **details,
    )
    db.add(move)
    audit(db, actor, "Estoque", move, action="Entrada" if quantity > 0 else "Saída")
    return move


def record_stock(db, id, body, actor):
    try:
        return _record_stock(db, id, body, actor)
    except IntegrityError:
        db.rollback()
        old = (
            db.scalar(select(StockMove).where(StockMove.request_key == body.request_key))
            if body.request_key
            else None
        )
        payload = {"product_id": id, **body.model_dump(mode="json", exclude={"request_key"})}
        if not old or {"project_id": None, **old.request_payload} != payload:
            raise HTTPException(409, "Movimentação conflitante.")
        return db.get(Product, id)


def _record_stock(db, id, body, actor):
    payload = {"product_id": id, **body.model_dump(mode="json", exclude={"request_key"})}
    if body.request_key:
        old = db.scalar(select(StockMove).where(StockMove.request_key == body.request_key))
        if old:
            if {"project_id": None, **old.request_payload} != payload:
                raise HTTPException(409, "Identificador já usado em outra movimentação.")
            return db.get(Product, id)
    product = db.get(Product, id)
    if not product:
        raise HTTPException(404, "Produto não encontrado.")
    supplier = supplier_for(db, body.supplier_id)
    unit_cost = body.unit_cost_cents
    if body.project_id:
        project = locked(db, Project, body.project_id)
        if project.status not in {"Execução", "Manutenção"}:
            raise HTTPException(409, "Registre consumo em projetos na execução ou manutenção.")
        if not product.active:
            raise HTTPException(409, "Produto inativo não pode ser utilizado em um novo consumo.")
        if unit_cost is None and product.cost_cents > 0:
            unit_cost = product.cost_cents
    move = change_stock(
        db,
        id,
        body.quantity,
        body.reason,
        actor,
        origin=body.origin or (supplier.name if supplier else "Ajuste"),
        destination=body.destination or product.location or "Estoque",
        reference=body.reference,
        supplier_id=body.supplier_id,
        unit_cost_cents=unit_cost,
        project_id=body.project_id,
        request_key=body.request_key,
        request_payload=payload,
    )
    if body.record_payable:
        amount = body.quantity * body.unit_cost_cents
        if amount > 100000000:
            raise HTTPException(422, "Valor da compra excede o limite permitido.")
        entry = Ledger(
            direction="Despesa",
            source="Estoque",
            supplier_id=supplier.id,
            stock_move_id=move.id,
            counterparty=supplier.name,
            description=f"Compra: {product.name} · {body.reason}",
            due_date=body.due_date.isoformat(),
            amount_cents=amount,
            status="Pendente",
        )
        db.add(entry)
        audit(db, actor, "Financeiro", entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        old = (
            db.scalar(select(StockMove).where(StockMove.request_key == body.request_key))
            if body.request_key
            else None
        )
        if not old or {"project_id": None, **old.request_payload} != payload:
            raise HTTPException(409, "Movimentação conflitante.")
    return db.get(Product, id)


def save_customer(db, body, actor, row=None):
    before = snapshot(row) if row else None
    values = body.model_dump(mode="json", exclude={"password"}, exclude_unset=bool(row))
    if row:
        if row.role != "customer":
            raise HTTPException(404, "Cliente não encontrado.")
        # Validate document against the resulting person type on partial edits.
        validate_candidate(type(body), {**before, **values})
        for key, value in values.items():
            if key != "email" or value is not None:
                setattr(row, key, value)
    else:
        password = body.password or secrets.token_urlsafe(32)
        row = User(
            **values,
            customer_code=next_code(db, "CLI"),
            password_hash=passwords.hash(password),
            portal_enabled=bool(body.password),
            role="customer",
        )
        db.add(row)
    try:
        audit(db, actor, "Cliente", row, before, "Editar" if before else "Criar")
        commit(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "E-mail ou documento já cadastrado.")
    return row


def save_supplier(db, body, actor, row=None):
    before = snapshot(row) if row else None
    values = body.model_dump(mode="json")
    values["identity_key"] = normalized(body.name)
    values["updated_at"] = now()
    if row:
        for key, value in values.items():
            setattr(row, key, value)
    else:
        row = Supplier(**values, code=next_code(db, "FOR"))
        db.add(row)
    try:
        audit(db, actor, "Fornecedor", row, before, "Editar" if before else "Criar")
        commit(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Fornecedor ou CNPJ já cadastrado.")
    return row
