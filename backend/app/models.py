from datetime import datetime, timezone

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def now():
    return datetime.now(timezone.utc).isoformat()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="customer")
    phone: Mapped[str] = mapped_column(default="")
    address: Mapped[str] = mapped_column(default="")
    city: Mapped[str] = mapped_column(default="")
    active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str] = mapped_column(default="")
    created_at: Mapped[str] = mapped_column(default=now)
    avatar_url: Mapped[str] = mapped_column(default="", server_default="")
    customer_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    customer_type: Mapped[str] = mapped_column(
        default="Pessoa física", server_default="Pessoa física"
    )
    document: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)
    postal_code: Mapped[str] = mapped_column(default="", server_default="")
    district: Mapped[str] = mapped_column(default="", server_default="")
    state: Mapped[str] = mapped_column(default="", server_default="")
    contact_name: Mapped[str] = mapped_column(default="", server_default="")
    portal_enabled: Mapped[bool] = mapped_column(default=True, server_default="1")


class Species(Base):
    __tablename__ = "species"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    scientific_name: Mapped[str]
    light: Mapped[str]
    watering: Mapped[str]
    size: Mapped[str]
    environment: Mapped[str]
    difficulty: Mapped[str]
    use: Mapped[str]
    description: Mapped[str]
    image_url: Mapped[str] = mapped_column(default="")
    demo_asset: Mapped[str] = mapped_column(default="")
    watering_frequency: Mapped[str] = mapped_column(default="")
    height: Mapped[str] = mapped_column(default="")
    care: Mapped[str] = mapped_column(default="")
    substrate: Mapped[str] = mapped_column(default="", server_default="")
    propagation: Mapped[str] = mapped_column(default="", server_default="")
    precautions: Mapped[str] = mapped_column(default="", server_default="")
    family: Mapped[str] = mapped_column(default="", server_default="")
    origin: Mapped[str] = mapped_column(default="", server_default="")
    photos: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    sources: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
        CheckConstraint("price_cents > 0", name="ck_products_price_positive"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    category: Mapped[str]
    description: Mapped[str]
    price_cents: Mapped[int]
    stock: Mapped[int] = mapped_column(default=0)
    low_stock: Mapped[int] = mapped_column(default=5)
    species_id: Mapped[int | None] = mapped_column(ForeignKey("species.id"), nullable=True)
    image_url: Mapped[str] = mapped_column(default="")
    active: Mapped[bool] = mapped_column(default=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True)
    location: Mapped[str] = mapped_column(default="")
    demo_asset: Mapped[str] = mapped_column(default="")
    brand: Mapped[str] = mapped_column(default="", server_default="")
    variant: Mapped[str] = mapped_column(default="", server_default="")
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    unit: Mapped[str] = mapped_column(default="un", server_default="un")
    cost_cents: Mapped[int] = mapped_column(default=0, server_default="0")
    pricing_mode: Mapped[str] = mapped_column(default="Manual", server_default="Manual")
    markup_percent: Mapped[float] = mapped_column(default=0, server_default="0")
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    identity_key: Mapped[str | None] = mapped_column(String(500), unique=True, nullable=True)
    tax_regime: Mapped[str] = mapped_column(default="Carga efetiva", server_default="Carga efetiva")
    tax_rates: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    ncm: Mapped[str] = mapped_column(default="", server_default="")


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str]
    price_cents: Mapped[int]
    unit: Mapped[str]
    category: Mapped[str] = mapped_column(default="Manutenção")
    duration: Mapped[str] = mapped_column(default="2 horas")
    responsible: Mapped[str] = mapped_column(default="Equipe Ateliê Verde")
    active: Mapped[bool] = mapped_column(default=True)
    demo_asset: Mapped[str] = mapped_column(default="")
    delivery_mode: Mapped[str] = mapped_column(default="Presencial", server_default="Presencial")


class Quote(Base):
    __tablename__ = "quotes"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    area: Mapped[float]
    address: Mapped[str]
    description: Mapped[str]
    status: Mapped[str] = mapped_column(default="Solicitado")
    amount_cents: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[str] = mapped_column(default=now)
    plants: Mapped[list] = mapped_column(JSON, default=list)
    materials: Mapped[list] = mapped_column(JSON, default=list)
    brief: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    brief_revision: Mapped[int] = mapped_column(default=0, server_default="0")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    quote_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotes.id"), unique=True, nullable=True
    )
    address: Mapped[str]
    area: Mapped[float]
    status: Mapped[str] = mapped_column(default="Orçamento")
    budget_cents: Mapped[int]
    start_date: Mapped[str]
    end_date: Mapped[str]
    description: Mapped[str] = mapped_column(default="")
    brief: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    brief_revision: Mapped[int] = mapped_column(default=0, server_default="0")
    delivery_mode: Mapped[str] = mapped_column(default="Presencial", server_default="Presencial")
    reference_image_url: Mapped[str] = mapped_column(default="", server_default="")
    reference_image_note: Mapped[str] = mapped_column(default="", server_default="")
    plants: Mapped[list] = mapped_column(JSON, default=list)
    materials: Mapped[list] = mapped_column(JSON, default=list)
    services: Mapped[list] = mapped_column(JSON, default=list)
    tasks: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(default=now)


class ProjectEvent(Base):
    __tablename__ = "project_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str]
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(default=now)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("request_key", name="uq_orders_request_key"),
        Index("ix_orders_customer_id", "customer_id"),
    )
    request_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    total_cents: Mapped[int]
    items: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(default="Confirmado")
    created_at: Mapped[str] = mapped_column(default=now)


class StockMove(Base):
    __tablename__ = "stock_moves"
    __table_args__ = (
        Index("ix_stock_moves_product_id", "product_id"),
        Index("ix_stock_moves_project_id", "project_id"),
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", name="fk_stock_moves_project_id"), nullable=True
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    reason: Mapped[str]
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(default=now)
    balance_before: Mapped[int | None] = mapped_column(nullable=True)
    balance_after: Mapped[int | None] = mapped_column(nullable=True)
    origin: Mapped[str] = mapped_column(default="", server_default="")
    destination: Mapped[str] = mapped_column(default="", server_default="")
    reference: Mapped[str] = mapped_column(default="", server_default="")
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    unit_cost_cents: Mapped[int | None] = mapped_column(nullable=True)
    request_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")


class Image(Base):
    __tablename__ = "images"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    entity: Mapped[str]
    entity_id: Mapped[int]
    filename: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=now)


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str]
    date: Mapped[str]
    start_time: Mapped[str]
    end_time: Mapped[str]
    responsible: Mapped[str]
    status: Mapped[str] = mapped_column(default="Agendado")
    address: Mapped[str]
    amount_cents: Mapped[int] = mapped_column(default=0)


class Ledger(Base):
    __tablename__ = "ledger"
    __table_args__ = (CheckConstraint("amount_cents > 0", name="ck_ledger_amount_positive"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    direction: Mapped[str]
    source: Mapped[str]
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id"), unique=True, nullable=True
    )
    counterparty: Mapped[str]
    description: Mapped[str]
    due_date: Mapped[str]
    amount_cents: Mapped[int]
    status: Mapped[str] = mapped_column(default="Pendente")
    paid_date: Mapped[str] = mapped_column(default="")
    created_at: Mapped[str] = mapped_column(default=now)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    stock_move_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_moves.id"), unique=True, nullable=True
    )


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str]
    trade_name: Mapped[str] = mapped_column(default="")
    document: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)
    category: Mapped[str]
    contact_name: Mapped[str] = mapped_column(default="")
    email: Mapped[str] = mapped_column(default="")
    phone: Mapped[str] = mapped_column(default="")
    address: Mapped[str] = mapped_column(default="")
    city: Mapped[str] = mapped_column(default="")
    state: Mapped[str] = mapped_column(default="")
    postal_code: Mapped[str] = mapped_column(default="")
    delivery_days: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str] = mapped_column(default="")
    active: Mapped[bool] = mapped_column(default=True)
    identity_key: Mapped[str] = mapped_column(String(300), unique=True)
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)


class BusinessSequence(Base):
    __tablename__ = "business_sequences"
    prefix: Mapped[str] = mapped_column(String(20), primary_key=True)
    value: Mapped[int] = mapped_column(default=0)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    entity: Mapped[str]
    entity_id: Mapped[int]
    action: Mapped[str]
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(default=now)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("customer_id", "product_id"),
        CheckConstraint("rating >= 1 AND rating <= 5"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int]
    comment: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=now)


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (__import__("sqlalchemy").UniqueConstraint("customer_id", "product_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "(project_id IS NOT NULL AND quote_id IS NULL) OR (project_id IS NULL AND quote_id IS NOT NULL)",
            name="ck_documents_parent",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    quote_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotes.id", name="fk_documents_quote_id"), nullable=True
    )
    name: Mapped[str]
    filename: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=now)


class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(150), unique=True)
    title: Mapped[str]
    category: Mapped[str]
    summary: Mapped[str]
    minutes: Mapped[int]
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    sections: Mapped[list] = mapped_column(JSON, default=list)
    sources: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (__import__("sqlalchemy").UniqueConstraint("user_id", "article_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))
    completed_at: Mapped[str] = mapped_column(default=now)


class CatalogVersion(Base):
    __tablename__ = "catalog_versions"
    version: Mapped[str] = mapped_column(String(100), primary_key=True)
    applied_at: Mapped[str] = mapped_column(default=now)


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(default="Nova conversa")
    memory: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    pending_request: Mapped[str] = mapped_column(default="", server_default="")
    updated_at: Mapped[str] = mapped_column(default=now)
    created_at: Mapped[str] = mapped_column(default=now)


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("conversation_id", "request_id", "role"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_assistant_message_role"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[str]
    role: Mapped[str]
    text: Mapped[str]
    status: Mapped[str] = mapped_column(default="completed")
    mode: Mapped[str] = mapped_column(default="catalog")
    sources: Mapped[list] = mapped_column(JSON, default=list)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(default=now)


class AssistantPreference(Base):
    __tablename__ = "assistant_preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(default=True, server_default="1")
    motion: Mapped[bool] = mapped_column(default=True, server_default="1")
    typewriter: Mapped[bool] = mapped_column(default=True, server_default="1")
    voice: Mapped[bool] = mapped_column(default=False, server_default="0")


class AssistantConfiguration(Base):
    __tablename__ = "assistant_configuration"
    id: Mapped[int] = mapped_column(primary_key=True)
    enabled: Mapped[bool] = mapped_column(default=True, server_default="1")
    greeting: Mapped[str]
    suggestions: Mapped[list] = mapped_column(JSON, default=list)


class AssistantResearchCache(Base):
    __tablename__ = "assistant_research_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    expires_at: Mapped[float]


class AssistantAttachment(Base):
    __tablename__ = "assistant_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("assistant_conversations.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=now)
