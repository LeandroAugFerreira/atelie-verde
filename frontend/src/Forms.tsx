import { useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { write } from "./api";
import { SaveButton } from "./components";
import { useGreen } from "./context";
import {
  money,
  type User,
  type Species,
  type Project,
  type Service,
} from "./types";

type Field = {
  key: string;
  label: string;
  type?: string;
  options?: { value: string; label: string }[];
  default?: string;
  required?: boolean;
  min?: number;
  max?: number;
};
const opts = (values: string[]) =>
  values.map((value) => ({ value, label: value }));
export const categories = [
  "Plantas",
  "Vasos",
  "Substratos",
  "Fertilizantes",
  "Ferramentas",
  "Acessórios",
];
export function EntityForm({
  kind,
  item,
  species,
  onSaved,
}: {
  kind: string;
  item?: Record<string, unknown>;
  species: Species[];
  onSaved: () => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const fields: Field[] =
    kind === "products"
      ? [
          { key: "name", label: "Nome do produto", required: true, max: 100 },
          { key: "category", label: "Categoria", options: opts(categories) },
          {
            key: "sku",
            label: "SKU / código do produto",
            required: true,
            max: 100,
          },
          { key: "location", label: "Localização no estoque", max: 100 },
          {
            key: "price_cents",
            label: "Preço (R$)",
            type: "number",
            required: true,
            min: 0.01,
          },
          ...(!item
            ? [
                {
                  key: "stock",
                  label: "Estoque inicial",
                  type: "number",
                  min: 0,
                  default: "0",
                },
              ]
            : []),
          {
            key: "low_stock",
            label: "Alerta de estoque baixo",
            type: "number",
            min: 0,
            default: "5",
          },
          {
            key: "species_id",
            label: "Espécie vinculada",
            options: [
              { value: "", label: "Sem vínculo" },
              ...species.map((s) => ({ value: String(s.id), label: s.name })),
            ],
          },
          {
            key: "active",
            label: "Disponibilidade",
            options: [
              { value: "true", label: "Ativo" },
              { value: "false", label: "Inativo" },
            ],
          },
          {
            key: "description",
            label: "Descrição",
            type: "textarea",
            max: 2000,
          },
        ]
      : kind === "species"
        ? [
            { key: "name", label: "Nome popular", required: true, max: 100 },
            {
              key: "scientific_name",
              label: "Nome científico",
              required: true,
              max: 150,
            },
            {
              key: "light",
              label: "Luminosidade",
              options: opts(["Sol pleno", "Meia-sombra", "Sombra"]),
            },
            {
              key: "watering",
              label: "Rega",
              options: opts(["Baixa", "Moderada", "Frequente"]),
            },
            {
              key: "size",
              label: "Porte",
              options: opts(["Pequeno", "Médio", "Grande"]),
            },
            {
              key: "environment",
              label: "Ambiente",
              options: opts(["Interno", "Externo", "Ambos"]),
            },
            {
              key: "difficulty",
              label: "Manutenção",
              options: opts(["Baixa", "Média", "Alta"]),
            },
            {
              key: "use",
              label: "Usos (ex.: Flores / ornamental)",
              required: true,
              max: 200,
            },
            {
              key: "description",
              label: "Características e cuidados",
              type: "textarea",
              max: 2000,
            },
            {
              key: "watering_frequency",
              label: "Frequência de rega",
              max: 100,
            },
            { key: "height", label: "Porte adulto (altura)", max: 100 },
            { key: "family", label: "Família botânica", max: 150 },
            { key: "origin", label: "Origem", max: 300 },
            {
              key: "substrate",
              label: "Substrato",
              type: "textarea",
              max: 1000,
            },
            {
              key: "propagation",
              label: "Propagação",
              type: "textarea",
              max: 1000,
            },
            {
              key: "precautions",
              label: "Precauções",
              type: "textarea",
              max: 1000,
            },
            {
              key: "care",
              label: "Cuidados detalhados",
              type: "textarea",
              max: 3000,
            },
          ]
        : kind === "services"
          ? [
              {
                key: "name",
                label: "Nome do serviço",
                required: true,
                max: 100,
              },
              {
                key: "price_cents",
                label: "Preço de referência (R$)",
                type: "number",
                required: true,
                min: 0.01,
              },
              {
                key: "unit",
                label: "Unidade",
                options: opts(["m²", "visita", "projeto"]),
              },
              {
                key: "delivery_mode",
                label: "Modalidade",
                options: opts(["Presencial", "Virtual"]),
              },
              {
                key: "category",
                label: "Categoria",
                options: opts([
                  "Manutenção",
                  "Implantação",
                  "Irrigação",
                  "Consultoria",
                  "Projeto",
                ]),
              },
              { key: "duration", label: "Duração média", default: "2 horas" },
              {
                key: "responsible",
                label: "Responsável",
                default: "Equipe Ateliê Verde",
              },
              {
                key: "active",
                label: "Status",
                options: [
                  { value: "true", label: "Ativo" },
                  { value: "false", label: "Inativo" },
                ],
              },
              {
                key: "description",
                label: "Descrição",
                type: "textarea",
                max: 2000,
              },
            ]
          : [
              { key: "name", label: "Nome completo", required: true, max: 100 },
              ...(!item
                ? [
                    {
                      key: "email",
                      label: "E-mail",
                      type: "email",
                      required: true,
                      max: 254,
                    },
                    {
                      key: "password",
                      label: "Senha inicial (mínimo 10 caracteres)",
                      type: "password",
                      required: true,
                      max: 128,
                    },
                  ]
                : []),
              { key: "phone", label: "Telefone", max: 30 },
              { key: "address", label: "Endereço", max: 500 },
              ...(item
                ? [
                    { key: "city", label: "Cidade / UF", max: 100 },
                    {
                      key: "active",
                      label: "Status",
                      options: [
                        { value: "true", label: "Ativo" },
                        { value: "false", label: "Inativo" },
                      ],
                    },
                    {
                      key: "notes",
                      label: "Observações",
                      type: "textarea",
                      max: 3000,
                    },
                  ]
                : []),
            ];
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {};
    fields.forEach((f) => {
      const value = String(form.get(f.key) || "");
      body[f.key] =
        f.key === "price_cents"
          ? Math.round(Number(value) * 100)
          : f.key === "species_id"
            ? value
              ? Number(value)
              : null
            : f.key === "active"
              ? value === "true"
              : f.type === "number"
                ? Number(value)
                : value;
    });
    if (kind === "products" && item) body.stock = item.stock;
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
    <form onSubmit={submit} className="form">
      <div className="form-grid">
        {fields.map((f) => {
          const initial = item?.[f.key];
          const value =
            initial === null
              ? ""
              : initial !== undefined
                ? f.key === "price_cents"
                  ? String(Number(initial) / 100)
                  : String(initial)
                : (f.default ?? "");
          return (
            <label className={f.type === "textarea" ? "full" : ""} key={f.key}>
              {f.label}
              {f.options ? (
                <select name={f.key} defaultValue={value || f.options[0].value}>
                  {f.options.map((o) => (
                    <option value={o.value} key={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : f.type === "textarea" ? (
                <textarea
                  name={f.key}
                  defaultValue={value}
                  maxLength={f.max}
                  rows={3}
                />
              ) : (
                <input
                  name={f.key}
                  defaultValue={value}
                  type={f.type || "text"}
                  required={f.required}
                  min={f.min}
                  maxLength={f.max}
                  minLength={
                    f.key === "password"
                      ? 10
                      : f.required && f.type !== "number" && f.type !== "email"
                        ? 2
                        : undefined
                  }
                  step={f.key === "price_cents" ? "0.01" : "1"}
                />
              )}
            </label>
          );
        })}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="form-footer">
        <span>Os dados serão salvos no Ateliê Verde.</span>
        <SaveButton busy={busy} />
      </div>
    </form>
  );
}

export function ProjectForm({
  item,
  customers,
  species,
  onSaved,
}: {
  item?: Project;
  customers: User[];
  species: Species[];
  onSaved: () => Promise<void>;
}) {
  const [plants, setPlants] = useState(item?.plants || []),
    [materials, setMaterials] = useState(item?.materials || []),
    [services, setServices] = useState(item?.services || []),
    [tasks, setTasks] = useState(item?.tasks || []),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const today = new Date().toLocaleDateString("sv-SE");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const f = new FormData(e.currentTarget);
    const body = {
      name: f.get("name"),
      customer_id: Number(f.get("customer_id")),
      address: f.get("address"),
      area: Number(f.get("area")),
      budget_cents: Math.round(Number(f.get("budget")) * 100),
      start_date: f.get("start_date"),
      end_date: f.get("end_date"),
      description: f.get("description"),
      plants,
      materials,
      services,
      tasks,
    };
    try {
      await write(
        `/projects${item ? "/" + item.id : ""}`,
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
  const costs = (
    list: typeof materials,
    set: (v: typeof materials) => void,
    title: string,
  ) => (
    <div className="nested">
      <div className="section-heading">
        <h3>{title}</h3>
        <button
          type="button"
          className="text-button"
          onClick={() =>
            set([...list, { name: "", quantity: 1, unit_price_cents: 0 }])
          }
        >
          <Plus size={15} />
          Adicionar
        </button>
      </div>
      {list.map((row, i) => (
        <div className="cost-row" key={i}>
          <input
            aria-label={`Nome de ${title}`}
            placeholder="Descrição"
            value={row.name}
            required
            onChange={(e) =>
              set(
                list.map((r, j) =>
                  j === i ? { ...r, name: e.target.value } : r,
                ),
              )
            }
          />
          <input
            aria-label="Quantidade"
            type="number"
            min="0.01"
            step="0.01"
            value={row.quantity}
            onChange={(e) =>
              set(
                list.map((r, j) =>
                  j === i ? { ...r, quantity: Number(e.target.value) } : r,
                ),
              )
            }
          />
          <input
            aria-label="Valor unitário em reais"
            type="number"
            min="0"
            step="0.01"
            value={row.unit_price_cents / 100}
            onChange={(e) =>
              set(
                list.map((r, j) =>
                  j === i
                    ? {
                        ...r,
                        unit_price_cents: Math.round(
                          Number(e.target.value) * 100,
                        ),
                      }
                    : r,
                ),
              )
            }
          />
          <button
            type="button"
            className="icon-button"
            aria-label="Remover linha"
            onClick={() => set(list.filter((_, j) => j !== i))}
          >
            <Trash2 size={16} />
          </button>
        </div>
      ))}
      <p className="muted small">
        Descrição · quantidade · valor unitário (R$)
      </p>
    </div>
  );
  return (
    <form onSubmit={submit} className="form">
      <div className="form-grid">
        <label>
          Nome do projeto
          <input
            name="name"
            defaultValue={item?.name}
            required
            minLength={2}
            maxLength={150}
          />
        </label>
        <label>
          Cliente
          <select name="customer_id" defaultValue={item?.customer_id} required>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="full">
          Endereço da obra
          <input
            name="address"
            defaultValue={item?.address}
            required
            minLength={5}
          />
        </label>
        <label>
          Área aproximada (m²)
          <input
            name="area"
            type="number"
            step="0.1"
            min="0.1"
            defaultValue={item?.area}
            required
          />
        </label>
        <label>
          Orçamento total (R$)
          <input
            name="budget"
            type="number"
            step="0.01"
            min="0"
            defaultValue={(item?.budget_cents || 0) / 100}
            required
          />
        </label>
        <label>
          Data inicial
          <input
            name="start_date"
            type="date"
            defaultValue={item?.start_date || today}
            required
          />
        </label>
        <label>
          Data final
          <input
            name="end_date"
            type="date"
            defaultValue={item?.end_date || today}
            required
          />
        </label>
        <label className="full">
          Sobre o projeto
          <textarea
            name="description"
            defaultValue={item?.description}
            rows={2}
          />
        </label>
      </div>
      <div className="nested">
        <div className="section-heading">
          <h3>Espécies selecionadas</h3>
          <button
            type="button"
            className="text-button"
            disabled={!species.length}
            onClick={() =>
              setPlants([...plants, { species_id: species[0].id, quantity: 1 }])
            }
          >
            <Plus size={15} />
            Selecionar espécie
          </button>
        </div>
        {plants.map((plant, i) => (
          <div className="plant-row project-plant-row" key={i}>
            <select
              value={plant.species_id}
              aria-label="Espécie"
              onChange={(e) =>
                setPlants(
                  plants.map((p, j) =>
                    i === j ? { ...p, species_id: Number(e.target.value) } : p,
                  ),
                )
              }
            >
              {species.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.light}
                </option>
              ))}
            </select>
            <input
              aria-label="Quantidade de plantas"
              type="number"
              min="1"
              value={plant.quantity}
              onChange={(e) =>
                setPlants(
                  plants.map((p, j) =>
                    i === j ? { ...p, quantity: Number(e.target.value) } : p,
                  ),
                )
              }
            />
            <input
              aria-label="Aplicação da espécie"
              placeholder="Aplicação no projeto"
              value={plant.application || ""}
              maxLength={200}
              onChange={(e) =>
                setPlants(
                  plants.map((p, j) =>
                    i === j ? { ...p, application: e.target.value } : p,
                  ),
                )
              }
            />
            <button
              type="button"
              aria-label="Remover espécie"
              className="icon-button"
              onClick={() => setPlants(plants.filter((_, j) => j !== i))}
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>
      {costs(materials, setMaterials, "Materiais")}
      {costs(services, setServices, "Serviços")}
      <p className="cost-summary">
        Custos de materiais e serviços:{" "}
        <strong>
          {money(
            [...materials, ...services].reduce(
              (s, c) => s + c.quantity * c.unit_price_cents,
              0,
            ),
          )}
        </strong>
      </p>
      <div className="nested">
        <div className="section-heading">
          <h3>Cronograma</h3>
          <button
            type="button"
            className="text-button"
            onClick={() =>
              setTasks([
                ...tasks,
                { title: "", date: item?.start_date || today, done: false },
              ])
            }
          >
            <Plus size={15} />
            Adicionar etapa
          </button>
        </div>
        {tasks.map((task, i) => (
          <div className="task-row" key={i}>
            <input
              type="checkbox"
              aria-label="Etapa concluída"
              checked={task.done}
              onChange={(e) =>
                setTasks(
                  tasks.map((t, j) =>
                    j === i ? { ...t, done: e.target.checked } : t,
                  ),
                )
              }
            />
            <input
              aria-label="Nome da etapa"
              value={task.title}
              placeholder="Nome da etapa"
              required
              onChange={(e) =>
                setTasks(
                  tasks.map((t, j) =>
                    j === i ? { ...t, title: e.target.value } : t,
                  ),
                )
              }
            />
            <input
              aria-label="Data da etapa"
              type="date"
              required
              value={task.date}
              onChange={(e) =>
                setTasks(
                  tasks.map((t, j) =>
                    j === i ? { ...t, date: e.target.value } : t,
                  ),
                )
              }
            />
            <button
              type="button"
              className="icon-button"
              aria-label="Remover etapa"
              onClick={() => setTasks(tasks.filter((_, j) => j !== i))}
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="form-footer">
        <span>
          Seleção de espécies é planejamento; compras baixam o estoque.
        </span>
        <SaveButton busy={busy} />
      </div>
    </form>
  );
}

export function QuoteForm({
  services,
  onSaved,
  selectedService,
}: {
  services: Service[];
  onSaved: (id: number) => Promise<void>;
  selectedService?: number;
}) {
  const { open } = useGreen();
  const [serviceId, setServiceId] = useState(
    selectedService || services[0]?.id,
  );
  const selected = services.find((s) => s.id === serviceId);
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (selected?.delivery_mode === "Virtual") {
      open("landscape-studio", { service: selected });
      return;
    }
    setBusy(true);
    const f = new FormData(e.currentTarget);
    try {
      const quote = await write<{ id: number }>("/quotes", {
        service_id: Number(f.get("service_id")),
        area: Number(f.get("area")),
        address: f.get("address"),
        description: f.get("description"),
      });
      await onSaved(quote.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="form" onSubmit={submit}>
      <p className="muted">
        Conte sobre o seu espaço. Nossa equipe vai avaliar e preparar uma
        proposta.
      </p>
      <div className="form-grid">
        <label>
          Serviço
          <select
            name="service_id"
            value={serviceId}
            onChange={(e) => setServiceId(Number(e.target.value))}
            required
          >
            {services.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        {selected?.delivery_mode === "Virtual" ? (
          <p className="notice full">
            No atendimento virtual, prepare as medidas, as condições do local e
            as plantas no planejador. Você também poderá importar dados, enviar
            fotos e anexar documentos.
          </p>
        ) : (
          <>
            <label>
              Área aproximada (m²)
              <input name="area" type="number" min="0.1" step="0.1" required />
            </label>
            <label className="full">
              Endereço do local
              <input name="address" required minLength={5} maxLength={500} />
            </label>
            <label className="full">
              O que você tem em mente?
              <textarea
                name="description"
                rows={4}
                maxLength={3000}
                placeholder="Objetivos, condições do espaço e preferências…"
              />
            </label>
          </>
        )}
      </div>
      <p className="muted small">
        Após enviar, você poderá anexar fotos do local.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="form-footer">
        <span>O valor será definido após avaliação.</span>
        <SaveButton
          busy={busy}
          label={
            selected?.delivery_mode === "Virtual"
              ? "Continuar no planejador"
              : "Solicitar orçamento"
          }
        />
      </div>
    </form>
  );
}
