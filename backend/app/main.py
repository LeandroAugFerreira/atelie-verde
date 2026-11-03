import io
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image as PILImage
from PIL import ImageOps, UnidentifiedImageError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import business
from .checkout import checkout
from .clock import today as business_today
from .database import DATA_DIR, Base, SessionLocal, engine, get_db
from .landscaping import plant_list, validate_brief
from .models import (
    Image,
    Ledger,
    Order,
    Product,
    Project,
    ProjectEvent,
    Quote,
    Service,
    Species,
    StockMove,
    User,
)
from .plant_groups import plant_groups
from .schemas import (
    CustomerCreate,
    CustomerInput,
    Login,
    OrderInput,
    ProductInput,
    ProfileInput,
    ProjectInput,
    QuoteInput,
    QuotePrice,
    Register,
    ServiceInput,
    SpeciesInput,
    StatusInput,
    StockInput,
)
from .security import admin, current_user, passwords, token_for
from .service_catalog import details as service_details
from .transactions import locked

STAGES = ["Orçamento", "Aprovado", "Planejamento", "Execução", "Finalizado", "Manutenção"]
UPLOADS = DATA_DIR / "uploads"
UPLOADS.mkdir(exist_ok=True)
PILImage.MAX_IMAGE_PIXELS = 16000000


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    if os.getenv("SEED_DEMO", "false").lower() == "true":
        from .seed import seed

        with SessionLocal() as db:
            seed(db)
            from .catalog import sync_catalog

            sync_catalog(db)
            from .photo_quality import sync_photo_quality

            sync_photo_quality(db)
            from .photo_curated import sync_curated_photos

            sync_curated_photos(db)
            from .project_references import sync_project_references

            sync_project_references(db)
            from .commercial_seed import sync_commercial

            sync_commercial(db)
            from .demo_details import complete_demo, complete_demo_sales, link_demo_projects

            complete_demo(db)
            complete_demo_sales(db)
            link_demo_projects(db)
            from .service_catalog import sync_offers

            sync_offers(db)
            from .expanded_demo import expand_shop, rename_demo_profiles

            rename_demo_profiles(db)
            expand_shop(db)
            from .product_media import sync_product_media

            sync_product_media(db)
            from .project_demo import seed_project_portfolio

            seed_project_portfolio(db)
            from .customer_activity_demo import seed_customer_activity

            seed_customer_activity(db)
    from .assistant_provider import warmup

    warmup()
    yield
    from .assistant_connections import close_all

    close_all()


app = FastAPI(title="Ateliê Verde API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request, error):
    if request.url.path.startswith(("/api/assistant/admin-ai", "/api/assistant/connection")):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Confira os campos informados. Valores sensíveis não são exibidos na mensagem de validação."
            },
        )
    return await request_validation_exception_handler(request, error)


from .assistant_connections import router as connection_router

app.include_router(connection_router, prefix="/api")
from .assistant_admin_ai import router as admin_ai_router

app.include_router(admin_ai_router, prefix="/api")

from .assistant_request import cloud_permitted, local_access


@app.middleware("http")
async def personal_cloud_scope(request, call_next):
    token = cloud_permitted.set(local_access(request))
    try:
        return await call_next(request)
    finally:
        cloud_permitted.reset(token)


app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(
        ","
    ),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def data(row):
    return {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
        if c.name not in {"password_hash", "identity_key", "request_payload"}
    }


def get(db, cls, id):
    row = db.get(cls, id)
    if not row:
        raise HTTPException(404, "Registro não encontrado.")
    return row


def own(row, user):
    if user.role != "admin" and row.customer_id != user.id:
        raise HTTPException(404, "Registro não encontrado.")


def rows(db, cls):
    return db.scalars(select(cls).order_by(cls.id)).all()


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(body: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if (
        not user
        or not user.active
        or not user.portal_enabled
        or not passwords.verify(body.password, user.password_hash)
    ):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    return {"access_token": token_for(user), "user": data(user)}


@app.post("/api/auth/register", status_code=201)
def register(body: Register, db: Session = Depends(get_db)):
    fields = body.model_dump(exclude={"password"})
    fields["email"] = fields["email"].strip().lower()
    user = User(
        **fields,
        customer_code=business.next_code(db, "CLI"),
        password_hash=passwords.hash(body.password),
    )
    db.add(user)
    try:
        db.flush()
        business.audit(db, user, "Cliente", user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Este e-mail já está cadastrado.")
    return {"access_token": token_for(user), "user": data(user)}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return data(user)


@app.put("/api/auth/profile")
def edit_profile(body: ProfileInput, db: Session = Depends(get_db), user=Depends(current_user)):
    values = body.model_dump()
    values["email"] = values["email"].strip().lower()
    for key, value in values.items():
        setattr(user, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Este e-mail já está cadastrado.")
    return data(user)


@app.get("/api/species")
def species(
    light: str = "",
    size: str = "",
    objective: str = "",
    difficulty: str = "",
    environment: str = "",
    group: str = "",
    db: Session = Depends(get_db),
):
    query = select(Species)
    for column, value in [
        (Species.light, light),
        (Species.size, size),
        (Species.difficulty, difficulty),
    ]:
        if value:
            query = query.where(column == value)
    if environment:
        query = query.where(Species.environment.in_([environment, "Ambos"]))
    if objective:
        query = query.where(func.lower(Species.use).contains(objective.lower()))
    return [
        {**data(s), "plant_groups": plant_groups(s)}
        for s in db.scalars(query.order_by(Species.name))
        if not group or group in plant_groups(s)
    ]


@app.post("/api/species", status_code=201)
def create_species(body: SpeciesInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = Species(**body.model_dump())
    db.add(row)
    db.commit()
    return data(row)


@app.put("/api/species/{id}")
def edit_species(id: int, body: SpeciesInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = get(db, Species, id)
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    return data(row)


@app.get("/api/products")
def products(db: Session = Depends(get_db)):
    return [
        {
            k: v
            for k, v in data(p).items()
            if k
            not in {
                "cost_cents",
                "markup_percent",
                "pricing_mode",
                "supplier_id",
                "tax_regime",
                "tax_rates",
                "ncm",
            }
        }
        for p in db.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.id))
    ]


@app.get("/api/admin/products")
def all_products(db: Session = Depends(get_db), user=Depends(admin)):
    return [data(p) for p in rows(db, Product)]


@app.post("/api/products", status_code=201)
def create_product(body: ProductInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = business.save_product(db, body, user)
    business.commit(db)
    return data(row)


@app.put("/api/products/{id}")
def edit_product(id: int, body: ProductInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = get(db, Product, id)
    business.save_product(db, body, user, row)
    business.commit(db)
    return data(row)


@app.post("/api/products/{id}/stock")
def stock(id: int, body: StockInput, db: Session = Depends(get_db), user=Depends(admin)):
    return data(business.record_stock(db, id, body, user))


@app.get("/api/stock-moves")
def stock_moves(db: Session = Depends(get_db), user=Depends(admin)):
    return [data(m) for m in db.scalars(select(StockMove).order_by(StockMove.id.desc()).limit(100))]


@app.get("/api/services")
def services(db: Session = Depends(get_db)):
    return [{**data(s), "details": service_details(s)} for s in rows(db, Service)]


@app.post("/api/services", status_code=201)
def create_service(body: ServiceInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = Service(**body.model_dump())
    db.add(row)
    db.commit()
    return data(row)


@app.put("/api/services/{id}")
def edit_service(id: int, body: ServiceInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = get(db, Service, id)
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    return data(row)


@app.get("/api/customers")
def customers(db: Session = Depends(get_db), user=Depends(admin)):
    return [
        data(u) for u in db.scalars(select(User).where(User.role == "customer").order_by(User.name))
    ]


@app.post("/api/customers", status_code=201)
def create_customer(body: CustomerCreate, db: Session = Depends(get_db), user=Depends(admin)):
    return data(business.save_customer(db, body, user))


@app.put("/api/customers/{id}")
def edit_customer(id: int, body: CustomerInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = get(db, User, id)
    if row.role != "customer":
        raise HTTPException(404, "Cliente não encontrado.")
    business.save_customer(db, body, user, row)
    return data(row)


@app.get("/api/quotes")
def quotes(db: Session = Depends(get_db), user=Depends(current_user)):
    query = select(Quote).order_by(Quote.id.desc())
    if user.role != "admin":
        query = query.where(Quote.customer_id == user.id)
    return [data(q) for q in db.scalars(query)]


@app.post("/api/quotes", status_code=201)
def create_quote(body: QuoteInput, db: Session = Depends(get_db), user=Depends(current_user)):
    service = get(db, Service, body.service_id)
    if not service.active:
        raise HTTPException(422, "Selecione um serviço ativo.")
    customer_id = body.customer_id if user.role == "admin" and body.customer_id else user.id
    if user.role != "admin" and body.customer_id and body.customer_id != user.id:
        raise HTTPException(403, "Solicite um orçamento para sua própria conta.")
    customer = get(db, User, customer_id)
    if customer.role != "customer" or not customer.active:
        raise HTTPException(422, "Selecione um cliente ativo.")
    for plant in body.plants:
        get(db, Species, plant.species_id)
    fields = body.model_dump(exclude={"customer_id", "brief"}, mode="json")
    if service.delivery_mode == "Virtual" and not body.brief:
        raise HTTPException(422, "Preencha o levantamento e a planta no planejador virtual.")
    if body.brief:
        if service.category != "Projeto":
            raise HTTPException(422, "O planejamento visual se aplica a projetos paisagísticos.")
        validate_brief(db, body.brief)
        fields.update(
            brief=body.brief.model_dump(mode="json"),
            plants=plant_list(body.brief),
            area=body.brief.width * body.brief.length,
        )
    row = Quote(**fields, customer_id=customer_id)
    db.add(row)
    db.commit()
    return data(row)


@app.patch("/api/quotes/{id}/price")
def price_quote(id: int, body: QuotePrice, db: Session = Depends(get_db), user=Depends(admin)):
    row = locked(db, Quote, id)
    if row.status in {"Aprovado", "Rejeitado"}:
        raise HTTPException(409, "Este orçamento já foi encerrado.")
    row.amount_cents = body.amount_cents
    if body.plants is not None:
        if row.brief and [p.model_dump() for p in body.plants] != row.plants:
            raise HTTPException(
                422, "Atualize as espécies na planta visual antes de alterar a proposta."
            )
        for p in body.plants:
            get(db, Species, p.species_id)
        row.plants = [p.model_dump() for p in body.plants]
    if body.materials is not None:
        row.materials = [m.model_dump() for m in body.materials]
    row.status = "Enviado"
    db.commit()
    return data(row)


@app.post("/api/quotes/{id}/approve")
def approve_quote(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = locked(db, Quote, id)
    own(row, user)
    result = db.execute(
        update(Quote).where(Quote.id == id, Quote.status == "Enviado").values(status="Aprovado")
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Somente um orçamento enviado pode ser aprovado.")
    today = business_today().isoformat()
    project = Project(
        name=f"{get(db, Service, row.service_id).name} · {get(db, User, row.customer_id).name}",
        customer_id=row.customer_id,
        quote_id=id,
        address=row.address,
        area=row.area,
        budget_cents=row.amount_cents,
        status="Aprovado",
        start_date=today,
        end_date=today,
        description=row.description,
        plants=row.plants,
        materials=row.materials,
        brief=row.brief or {},
        delivery_mode=get(db, Service, row.service_id).delivery_mode,
    )
    db.add(project)
    db.flush()
    db.add(ProjectEvent(project_id=project.id, status="Aprovado", actor_id=user.id))
    db.commit()
    return data(project)


@app.get("/api/projects")
def projects(db: Session = Depends(get_db), user=Depends(current_user)):
    query = select(Project).order_by(Project.id.desc())
    if user.role != "admin":
        query = query.where(Project.customer_id == user.id)
    return [data(p) for p in db.scalars(query)]


def validate_project(body, db, previous_customer_id=None):
    customer = get(db, User, body.customer_id)
    if customer.role != "customer" or (
        not customer.active and body.customer_id != previous_customer_id
    ):
        raise HTTPException(422, "Selecione um cliente ativo.")
    for plant in body.plants:
        get(db, Species, plant.species_id)


@app.post("/api/projects", status_code=201)
def create_project(body: ProjectInput, db: Session = Depends(get_db), user=Depends(admin)):
    validate_project(body, db)
    row = Project(**body.model_dump(mode="json"))
    db.add(row)
    db.flush()
    db.add(ProjectEvent(project_id=row.id, status=row.status, actor_id=user.id))
    db.commit()
    return data(row)


@app.put("/api/projects/{id}")
def edit_project(id: int, body: ProjectInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = get(db, Project, id)
    validate_project(body, db, row.customer_id)
    if row.brief and [p.model_dump() for p in body.plants] != row.plants:
        raise HTTPException(422, "Atualize as espécies na aba Planta 2D deste projeto.")
    if row.quote_id and body.customer_id != row.customer_id:
        raise HTTPException(409, "O cliente está vinculado ao orçamento aprovado.")
    for k, v in body.model_dump(mode="json").items():
        setattr(row, k, v)
    db.commit()
    return data(row)


@app.patch("/api/projects/{id}/status")
def project_status(id: int, body: StatusInput, db: Session = Depends(get_db), user=Depends(admin)):
    row = locked(db, Project, id)
    index = STAGES.index(row.status)
    if index == len(STAGES) - 1 or body.status != STAGES[index + 1]:
        raise HTTPException(409, "Avance uma etapa por vez no fluxo do projeto.")
    result = db.execute(
        update(Project)
        .where(Project.id == id, Project.status == row.status)
        .values(status=body.status)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "O projeto mudou. Atualize a página.")
    db.add(ProjectEvent(project_id=id, status=body.status, actor_id=user.id))
    db.commit()
    return data(get(db, Project, id))


@app.get("/api/projects/{id}/events")
def project_events(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    own(get(db, Project, id), user)
    return [
        data(e)
        for e in db.scalars(
            select(ProjectEvent).where(ProjectEvent.project_id == id).order_by(ProjectEvent.id)
        )
    ]


@app.get("/api/orders")
def orders(db: Session = Depends(get_db), user=Depends(current_user)):
    query = select(Order).order_by(Order.id.desc())
    if user.role != "admin":
        query = query.where(Order.customer_id == user.id)
    return [data(o) for o in db.scalars(query)]


@app.post("/api/orders", status_code=201)
def create_order(body: OrderInput, db: Session = Depends(get_db), user=Depends(current_user)):
    return data(checkout(db, body, user))


@app.post("/api/orders/{id}/cancel")
def cancel_order(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = locked(db, Order, id)
    before = business.snapshot(row)
    own(row, user)
    result = db.execute(
        update(Order).where(Order.id == id, Order.status == "Confirmado").values(status="Cancelado")
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Este pedido já foi cancelado.")
    account = db.scalar(select(Ledger).where(Ledger.order_id == id))
    if account:
        if account.status == "Pago":
            db.rollback()
            raise HTTPException(
                409,
                "Pedido pago exige processo de reembolso. Não pode ser cancelado automaticamente.",
            )
        before_account = business.snapshot(account)
        account.status = "Cancelado"
        business.audit(db, user, "Financeiro", account, before_account, "Cancelar")
    for item in sorted(row.items, key=lambda i: i["product_id"]):
        business.change_stock(
            db,
            item["product_id"],
            item["quantity"],
            f"Cancelamento #{id}",
            user,
            origin=f"Cliente #{row.customer_id}",
            destination="Estoque",
            reference=f"Pedido #{id}",
        )
    business.audit(db, user, "Pedido", row, before, "Cancelar")
    db.commit()
    return data(row)


def image_target(db, entity, id, user, writing=False):
    if entity == "users":
        if id != user.id and (writing or user.role != "admin"):
            raise HTTPException(404, "Perfil não encontrado.")
        return get(db, User, id)
    cls = {"products": Product, "species": Species, "projects": Project, "quotes": Quote}.get(
        entity
    )
    if cls is None:
        raise HTTPException(422, "Tipo de imagem inválido.")
    row = locked(db, cls, id) if entity == "quotes" and writing else get(db, cls, id)
    if entity in ("projects", "quotes"):
        own(row, user)
        if (
            writing
            and entity == "quotes"
            and user.role != "admin"
            and row.status not in {"Solicitado", "Em análise"}
        ):
            raise HTTPException(
                409, "As fotos desta solicitação já foram enviadas para proposta ou encerradas."
            )
        if writing and entity == "projects" and user.role != "admin":
            raise HTTPException(403, "Somente o administrador pode editar fotos do projeto.")
    elif writing and user.role != "admin":
        raise HTTPException(403, "Acesso exclusivo do administrador.")
    return row


@app.get("/api/images/{entity}/{id:int}")
def list_images(entity: str, id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    target = image_target(db, entity, id, user)
    query = select(Image).where(Image.entity == entity, Image.entity_id == id)
    if entity == "projects" and target.quote_id:
        query = select(Image).where(
            ((Image.entity == entity) & (Image.entity_id == id))
            | ((Image.entity == "quotes") & (Image.entity_id == target.quote_id))
        )
    return [
        {**data(i), "url": f"/api/images/{i.id}/content"}
        for i in db.scalars(query.order_by(Image.id))
    ]


@app.post("/api/images/{entity}/{id:int}", status_code=201)
async def upload_image(
    entity: str,
    id: int,
    file: UploadFile = File(),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    target = image_target(db, entity, id, user, True)
    content = await file.read(5 * 1024 * 1024 + 1)
    await file.close()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "A imagem deve ter até 5 MB.")
    try:
        image = PILImage.open(io.BytesIO(content))
        if image.format not in ("JPEG", "PNG", "WEBP") or image.width * image.height > 16000000:
            raise ValueError()
        image.load()
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((1920, 1920))
    except (UnidentifiedImageError, ValueError, OSError, PILImage.DecompressionBombError):
        raise HTTPException(422, "Envie uma imagem JPG, PNG ou WebP válida (até 16 megapixels).")
    filename = f"{uuid.uuid4().hex}.jpg"
    image.save(UPLOADS / filename, quality=85)
    record = Image(owner_id=user.id, entity=entity, entity_id=id, filename=filename)
    db.add(record)
    db.flush()
    if entity in ("products", "species"):
        target.image_url = f"/api/images/{record.id}/content"
    elif entity == "users":
        previous = list(
            db.scalars(
                select(Image).where(
                    Image.entity == "users", Image.entity_id == id, Image.id != record.id
                )
            )
        )
        target.avatar_url = f"/api/images/{record.id}/content"
        for old in previous:
            db.delete(old)
    try:
        db.commit()
    except Exception:
        db.rollback()
        (UPLOADS / filename).unlink(missing_ok=True)
        raise
    if entity == "users":
        for old in previous:
            (UPLOADS / old.filename).unlink(missing_ok=True)
    return {**data(record), "url": f"/api/images/{record.id}/content"}


@app.get("/api/images/{id:int}/content")
def image_content(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = get(db, Image, id)
    image_target(db, row.entity, row.entity_id, user)
    if not (UPLOADS / row.filename).is_file():
        raise HTTPException(404, "Arquivo da imagem não encontrado.")
    return FileResponse(
        UPLOADS / row.filename,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=300"},
    )


@app.delete("/api/images/{id:int}", status_code=204)
def delete_image(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = get(db, Image, id)
    target = image_target(db, row.entity, row.entity_id, user, True)
    if row.entity in ("products", "species") and target.image_url == f"/api/images/{id}/content":
        target.image_url = ""
    elif row.entity == "users" and target.avatar_url == f"/api/images/{id}/content":
        target.avatar_url = ""
    path = UPLOADS / row.filename
    db.delete(row)
    db.commit()
    path.unlink(missing_ok=True)
    return Response(status_code=204)


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), user=Depends(admin)):
    sales = [o for o in rows(db, Order) if o.status != "Cancelado"]
    projects = rows(db, Project)
    total = sum(o.total_cents for o in sales)
    popular, customers_count, plant_count, months = {}, {}, {}, {}
    for o in sales:
        customers_count[o.customer_id] = customers_count.get(o.customer_id, 0) + 1
        month = o.created_at[:7]
        months[month] = months.get(month, 0) + o.total_cents
        for i in o.items:
            popular[i["name"]] = popular.get(i["name"], 0) + i["quantity"]
    for p in projects:
        for plant in p.plants:
            s = get(db, Species, plant["species_id"])
            plant_count[s.name] = plant_count.get(s.name, 0) + plant["quantity"]
    return {
        "revenue_cents": total,
        "orders_count": len(sales),
        "average_ticket_cents": round(total / len(sales)) if sales else 0,
        "recurring_customers": sum(n > 1 for n in customers_count.values()),
        "active_projects": sum(
            p.status in ("Aprovado", "Planejamento", "Execução", "Manutenção") for p in projects
        ),
        "quotes_pending": sum(q.status == "Solicitado" for q in rows(db, Quote)),
        "services_count": sum(p.quote_id is not None for p in projects),
        "project_budget_cents": sum(p.budget_cents for p in projects if p.status != "Orçamento"),
        "low_stock": [data(p) for p in rows(db, Product) if p.active and p.stock <= p.low_stock],
        "popular_products": sorted(popular.items(), key=lambda x: -x[1])[:5],
        "popular_plants": sorted(plant_count.items(), key=lambda x: -x[1])[:5],
        "monthly_sales": [{"month": k, "total_cents": v} for k, v in sorted(months.items())[-6:]],
    }


from .operations import router

app.include_router(router, prefix="/api")
from .learning import router as learning_router

app.include_router(learning_router, prefix="/api")

from .business_routes import router as business_router  # noqa: E402

app.include_router(business_router, prefix="/api")
from .landscaping import router as landscaping_router  # noqa: E402

app.include_router(landscaping_router, prefix="/api")
from .assistant import router as assistant_router

app.include_router(assistant_router, prefix="/api")
from .assistant_uploads import router as assistant_upload_router

app.include_router(assistant_upload_router, prefix="/api")
