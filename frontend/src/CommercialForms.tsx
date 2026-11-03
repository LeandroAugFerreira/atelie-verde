import { useEffect, useState, type FormEvent } from "react";
import { write } from "./api";
import { SaveButton } from "./components";
import { useGreen } from "./context";
import { categories } from "./Forms";
import {
  money,
  type Product,
  type Project,
  type Species,
  type Supplier,
} from "./types";

type Item = Record<string, unknown>;
type Field = {
  key: string;
  label: string;
  type?: string;
  options?: string[];
  required?: boolean;
  max?: number;
};
const status: Field = {
  key: "active",
  label: "Status",
  options: ["Ativo", "Inativo"],
};
const contactFields: Field[] = [
  { key: "contact_name", label: "Pessoa de contato", max: 120 },
  { key: "phone", label: "Telefone", max: 30 },
  { key: "email", label: "E-mail", type: "email", max: 254 },
  { key: "postal_code", label: "CEP", max: 9 },
  { key: "address", label: "Endereço e número", max: 500 },
  { key: "district", label: "Bairro", max: 100 },
  { key: "city", label: "Cidade", max: 100 },
  { key: "state", label: "UF", max: 2 },
  status,
  { key: "notes", label: "Observações", type: "textarea", max: 3000 },
];

export function CommercialPartyForm({
  kind,
  item,
  onSaved,
}: {
  kind: "customers" | "suppliers";
  item?: Item;
  onSaved: () => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const fields: Field[] =
    kind === "suppliers"
      ? [
          {
            key: "name",
            label: "Razão social / nome do fornecedor",
            required: true,
            max: 180,
          },
          { key: "trade_name", label: "Nome fantasia", max: 150 },
          { key: "document", label: "CNPJ", max: 18 },
          {
            key: "category",
            label: "Categoria",
            options: [...categories, "Outros"],
          },
          {
            key: "delivery_days",
            label: "Prazo de entrega (dias)",
            type: "number",
          },
          ...contactFields.filter((f) => f.key !== "district"),
        ]
      : [
          {
            key: "name",
            label: "Nome completo / razão social",
            required: true,
            max: 100,
          },
          {
            key: "customer_type",
            label: "Tipo de cliente",
            options: ["Pessoa física", "Pessoa jurídica"],
          },
          { key: "document", label: "CPF / CNPJ", max: 18 },
          ...(!item
            ? [
                {
                  key: "password",
                  label: "Senha inicial (opcional, mínimo 10 caracteres)",
                  type: "password",
                  max: 128,
                },
              ]
            : []),
          ...contactFields.map((f) =>
            f.key === "email" ? { ...f, required: true } : f,
          ),
        ];
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    const body = {
      ...values,
      active: values.active === "Ativo",
      document: values.document || null,
      delivery_days: undefined as number | undefined,
      password: undefined as string | undefined,
    };
    if (kind === "suppliers") body.delivery_days = Number(values.delivery_days);
    if (kind === "customers" && values.password)
      body.password = String(values.password);
    try {
      await write(
        `/${kind}${item ? "/" + item.id : ""}`,
        body,
        item ? "PUT" : "POST",
      );
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="form" onSubmit={submit}>
      <p className="form-hint">
        {item
          ? `Código: ${item.code || item.customer_code || "—"}`
          : "Código gerado automaticamente ao salvar."}
        {kind === "customers" &&
          !item &&
          " Preencha uma senha somente para habilitar o acesso do cliente ao portal."}
      </p>
      <div className="form-grid">
        {fields.map((f) => (
          <label key={f.key} className={f.type === "textarea" ? "full" : ""}>
            {f.label}
            {f.options ? (
              <select
                name={f.key}
                defaultValue={
                  f.key === "active"
                    ? item?.active === false
                      ? "Inativo"
                      : "Ativo"
                    : String(item?.[f.key] ?? f.options[0])
                }
              >
                {f.options.map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            ) : f.type === "textarea" ? (
              <textarea
                name={f.key}
                defaultValue={String(item?.[f.key] ?? "")}
                maxLength={f.max}
                rows={3}
              />
            ) : (
              <input
                name={f.key}
                type={f.type || "text"}
                defaultValue={String(
                  item?.[f.key] ?? (f.type === "number" ? 0 : ""),
                )}
                required={f.required}
                minLength={f.type === "password" ? 10 : undefined}
                maxLength={f.max}
                min={f.type === "number" ? 0 : undefined}
                max={f.type === "number" ? 365 : undefined}
              />
            )}
          </label>
        ))}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="form-footer">
        <span>Cadastros duplicados serão bloqueados.</span>
        <SaveButton busy={busy} />
      </div>
    </form>
  );
}

type Price = {
  cost_cents: number;
  markup_cents: number;
  tax_cents: number;
  taxes: Record<string, number>;
  effective_percent: number;
  suggested_price_cents: number;
  formula: string;
};
export function CommercialProductForm({
  item,
  species,
  suppliers,
  onSaved,
}: {
  item?: Product;
  species: Species[];
  suppliers: Supplier[];
  onSaved: () => Promise<void>;
}) {
  const [mode, setMode] = useState(item?.pricing_mode || "Manual"),
    [regime, setRegime] = useState(item?.tax_regime || "Carga efetiva");
  const [cost, setCost] = useState(String((item?.cost_cents || 0) / 100)),
    [margin, setMargin] = useState(String(item?.markup_percent || 0));
  const [rates, setRates] = useState<Record<string, number>>(
      item?.tax_rates || {},
    ),
    [preview, setPreview] = useState<Price | null>(null);
  const [priceError, setPriceError] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const keys =
    regime === "Simples Nacional"
      ? ["simples"]
      : regime === "Detalhado"
        ? ["icms", "pis", "cofins", "ipi", "other"]
        : ["effective"];
  const labels: Record<string, string> = {
    effective: "Carga tributária efetiva (%)",
    simples: "Simples — alíquota efetiva (%)",
    icms: "ICMS (%)",
    pis: "PIS (%)",
    cofins: "COFINS (%)",
    ipi: "IPI por fora (%)",
    other: "Outros tributos por dentro (%)",
  };
  useEffect(() => {
    let active = true;
    setPreview(null);
    setPriceError("");
    const timer = setTimeout(() => {
      write<Price>("/admin/pricing/preview", {
        cost_cents: Math.round(Number(cost) * 100),
        markup_percent: Number(margin),
        tax_regime: regime,
        tax_rates: rates,
      })
        .then((p) => {
          if (active) setPreview(p);
        })
        .catch((e) => {
          if (active) setPriceError(e.message);
        });
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [cost, margin, regime, rates]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const f = Object.fromEntries(new FormData(event.currentTarget));
    const body = {
      ...f,
      stock: item?.stock ?? Number(f.stock),
      low_stock: Number(f.low_stock),
      price_cents:
        mode === "Manual" ? Math.round(Number(f.price_cents) * 100) : null,
      cost_cents: Math.round(Number(cost) * 100),
      markup_percent: Number(margin),
      pricing_mode: mode,
      tax_regime: regime,
      tax_rates: rates,
      active: f.active === "true",
      species_id: f.species_id ? Number(f.species_id) : null,
      supplier_id: f.supplier_id ? Number(f.supplier_id) : null,
      barcode: f.barcode || null,
    };
    try {
      await write(
        `/products${item ? "/" + item.id : ""}`,
        body,
        item ? "PUT" : "POST",
      );
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="form" onSubmit={submit}>
      <div className="form-grid">
        <label>
          Nome do produto
          <input
            name="name"
            defaultValue={item?.name}
            required
            minLength={2}
            maxLength={100}
          />
        </label>
        <label>
          Categoria
          <select name="category" defaultValue={item?.category}>
            {categories.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          SKU / código do produto
          <input
            name="sku"
            defaultValue={item?.sku}
            maxLength={100}
            placeholder="Automático se deixar vazio"
          />
        </label>
        <label>
          Fornecedor
          <select name="supplier_id" defaultValue={item?.supplier_id || ""}>
            <option value="">Sem fornecedor vinculado</option>
            {suppliers
              .filter((s) => s.active || s.id === item?.supplier_id)
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} · {s.name}
                  {!s.active ? " (inativo)" : ""}
                </option>
              ))}
          </select>
        </label>
        <label>
          Marca / produtor
          <input name="brand" defaultValue={item?.brand} maxLength={100} />
        </label>
        <label>
          Variação / embalagem
          <input name="variant" defaultValue={item?.variant} maxLength={180} />
        </label>
        <label>
          Código de barras
          <input
            name="barcode"
            defaultValue={item?.barcode || ""}
            maxLength={100}
          />
        </label>
        <label>
          Unidade
          <select name="unit" defaultValue={item?.unit || "un"}>
            {["un", "kg", "L", "m", "m²", "pacote"].map((u) => (
              <option key={u}>{u}</option>
            ))}
          </select>
        </label>
        <label>
          Formação do preço
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option>Manual</option>
            <option>Custo + margem</option>
          </select>
        </label>
        <label>
          Preço (R$)
          <input
            name="price_cents"
            key={mode}
            type="number"
            defaultValue={
              mode === "Manual" ? (item?.price_cents || 0) / 100 : undefined
            }
            value={
              mode !== "Manual"
                ? preview
                  ? preview.suggested_price_cents / 100
                  : ""
                : undefined
            }
            readOnly={mode !== "Manual"}
            required={mode === "Manual"}
            min="0.01"
            step="0.01"
          />
        </label>
      </div>
      <details
        className="commercial-details"
        open={mode === "Custo + margem" ? true : undefined}
      >
        <summary>Custos, margem e impostos</summary>
        <div className="form-grid">
          <label>
            Custo unitário (R$)
            <input
              type="number"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              min={mode === "Custo + margem" ? "0.01" : "0"}
              step="0.01"
              required={mode === "Custo + margem"}
            />
          </label>
          <label>
            Margem sobre o custo (%)
            <input
              type="number"
              value={margin}
              onChange={(e) => setMargin(e.target.value)}
              min="0"
              max="500"
              step="0.01"
            />
          </label>
          <label>
            Regime de precificação
            <select
              value={regime}
              onChange={(e) => {
                setRegime(e.target.value);
                setRates({});
              }}
            >
              {["Carga efetiva", "Simples Nacional", "Detalhado"].map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </label>
          <label>
            NCM (opcional)
            <input
              name="ncm"
              defaultValue={item?.ncm || ""}
              pattern="[0-9]{8}"
              maxLength={8}
            />
          </label>
          {keys.map((k) => (
            <label key={k}>
              {labels[k]}
              <input
                type="number"
                min="0"
                max="100"
                step="0.001"
                value={rates[k] || 0}
                onChange={(e) =>
                  setRates({ ...rates, [k]: Number(e.target.value) })
                }
              />
            </label>
          ))}
        </div>
        {preview && (
          <div className="price-composition" aria-label="Composição do preço">
            <span>
              Custo <b>{money(preview.cost_cents)}</b>
            </span>
            <span>
              Margem <b>{money(preview.markup_cents)}</b>
            </span>
            <span>
              Tributos estimados <b>{money(preview.tax_cents)}</b>
            </span>
            <span>
              Preço sugerido <b>{money(preview.suggested_price_cents)}</b>
            </span>
          </div>
        )}
        {priceError && (
          <p className="error" role="alert">
            {priceError}
          </p>
        )}
        {preview && (
          <div className="tax-breakdown">
            {Object.entries(preview.taxes)
              .filter(([, v]) => v > 0)
              .map(([key, value]) => (
                <span key={key}>
                  {labels[key].replace(" (%)", "")}: <b>{money(value)}</b>
                </span>
              ))}
          </div>
        )}
        <p className="form-hint">
          Margem aplicada sobre o custo. Tributos por dentro e IPI por fora. No
          modo detalhado, PIS/COFINS usam a base sem ICMS. Informe as alíquotas
          aplicáveis à operação; esta é uma estimativa para formar o preço, sem
          apuração ou emissão fiscal.
        </p>
      </details>
      <div className="form-grid">
        {!item && (
          <label>
            Estoque inicial
            <input
              name="stock"
              type="number"
              defaultValue="0"
              min="0"
              max="1000000"
              step="1"
            />
          </label>
        )}
        <label>
          Alerta de estoque baixo
          <input
            name="low_stock"
            type="number"
            defaultValue={item?.low_stock ?? 5}
            min="0"
            max="1000000"
            step="1"
          />
        </label>
        <label>
          Localização no estoque
          <input
            name="location"
            defaultValue={item?.location}
            maxLength={100}
          />
        </label>
        <label>
          Espécie vinculada
          <select name="species_id" defaultValue={item?.species_id || ""}>
            <option value="">Sem vínculo</option>
            {species.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Disponibilidade
          <select name="active" defaultValue={String(item?.active ?? true)}>
            <option value="true">Ativo</option>
            <option value="false">Inativo</option>
          </select>
        </label>
        <label className="full">
          Descrição
          <textarea
            name="description"
            defaultValue={item?.description}
            rows={3}
            maxLength={2000}
          />
        </label>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="form-footer">
        <span>O servidor valida e recalcula o preço.</span>
        <SaveButton busy={busy} />
      </div>
    </form>
  );
}

export function CommercialStockForm({
  item,
  project,
}: {
  item?: Product;
  project?: Project;
}) {
  const { data, act, busy } = useGreen();
  const [productId, setProductId] = useState(item?.id || data.products[0]?.id),
    [quantity, setQuantity] = useState(project ? -1 : 0),
    [projectId, setProjectId] = useState(project ? String(project.id) : ""),
    [payable, setPayable] = useState(false),
    [error, setError] = useState("");
  const [key] = useState(() => crypto.randomUUID());
  const product = data.products.find((p) => p.id === productId);
  return (
    <form
      className="form"
      onSubmit={async (e) => {
        e.preventDefault();
        setError("");
        const f = Object.fromEntries(new FormData(e.currentTarget));
        const ok = await act(`/products/${productId}/stock`, {
          quantity,
          reason: f.reason,
          origin: f.origin,
          destination: f.destination,
          reference: f.reference,
          supplier_id:
            quantity > 0 && f.supplier_id ? Number(f.supplier_id) : null,
          unit_cost_cents:
            f.unit_cost_cents !== undefined && f.unit_cost_cents !== ""
              ? Math.round(Number(f.unit_cost_cents) * 100)
              : null,
          record_payable: quantity > 0 && payable,
          due_date: quantity > 0 && payable ? f.due_date : null,
          request_key: key,
          project_id: quantity < 0 && projectId ? Number(projectId) : null,
        });
        if (!ok)
          setError(
            "Movimentação não registrada. Confira os dados e o saldo disponível.",
          );
      }}
    >
      <label>
        Produto
        <select
          value={productId}
          onChange={(e) => setProductId(Number(e.target.value))}
        >
          {data.products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.sku} · {p.name} · saldo {p.stock}
            </option>
          ))}
        </select>
      </label>
      <div className="form-grid">
        <label>
          Quantidade (entrada positiva / saída negativa)
          <input
            type="number"
            step="1"
            required
            min="-1000000"
            max={project ? "-1" : "1000000"}
            value={quantity || ""}
            onChange={(e) => {
              setQuantity(Number(e.target.value));
              if (Number(e.target.value) < 0) setPayable(false);
            }}
          />
        </label>
        <label>
          Motivo
          <input name="reason" required minLength={3} maxLength={200} />
        </label>
        <label>
          Origem
          <input
            name="origin"
            maxLength={150}
            placeholder={quantity > 0 ? "Fornecedor / origem" : "Estoque"}
          />
        </label>
        <label>
          Destino
          <input
            name="destination"
            maxLength={150}
            placeholder={product?.location || "Estoque"}
          />
        </label>
        <label>
          Documento / referência
          <input
            name="reference"
            maxLength={100}
            placeholder="Nota, pedido ou ajuste"
          />
        </label>
        {quantity < 0 && (
          <>
            <label>
              Projeto (consumo)
              <select
                aria-label="Projeto (consumo)"
                value={projectId}
                disabled={Boolean(project)}
                onChange={(e) => setProjectId(e.target.value)}
              >
                <option value="">Saída sem vínculo com projeto</option>
                {data.projects
                  .filter((p) => ["Execução", "Manutenção"].includes(p.status))
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
              </select>
            </label>
            {projectId && (
              <label>
                Custo unitário do consumo (R$)
                <input
                  name="unit_cost_cents"
                  key={productId}
                  type="number"
                  min="0"
                  max="1000000"
                  step="0.01"
                  defaultValue={
                    product?.cost_cents ? product.cost_cents / 100 : ""
                  }
                  placeholder="Sem custo cadastrado"
                />
              </label>
            )}
          </>
        )}
        {quantity > 0 && (
          <>
            <label>
              Fornecedor
              <select
                key={productId}
                name="supplier_id"
                defaultValue={product?.supplier_id || ""}
                required={payable}
              >
                <option value="">Sem fornecedor vinculado</option>
                {data.suppliers
                  .filter((s) => s.active)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.code} · {s.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Custo unitário da entrada (R$)
              <input
                name="unit_cost_cents"
                type="number"
                step="0.01"
                min={payable ? "0.01" : "0"}
                required={payable}
              />
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={payable}
                onChange={(e) => setPayable(e.target.checked)}
              />
              Gerar conta a pagar desta entrada
            </label>
            {payable && (
              <label>
                Vencimento
                <input type="date" name="due_date" required />
              </label>
            )}
          </>
        )}
      </div>
      <p className="form-hint">
        Saldo previsto: {(product?.stock || 0) + quantity}{" "}
        {product?.unit || "un"}. Saídas sem saldo serão bloqueadas; a compra e a
        conta a pagar serão salvas juntas.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <SaveButton busy={busy} />
    </form>
  );
}
