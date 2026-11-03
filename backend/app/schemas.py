import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Login(BaseModel):
    email: str
    password: str


class Register(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10, max_length=128)
    phone: str = Field(default="", max_length=30)
    address: str = Field(default="", max_length=500)


class CustomerInput(BaseModel):
    model_config = {"str_strip_whitespace": True}
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(default="", max_length=30)
    address: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=3000)
    active: bool = True
    email: str | None = Field(
        default=None, min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    customer_type: Literal["Pessoa física", "Pessoa jurídica"] = "Pessoa física"
    document: str | None = Field(default=None, max_length=30)
    postal_code: str = Field(default="", max_length=12)
    district: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=2)
    contact_name: str = Field(default="", max_length=120)

    @model_validator(mode="after")
    def normalize_details(self):
        supplied = set(self.model_fields_set)
        self.document = normalize_document(
            self.document,
            (11 if self.customer_type == "Pessoa física" else 14)
            if "customer_type" in self.model_fields_set or isinstance(self, CustomerCreate)
            else len(re.sub(r"\D", "", self.document or "")),
        )
        self.postal_code = normalize_postal(self.postal_code)
        self.state = normalize_state(self.state)
        if self.email:
            self.email = self.email.lower()
        object.__setattr__(self, "__pydantic_fields_set__", supplied)
        return self


def normalize_document(value, length):
    if not value or not value.strip():
        return None
    if re.search(r"[^\d./\-\s]", value):
        raise ValueError("Documento deve conter apenas números e pontuação de CPF/CNPJ.")
    digits = re.sub(r"\D", "", value)
    if length not in {11, 14} or len(digits) != length or len(set(digits)) == 1:
        raise ValueError(f"Informe um documento com {length} dígitos.")
    return digits


def normalize_postal(value):
    if value and not re.fullmatch(r"\d{5}-?\d{3}", value):
        raise ValueError("CEP deve conter 8 dígitos.")
    return value.replace("-", "")


def normalize_state(value):
    value = value.upper()
    if (
        value
        and value
        not in "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
    ):
        raise ValueError("Informe uma UF válida.")
    return value


class CustomerCreate(CustomerInput):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str | None = Field(default=None, min_length=10, max_length=128)


class SupplierInput(BaseModel):
    model_config = {"str_strip_whitespace": True}
    name: str = Field(min_length=2, max_length=180)
    trade_name: str = Field(default="", max_length=150)
    document: str | None = Field(default=None, max_length=30)
    category: Literal[
        "Plantas", "Vasos", "Substratos", "Fertilizantes", "Ferramentas", "Acessórios", "Outros"
    ]
    contact_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=254)
    phone: str = Field(default="", max_length=30)
    address: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=2)
    postal_code: str = Field(default="", max_length=12)
    delivery_days: int = Field(default=0, ge=0, le=365)
    notes: str = Field(default="", max_length=3000)
    active: bool = True

    @model_validator(mode="after")
    def normalize_details(self):
        self.document = normalize_document(self.document, 14)
        self.postal_code = normalize_postal(self.postal_code)
        self.state = normalize_state(self.state)
        self.email = self.email.lower()
        if self.email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.email):
            raise ValueError("Informe um e-mail válido.")
        return self


class ActiveInput(BaseModel):
    active: bool


class ProfileInput(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str = Field(default="", max_length=30)
    address: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=100)


class SpeciesInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    scientific_name: str = Field(min_length=2, max_length=150)
    light: Literal["Sol pleno", "Meia-sombra", "Sombra"]
    watering: Literal["Baixa", "Moderada", "Frequente"]
    size: Literal["Pequeno", "Médio", "Grande"]
    environment: Literal["Interno", "Externo", "Ambos"]
    difficulty: Literal["Baixa", "Média", "Alta"]
    use: str = Field(max_length=200)
    description: str = Field(default="", max_length=2000)
    watering_frequency: str = Field(default="", max_length=100)
    height: str = Field(default="", max_length=100)
    care: str = Field(default="", max_length=3000)
    substrate: str = Field(default="", max_length=1000)
    propagation: str = Field(default="", max_length=1000)
    precautions: str = Field(default="", max_length=1000)
    family: str = Field(default="", max_length=150)
    origin: str = Field(default="", max_length=300)


class PricingInput(BaseModel):
    cost_cents: int = Field(default=0, ge=0, le=100000000)
    markup_percent: Decimal = Field(default=Decimal(0), ge=0, le=500)
    tax_regime: Literal["Carga efetiva", "Simples Nacional", "Detalhado"] = "Carga efetiva"
    tax_rates: dict[str, Decimal] = Field(default_factory=dict)
    ncm: str = Field(default="", pattern=r"^(\d{8})?$")

    @model_validator(mode="after")
    def taxes(self):
        allowed = {
            "Carga efetiva": {"effective"},
            "Simples Nacional": {"simples"},
            "Detalhado": {"icms", "pis", "cofins", "ipi", "other"},
        }[self.tax_regime]
        if set(self.tax_rates) - allowed:
            raise ValueError("As alíquotas devem corresponder ao regime selecionado.")
        if any(not rate.is_finite() or rate < 0 or rate > 100 for rate in self.tax_rates.values()):
            raise ValueError("Alíquotas devem estar entre 0 e 100%.")
        rates = self.tax_rates
        effective = rates.get(
            "effective",
            rates.get(
                "simples",
                rates.get("icms", 0)
                + (rates.get("pis", 0) + rates.get("cofins", 0)) * (1 - rates.get("icms", 0) / 100)
                + rates.get("other", 0),
            ),
        )
        if effective >= 100:
            raise ValueError("A carga tributária por dentro deve ser inferior a 100%.")
        return self


class ProductInput(PricingInput):
    model_config = {"str_strip_whitespace": True}
    name: str = Field(min_length=2, max_length=100)
    category: Literal[
        "Plantas", "Vasos", "Substratos", "Fertilizantes", "Ferramentas", "Acessórios"
    ]
    description: str = Field(default="", max_length=2000)
    price_cents: int | None = Field(default=None, gt=0, le=100000000)
    stock: int = Field(default=0, ge=0, le=1000000)
    low_stock: int = Field(default=5, ge=0, le=1000000)
    species_id: int | None = None
    active: bool = True
    sku: str = Field(default="", max_length=100)
    location: str = Field(default="", max_length=100)
    brand: str = Field(default="", max_length=100)
    variant: str = Field(default="", max_length=180)
    barcode: str | None = Field(default=None, max_length=100)
    unit: Literal["un", "kg", "L", "m", "m²", "pacote"] = "un"
    cost_cents: int = Field(default=0, ge=0, le=100000000)
    pricing_mode: Literal["Manual", "Custo + margem"] = "Manual"
    markup_percent: Decimal = Field(default=Decimal(0), ge=0, le=500)
    supplier_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def normalize_details(self):
        self.sku = self.sku.upper()
        # Preserve omitted values when updating an existing product.
        supplied = set(self.model_fields_set)
        self.barcode = self.barcode.strip() or None if self.barcode else None
        object.__setattr__(self, "__pydantic_fields_set__", supplied)
        if self.pricing_mode == "Manual" and not self.price_cents:
            raise ValueError("Informe o preço de venda.")
        if self.pricing_mode == "Custo + margem" and self.cost_cents <= 0:
            raise ValueError("Informe o custo para calcular o preço.")
        if self.species_id and self.category != "Plantas":
            raise ValueError("Uma espécie deve estar vinculada à categoria Plantas.")
        return self


class ServiceInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=2000)
    price_cents: int = Field(gt=0, le=100000000)
    unit: Literal["m²", "visita", "projeto"]
    category: Literal["Manutenção", "Implantação", "Irrigação", "Consultoria", "Projeto"] = (
        "Manutenção"
    )
    duration: str = Field(default="2 horas", max_length=100)
    responsible: str = Field(default="Equipe Ateliê Verde", max_length=100)
    active: bool = True
    delivery_mode: Literal["Virtual", "Presencial"] = "Presencial"


class QuoteInput(BaseModel):
    service_id: int
    area: float = Field(gt=0, le=1000000)
    address: str = Field(min_length=5, max_length=500)
    description: str = Field(default="", max_length=3000)
    customer_id: int | None = None
    plants: list["PlantItem"] = Field(default_factory=list, max_length=200)
    materials: list["CostItem"] = Field(default_factory=list, max_length=200)
    brief: "LandscapeBrief | None" = None


class QuotePrice(BaseModel):
    amount_cents: int = Field(gt=0, le=100000000)
    plants: list["PlantItem"] | None = Field(default=None, max_length=200)
    materials: list["CostItem"] | None = Field(default=None, max_length=200)


class PlantItem(BaseModel):
    species_id: int
    quantity: int = Field(gt=0, le=10000)
    application: str = Field(default="", max_length=200)


class LayoutPlant(PlantItem):
    x: float = Field(ge=0, le=500, allow_inf_nan=False)
    y: float = Field(ge=0, le=500, allow_inf_nan=False)
    diameter: float = Field(default=1, gt=0, le=100, allow_inf_nan=False)


class LayoutZone(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    kind: Literal["Canteiro", "Caminho", "Deck", "Gramado", "Construção", "Água"] = "Canteiro"
    x: float = Field(ge=0, le=500, allow_inf_nan=False)
    y: float = Field(ge=0, le=500, allow_inf_nan=False)
    width: float = Field(gt=0, le=500, allow_inf_nan=False)
    length: float = Field(gt=0, le=500, allow_inf_nan=False)


class LandscapeBrief(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    width: float = Field(gt=0, le=500, allow_inf_nan=False)
    length: float = Field(gt=0, le=500, allow_inf_nan=False)
    north: int = Field(default=0, ge=0, le=359)
    light: Literal["Sol pleno", "Meia-sombra", "Sombra", "Misto"] = "Misto"
    soil: str = Field(default="Não avaliado", max_length=500)
    drainage: Literal["Boa", "Regular", "Ruim", "Não avaliada"] = "Não avaliada"
    maintenance: Literal["Baixa", "Média", "Alta"] = "Baixa"
    objective: str = Field(default="", max_length=1000)
    notes: str = Field(default="", max_length=3000)
    plantings: list[LayoutPlant] = Field(default_factory=list, max_length=200)
    zones: list[LayoutZone] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def coordinates(self):
        if any(p.x > self.width or p.y > self.length for p in self.plantings):
            raise ValueError("As plantas devem estar dentro dos limites do terreno.")
        if any(z.x + z.width > self.width or z.y + z.length > self.length for z in self.zones):
            raise ValueError("As áreas devem estar dentro dos limites do terreno.")
        return self


class BriefUpdate(BaseModel):
    brief: LandscapeBrief
    expected_revision: int = Field(default=0, ge=0)
    address: str | None = Field(default=None, min_length=5, max_length=500)


class CostItem(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    quantity: float = Field(gt=0, le=100000)
    unit_price_cents: int = Field(ge=0, le=100000000)


class TaskItem(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    date: date
    done: bool = False


class ProjectInput(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    customer_id: int
    address: str = Field(min_length=5, max_length=500)
    area: float = Field(gt=0, le=1000000)
    budget_cents: int = Field(ge=0, le=100000000)
    start_date: date
    end_date: date
    description: str = Field(default="", max_length=3000)
    plants: list[PlantItem] = Field(default_factory=list, max_length=200)
    materials: list[CostItem] = Field(default_factory=list, max_length=200)
    services: list[CostItem] = Field(default_factory=list, max_length=100)
    tasks: list[TaskItem] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def dates(self):
        if self.end_date < self.start_date:
            raise ValueError("A data final deve ser igual ou posterior à inicial.")
        if any(t.date < self.start_date or t.date > self.end_date for t in self.tasks):
            raise ValueError("As etapas devem estar dentro do período do projeto.")
        return self


class StatusInput(BaseModel):
    status: Literal["Orçamento", "Aprovado", "Planejamento", "Execução", "Finalizado", "Manutenção"]


class StockInput(BaseModel):
    model_config = {"str_strip_whitespace": True}
    quantity: int = Field(ge=-1000000, le=1000000)
    reason: str = Field(min_length=3, max_length=200)
    origin: str = Field(default="", max_length=150)
    destination: str = Field(default="", max_length=150)
    reference: str = Field(default="", max_length=100)
    supplier_id: int | None = Field(default=None, gt=0)
    unit_cost_cents: int | None = Field(default=None, ge=0, le=100000000)
    request_key: str | None = Field(default=None, min_length=10, max_length=64)
    record_payable: bool = False
    due_date: date | None = None
    project_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def receipt(self):
        if self.project_id and self.quantity >= 0:
            raise ValueError("Consumo em projeto deve ser uma saída de estoque.")
        if not self.quantity:
            raise ValueError("Informe uma quantidade diferente de zero.")
        if self.supplier_id and self.quantity < 0:
            raise ValueError("Fornecedor se aplica às entradas de estoque.")
        if self.record_payable and (
            self.quantity <= 0
            or not self.supplier_id
            or not self.unit_cost_cents
            or not self.due_date
        ):
            raise ValueError(
                "Para gerar conta a pagar, informe entrada, fornecedor, custo positivo e vencimento."
            )
        return self


class OrderItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=10000)


class OrderInput(BaseModel):
    items: list[OrderItem] = Field(min_length=1, max_length=100)
    request_key: str | None = Field(default=None, min_length=10, max_length=64)


class AppointmentInput(BaseModel):
    service_id: int
    customer_id: int
    title: str = Field(min_length=2, max_length=150)
    date: date
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    responsible: str = Field(min_length=2, max_length=100)
    status: Literal["Agendado", "Em execução", "Concluído", "Cancelado"] = "Agendado"
    address: str = Field(min_length=5, max_length=500)
    amount_cents: int = Field(default=0, ge=0, le=100000000)

    @model_validator(mode="after")
    def times(self):
        if self.end_time <= self.start_time:
            raise ValueError("O término deve ser posterior ao início.")
        return self


class LedgerInput(BaseModel):
    direction: Literal["Receita", "Despesa"]
    source: Literal["Loja", "Serviços", "Projetos", "Estoque", "Outros"]
    supplier_id: int | None = Field(default=None, gt=0)
    customer_id: int | None = None
    counterparty: str = Field(min_length=2, max_length=150)
    description: str = Field(min_length=2, max_length=500)
    due_date: date
    amount_cents: int = Field(gt=0, le=100000000)
    status: Literal["Pendente", "Pago"] = "Pendente"
    paid_date: date | None = None

    @model_validator(mode="after")
    def payment(self):
        if self.status == "Pago" and not self.paid_date:
            raise ValueError("Informe a data de pagamento.")
        if self.status == "Pendente":
            self.paid_date = None
        return self


class ReviewInput(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=1000)


class QuoteStatus(BaseModel):
    status: Literal["Em análise", "Rejeitado"]


class SettingsInput(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: str = Field(max_length=254)
    phone: str = Field(max_length=50)
    address: str = Field(max_length=500)
    low_stock_alert: bool = True
    quote_alert: bool = True


QuoteInput.model_rebuild()
QuotePrice.model_rebuild()
