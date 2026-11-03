import csv
import io
import uuid
import zipfile
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import business
from .clock import business_date
from .clock import today as business_today
from .database import DATA_DIR, get_db
from .main import data, get, own, rows
from .models import (
    Appointment,
    Document,
    Favorite,
    Ledger,
    Order,
    Product,
    Project,
    Quote,
    Review,
    Service,
    Setting,
    StockMove,
    User,
)
from .schemas import (
    AppointmentInput,
    LedgerInput,
    ProductInput,
    QuoteStatus,
    ReviewInput,
    SettingsInput,
)
from .security import admin, current_user
from .transactions import locked

router = APIRouter()


@router.get("/appointments")
def appointments(db: Session = Depends(get_db), user=Depends(current_user)):
    query = select(Appointment).order_by(Appointment.date, Appointment.start_time)
    if user.role != "admin":
        query = query.where(Appointment.customer_id == user.id)
    return [data(a) for a in db.scalars(query)]


def validate_appointment(body, db, id=0):
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    get(db, Service, body.service_id)
    if get(db, User, body.customer_id).role != "customer":
        raise HTTPException(422, "Selecione um cliente.")
    # Serializa a agenda por prestador para impedir agendamentos simultâneos conflitantes.
    db.execute(select(User.id).where(User.role == "admin").with_for_update()).all()
    if body.status != "Cancelado":
        conflict = db.scalar(
            select(Appointment.id).where(
                Appointment.id != id,
                Appointment.date == body.date.isoformat(),
                Appointment.responsible == body.responsible,
                Appointment.status != "Cancelado",
                Appointment.start_time < body.end_time,
                Appointment.end_time > body.start_time,
            )
        )
        if conflict:
            raise HTTPException(409, "O responsável já tem um compromisso nesse horário.")


@router.post("/appointments", status_code=201)
def create_appointment(body: AppointmentInput, db: Session = Depends(get_db), user=Depends(admin)):
    validate_appointment(body, db)
    row = Appointment(**body.model_dump(mode="json"))
    db.add(row)
    db.commit()
    return data(row)


@router.put("/appointments/{id}")
def edit_appointment(
    id: int, body: AppointmentInput, db: Session = Depends(get_db), user=Depends(admin)
):
    row = get(db, Appointment, id)
    validate_appointment(body, db, id)
    for k, v in body.model_dump(mode="json").items():
        setattr(row, k, v)
    db.commit()
    return data(row)


@router.get("/ledger")
def ledger(db: Session = Depends(get_db), user=Depends(admin)):
    return [
        data(entry)
        for entry in db.scalars(select(Ledger).order_by(Ledger.due_date.desc(), Ledger.id.desc()))
    ]


@router.post("/ledger", status_code=201)
def create_ledger(body: LedgerInput, db: Session = Depends(get_db), user=Depends(admin)):
    if body.customer_id:
        get(db, User, body.customer_id)
    if body.supplier_id:
        if body.direction != "Despesa":
            raise HTTPException(422, "Fornecedor deve estar vinculado a uma despesa.")
        business.supplier_for(db, body.supplier_id)
    fields = body.model_dump(mode="json")
    fields["paid_date"] = fields["paid_date"] or ""
    row = Ledger(**fields)
    db.add(row)
    business.audit(db, user, "Financeiro", row)
    db.commit()
    return data(row)


@router.patch("/ledger/{id}/pay")
def pay_ledger(id: int, paid_date: date, db: Session = Depends(get_db), user=Depends(admin)):
    row = get(db, Ledger, id)
    if row.order_id:
        order = locked(db, Order, row.order_id)
        if order.status == "Cancelado":
            raise HTTPException(409, "Pedido cancelado não pode receber pagamento.")
    row = locked(db, Ledger, id)
    before = business.snapshot(row)
    result = db.execute(
        update(Ledger)
        .where(Ledger.id == id, Ledger.status == "Pendente")
        .values(status="Pago", paid_date=paid_date.isoformat())
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Somente uma conta pendente pode ser baixada.")
    business.audit(db, user, "Financeiro", row, before, "Pagar")
    db.commit()
    return data(row)


@router.patch("/quotes/{id}/status")
def quote_status(
    id: int, body: QuoteStatus, db: Session = Depends(get_db), user=Depends(current_user)
):
    row = locked(db, Quote, id)
    own(row, user)
    if row.status in ("Aprovado", "Rejeitado"):
        raise HTTPException(409, "Este orçamento já foi encerrado.")
    if body.status == "Em análise" and user.role != "admin":
        raise HTTPException(403, "Somente o administrador pode iniciar a análise.")
    row.status = body.status
    db.commit()
    return data(row)


@router.get("/reviews")
def reviews(db: Session = Depends(get_db)):
    return [
        {**data(row), "customer_name": name}
        for row, name in db.execute(
            select(Review, User.name).join(User, User.id == Review.customer_id).order_by(Review.id)
        )
    ]


@router.post("/products/{id}/reviews", status_code=201)
def create_review(
    id: int, body: ReviewInput, db: Session = Depends(get_db), user=Depends(current_user)
):
    get(db, Product, id)
    purchased = any(
        any(i["product_id"] == id for i in o.items)
        for o in db.scalars(
            select(Order).where(Order.customer_id == user.id, Order.status == "Confirmado")
        )
    )
    if not purchased:
        raise HTTPException(403, "A avaliação fica disponível após a compra deste produto.")
    row = Review(product_id=id, customer_id=user.id, **body.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Você já avaliou este produto.")
    return data(row)


@router.get("/favorites")
def favorites(db: Session = Depends(get_db), user=Depends(current_user)):
    return [
        f.product_id for f in db.scalars(select(Favorite).where(Favorite.customer_id == user.id))
    ]


@router.post("/favorites/{id}", status_code=201)
def add_favorite(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    get(db, Product, id)
    db.add(Favorite(product_id=id, customer_id=user.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return {"product_id": id}


@router.delete("/favorites/{id}", status_code=204)
def remove_favorite(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.scalar(
        select(Favorite).where(Favorite.product_id == id, Favorite.customer_id == user.id)
    )
    if row:
        db.delete(row)
        db.commit()
    return Response(status_code=204)


@router.get("/settings")
def settings(db: Session = Depends(get_db), user=Depends(admin)):
    row = db.get(Setting, 1)
    return (
        row.value
        if row
        else {
            "name": "Ateliê Verde",
            "email": "contato@atelieverde.local",
            "phone": "",
            "address": "",
            "low_stock_alert": True,
            "quote_alert": True,
        }
    )


@router.put("/settings")
def edit_settings(body: SettingsInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = db.get(Setting, 1)
    if row:
        row.value = body.model_dump()
    else:
        db.add(Setting(id=1, value=body.model_dump()))
    db.commit()
    return body.model_dump()


@router.get("/projects/{id}/documents")
def documents(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    project = get(db, Project, id)
    own(project, user)
    return [
        data(d)
        for d in db.scalars(
            select(Document).where(
                or_(Document.project_id == id, Document.quote_id == project.quote_id)
                if project.quote_id
                else Document.project_id == id
            )
        )
    ]


@router.post("/projects/{id}/documents", status_code=201)
async def upload_document(
    id: int, file: UploadFile = File(), db: Session = Depends(get_db), user=Depends(admin)
):
    get(db, Project, id)
    return await store_document(file, db, project_id=id)


@router.get("/quotes/{id}/documents")
def quote_documents(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    own(get(db, Quote, id), user)
    return [data(row) for row in db.scalars(select(Document).where(Document.quote_id == id))]


@router.post("/quotes/{id}/documents", status_code=201)
async def upload_quote_document(
    id: int, file: UploadFile = File(), db: Session = Depends(get_db), user=Depends(current_user)
):
    row = locked(db, Quote, id)
    own(row, user)
    if user.role != "admin" and row.status not in {"Solicitado", "Em análise"}:
        raise HTTPException(
            409, "Os anexos desta solicitação já foram enviados para proposta ou encerrados."
        )
    return await store_document(file, db, quote_id=id)


async def store_document(file, db, project_id=None, quote_id=None):
    content = await file.read(10 * 1024 * 1024 + 1)
    await file.close()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Documento limitado a 10 MB.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(422, "Envie um documento PDF.")
    directory = DATA_DIR / "documents"
    directory.mkdir(exist_ok=True)
    filename = f"{uuid.uuid4().hex}.pdf"
    (directory / filename).write_bytes(content)
    row = Document(
        project_id=project_id,
        quote_id=quote_id,
        name=Path(file.filename or "documento.pdf").name[:200],
        filename=filename,
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        (directory / filename).unlink(missing_ok=True)
        raise
    return data(row)


@router.get("/documents/{id}/content")
def download_document(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = get(db, Document, id)
    own(get(db, Project, row.project_id) if row.project_id else get(db, Quote, row.quote_id), user)
    if not (DATA_DIR / "documents" / row.filename).is_file():
        raise HTTPException(404, "Arquivo do documento não encontrado.")
    return FileResponse(
        DATA_DIR / "documents" / row.filename,
        media_type="application/pdf",
        filename=row.name,
        headers={"Cache-Control": "private, no-store"},
    )


@router.delete("/documents/{id}", status_code=204)
def delete_document(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = get(db, Document, id)
    if user.role != "admin":
        if row.project_id:
            raise HTTPException(403, "Somente a equipe pode excluir documentos de entrega.")
        quote = locked(db, Quote, row.quote_id)
        own(quote, user)
        if quote.status not in {"Solicitado", "Em análise"}:
            raise HTTPException(
                409,
                "Os documentos desta solicitação já foram enviados para proposta ou encerrados.",
            )
    path = DATA_DIR / "documents" / row.filename
    db.delete(row)
    db.commit()
    path.unlink(missing_ok=True)
    return Response(status_code=204)


@router.post("/products-import")
async def import_products(
    file: UploadFile = File(), db: Session = Depends(get_db), user=Depends(admin)
):
    content = await file.read(2 * 1024 * 1024 + 1)
    await file.close()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "Planilha limitada a 2 MB.")
    try:
        if (file.filename or "").lower().endswith(".xlsx"):
            from openpyxl import load_workbook

            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if sum(f.file_size for f in archive.infolist()) > 20 * 1024 * 1024:
                    raise ValueError("Arquivo descompactado excede 20 MB.")
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
            iterator = workbook.active.iter_rows(values_only=True)
            headers = list(next(iterator))
            raw = []
            for index, values in enumerate(iterator):
                if index >= 1000:
                    raise ValueError("Limite de 1.000 linhas.")
                raw.append(dict(zip(headers, values)))
            workbook.close()
        elif (file.filename or "").lower().endswith(".csv"):
            text = content.decode("utf-8-sig")
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,")
            raw = list(csv.DictReader(io.StringIO(text), dialect=dialect))
        else:
            raise ValueError("Use CSV UTF-8 ou XLSX.")
        if not raw or len(raw) > 1000:
            raise ValueError("Informe de 1 a 1.000 linhas.")
        inputs = [
            ProductInput.model_validate({k: v for k, v in r.items() if v is not None and v != ""})
            for r in raw
        ]
        skus = [r.sku for r in inputs if r.sku]
        if len(set(skus)) != len(skus):
            raise ValueError("A planilha contém SKUs duplicados.")
        for index, body in enumerate(inputs, start=2):
            try:
                business.save_product(db, body, user, initial_reason="Importação de planilha")
            except HTTPException as error:
                db.rollback()
                raise HTTPException(
                    error.status_code,
                    f"Linha {index}: {error.detail}. Nenhuma linha foi importada.",
                )
        db.commit()
        return {"imported": len(inputs)}
    except (
        ValueError,
        ValidationError,
        KeyError,
        StopIteration,
        zipfile.BadZipFile,
        UnicodeDecodeError,
    ) as e:
        db.rollback()
        raise HTTPException(422, f"Importação cancelada: {str(e)[:500]}")
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Um SKU foi cadastrado durante a importação. Nenhuma linha foi importada."
        )


@router.get("/analytics")
def analytics(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    user=Depends(admin),
):
    today = business_today()
    start = start or today.replace(day=1)
    end = end or today
    if end < start:
        raise HTTPException(422, "Período inválido.")

    def inside(value):
        return bool(value) and start.isoformat() <= business_date(value) <= end.isoformat()

    accounts = rows(db, Ledger)
    paid = [entry for entry in accounts if entry.status == "Pago" and inside(entry.paid_date)]
    income = sum(entry.amount_cents for entry in paid if entry.direction == "Receita")
    expense = sum(entry.amount_cents for entry in paid if entry.direction == "Despesa")
    late = [
        entry
        for entry in accounts
        if entry.status == "Pendente" and entry.due_date < today.isoformat()
    ]
    all_orders = rows(db, Order)
    orders = [o for o in all_orders if o.status == "Confirmado" and inside(o.created_at)]
    product_ids = {i["product_id"] for order in orders for i in order.items}
    products_by_id = {
        p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids)))
    }
    sales, category = {}, {}
    for o in orders:
        for item in o.items:
            product = products_by_id[item["product_id"]]
            previous = sales.get(
                product.id, {"product": data(product), "quantity": 0, "revenue_cents": 0}
            )
            previous["quantity"] += item["quantity"]
            previous["revenue_cents"] += item["quantity"] * item["price_cents"]
            sales[product.id] = previous
            sale_category = item.get("category", product.category)
            category[sale_category] = category.get(sale_category, 0) + item["quantity"]
    origin = {
        name: sum(
            entry.amount_cents
            for entry in paid
            if entry.direction == "Receita" and entry.source == name
        )
        for name in ["Loja", "Serviços", "Projetos", "Outros"]
    }
    monthly = []
    for month in range(1, 13):
        key = f"{end.year}-{month:02d}"
        items = [
            entry
            for entry in accounts
            if entry.status == "Pago" and entry.paid_date.startswith(key)
        ]
        monthly.append(
            {
                "month": key,
                "income": sum(
                    entry.amount_cents for entry in items if entry.direction == "Receita"
                ),
                "expense": sum(
                    entry.amount_cents for entry in items if entry.direction == "Despesa"
                ),
            }
        )
    previous_start = start - (end - start + timedelta(days=1))
    previous_end = start - timedelta(days=1)
    old_income = sum(
        entry.amount_cents
        for entry in accounts
        if entry.status == "Pago"
        and entry.direction == "Receita"
        and previous_start.isoformat() <= entry.paid_date <= previous_end.isoformat()
    )
    growth = round((income - old_income) / old_income * 100, 1) if old_income else None
    appointments = rows(db, Appointment)
    projects = rows(db, Project)
    clients = [u for u in rows(db, User) if u.role == "customer"]
    count_by_customer = {}
    for o in all_orders:
        if o.status == "Confirmado":
            count_by_customer[o.customer_id] = count_by_customer.get(o.customer_id, 0) + 1
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "income": income,
        "expense": expense,
        "profit": income - expense,
        "overdue_income": sum(entry.amount_cents for entry in late if entry.direction == "Receita"),
        "growth": growth,
        "products_sold": sum(i["quantity"] for o in orders for i in o.items),
        "services_completed": sum(a.status == "Concluído" and inside(a.date) for a in appointments),
        "active_services": sum(a.status in ("Agendado", "Em execução") for a in appointments),
        "teams": len(
            {a.responsible for a in appointments if a.status in ("Agendado", "Em execução")}
        ),
        "service_income": origin["Serviços"],
        "projects_active": sum(
            p.status in ("Aprovado", "Planejamento", "Execução", "Manutenção") for p in projects
        ),
        "customers_active": sum(c.active for c in clients),
        "customers_new": sum(inside(c.created_at) for c in clients),
        "customers_recurring": sum(n > 1 for n in count_by_customer.values()),
        "average_ticket": round(sum(o.total_cents for o in orders) / len(orders)) if orders else 0,
        "monthly": monthly,
        "categories": category,
        "origins": origin,
        "top_products": sorted(sales.values(), key=lambda x: -x["quantity"])[:5],
        "stock_moves_month": sum(inside(m.created_at) for m in rows(db, StockMove)),
        "accounts_receivable": [
            data(entry)
            for entry in accounts
            if entry.direction == "Receita" and entry.status == "Pendente"
        ],
        "accounts_payable": [
            data(entry)
            for entry in accounts
            if entry.direction == "Despesa" and entry.status == "Pendente"
        ],
    }
