import { useEffect, useState } from "react";
import {
  Truck,
  Plus,
  Pencil,
  PackageOpen,
  CheckCircle,
  Clock,
  ClipboardList,
} from "lucide-react";
import { useGreen } from "./context";
import { api } from "./api";
import { AdminFilters, filterOptions } from "./AdminFilters";
import { Kpi, Panel, Status, Paginator, exportCSV } from "./ReferenceUI";
import { PageTitle } from "./AdminPages";
import { Empty } from "./components";
import { money, dateLabel, type Move } from "./types";

const normalize = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
export function SuppliersPage() {
  const { data, search, setSearch, open, act, go } = useGreen();
  const [category, setCategory] = useState(""),
    [status, setStatus] = useState(""),
    [city, setCity] = useState(""),
    [page, setPage] = useState(1),
    [selected, setSelected] = useState<number | null>(null);
  const list = data.suppliers.filter(
    (s) =>
      (!category || s.category === category) &&
      (!city || s.city === city) &&
      (!status || s.active === (status === "Ativo")) &&
      normalize(
        [
          s.code,
          s.name,
          s.trade_name,
          s.document,
          s.category,
          s.email,
          s.phone,
          s.city,
          s.contact_name,
        ].join(" "),
      ).includes(normalize(search)),
  );
  const supplier = list.find((s) => s.id === selected) || list[0];
  const linked = data.products.filter((p) => p.supplier_id === supplier?.id);
  useEffect(() => setPage(1), [search, category, status, city]);
  return (
    <>
      <PageTitle
        title="Fornecedores"
        subtitle="Parceiros, contatos e abastecimento do estoque"
      >
        <button className="button secondary" onClick={() => go("inventory")}>
          <PackageOpen size={18} />
          Gerenciar produtos
        </button>
        <button
          className="button primary"
          onClick={() => open("entity", { entity: "suppliers" })}
        >
          <Plus size={18} />
          Novo fornecedor
        </button>
      </PageTitle>
      <div className="kpis">
        <Kpi
          title="Fornecedores ativos"
          value={data.suppliers.filter((s) => s.active).length}
          Icon={Truck}
        />
        <Kpi
          title="Produtos com fornecedor"
          value={data.products.filter((p) => p.supplier_id).length}
          Icon={PackageOpen}
          plant={1}
        />
        <Kpi
          title="Categorias atendidas"
          value={
            new Set(
              data.suppliers.filter((s) => s.active).map((s) => s.category),
            ).size
          }
          Icon={CheckCircle}
          plant={2}
        />
        <Kpi
          title="Prazo médio de entrega"
          value={`${Math.round(data.suppliers.filter((s) => s.active).reduce((n, s) => n + s.delivery_days, 0) / (data.suppliers.filter((s) => s.active).length || 1))} dias`}
          Icon={Clock}
          plant={3}
        />
      </div>
      <div className="split customer-split supplier-layout">
        <Panel
          title="Lista de fornecedores"
          Icon={Truck}
          className="supplier-list"
          actions={
            <button
              className="text-button"
              onClick={() =>
                exportCSV(
                  "fornecedores",
                  [
                    "Código",
                    "Nome",
                    "CNPJ",
                    "Categoria",
                    "Contato",
                    "Telefone",
                    "E-mail",
                    "Cidade",
                    "UF",
                    "Prazo",
                    "Status",
                  ],
                  list.map((s) => [
                    s.code,
                    s.name,
                    s.document || "",
                    s.category,
                    s.contact_name,
                    s.phone,
                    s.email,
                    s.city,
                    s.state,
                    s.delivery_days,
                    s.active ? "Ativo" : "Inativo",
                  ]),
                )
              }
            >
              Exportar CSV
            </button>
          }
        >
          <AdminFilters
            search={search}
            onSearch={setSearch}
            placeholder="Buscar fornecedor, CNPJ, contato ou cidade…"
            count={list.length}
            onClear={() => {
              setSearch("");
              setCategory("");
              setCity("");
              setStatus("");
            }}
            fields={[
              {
                label: "Categoria",
                value: category,
                onChange: setCategory,
                options: filterOptions(
                  data.suppliers.map((s) => s.category),
                  "Todas as categorias",
                ),
              },
              {
                label: "Status",
                value: status,
                onChange: setStatus,
                options: filterOptions(["Ativo", "Inativo"], "Todos os status"),
              },
              {
                label: "Cidade",
                value: city,
                onChange: setCity,
                options: filterOptions(
                  data.suppliers.map((s) => s.city),
                  "Todas as cidades",
                ),
              },
            ]}
          />
          <div className="table-scroll">
            <table className="dense-table suppliers-table">
              <thead>
                <tr>
                  <th>Fornecedor</th>
                  <th>Categoria</th>

                  <th>Status</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {list.slice((page - 1) * 10, page * 10).map((s) => (
                  <tr
                    key={s.id}
                    className={supplier?.id === s.id ? "selected" : ""}
                    onClick={() => setSelected(s.id)}
                  >
                    <td>{s.trade_name || s.name}</td>
                    <td>{s.category}</td>

                    <td>
                      <Status value={s.active ? "Ativo" : "Inativo"} />
                    </td>
                    <td>
                      <button
                        className="icon-button bordered"
                        aria-label={`Editar ${s.name}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          open("entity", { entity: "suppliers", record: s });
                        }}
                      >
                        <Pencil size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!list.length && (
              <Empty>
                Nenhum fornecedor encontrado. Cadastre seu primeiro parceiro.
              </Empty>
            )}
          </div>
          <Paginator
            total={list.length}
            page={page}
            setPage={setPage}
            size={10}
          />
        </Panel>
        <Panel
          title="Perfil do fornecedor"
          Icon={Truck}
          actions={
            supplier && (
              <button
                className="button primary small"
                onClick={() =>
                  open("entity", { entity: "suppliers", record: supplier })
                }
              >
                <Pencil size={14} />
                Editar
              </button>
            )
          }
        >
          {supplier ? (
            <div className="supplier-profile-body">
              <div className="supplier-profile-heading">
                <span className="round-icon">
                  <Truck size={26} />
                </span>
                <div>
                  <h3>{supplier.trade_name || supplier.name}</h3>
                  <p>
                    {supplier.code} · {supplier.category}
                  </p>
                  <Status value={supplier.active ? "Ativo" : "Inativo"} />
                </div>
              </div>
              <dl className="supplier-details">
                {[
                  ["Razão social", supplier.name],
                  ["CNPJ", supplier.document || "Não informado"],
                  ["Contato", supplier.contact_name || "—"],
                  ["Telefone", supplier.phone || "—"],
                  ["E-mail", supplier.email || "—"],
                  [
                    "Endereço",
                    [supplier.address, supplier.city, supplier.state]
                      .filter(Boolean)
                      .join(" · ") || "—",
                  ],
                  ["Entrega", `${supplier.delivery_days} dias`],
                ].map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
              <h4>Produtos vinculados ({linked.length})</h4>
              <div className="supplier-products">
                {linked.map((p) => (
                  <button
                    className="supplier-product"
                    key={p.id}
                    onClick={() =>
                      open("entity", { entity: "products", record: p })
                    }
                  >
                    <span>
                      {p.name}
                      <small>
                        {p.sku} · {p.unit}
                      </small>
                    </span>
                    <b>{p.stock} em estoque</b>
                  </button>
                ))}
                {!linked.length && (
                  <p className="form-hint">
                    Vincule produtos a este fornecedor no cadastro do Estoque.
                  </p>
                )}
              </div>
              {supplier.notes && (
                <p className="supplier-notes">{supplier.notes}</p>
              )}
              <button
                className="text-button"
                onClick={() =>
                  act(
                    `/suppliers/${supplier.id}/status`,
                    { active: !supplier.active },
                    "PATCH",
                    supplier.active
                      ? "Fornecedor inativado; histórico preservado."
                      : "Fornecedor ativado.",
                  )
                }
              >
                {supplier.active ? "Inativar fornecedor" : "Ativar fornecedor"}
              </button>
            </div>
          ) : (
            <Empty>Selecione um fornecedor.</Empty>
          )}
        </Panel>
      </div>
    </>
  );
}

type Audit = {
  id: number;
  entity: string;
  entity_id: number;
  action: string;
  actor_name: string;
  created_at: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
};
export function AuditHistory() {
  const [entity, setEntity] = useState(""),
    [page, setPage] = useState(1),
    [result, setResult] = useState<{ total: number; items: Audit[] }>({
      total: 0,
      items: [],
    }),
    [error, setError] = useState("");
  const [selectedAudit, setSelectedAudit] = useState<Audit | null>(null);
  useEffect(() => {
    let active = true;
    api<{ total: number; items: Audit[] }>(
      `/audit-events?entity=${encodeURIComponent(entity)}&offset=${(page - 1) * 20}&limit=20`,
    )
      .then((r) => {
        if (active) {
          setResult(r);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [entity, page]);
  return (
    <div className="detail commercial-history">
      <label>
        Cadastro / operação
        <select
          value={entity}
          onChange={(e) => {
            setEntity(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Todos</option>
          {["Produto", "Estoque", "Cliente", "Fornecedor", "Financeiro"].map(
            (e) => (
              <option key={e}>{e}</option>
            ),
          )}
        </select>
      </label>
      {selectedAudit && (
        <section className="record-details">
          <h3>
            {selectedAudit.entity} · {selectedAudit.action}
          </h3>
          <p>Responsável: {selectedAudit.actor_name}</p>
          <dl>
            {Object.keys(selectedAudit.after)
              .filter(
                (key) =>
                  JSON.stringify(selectedAudit.before[key]) !==
                  JSON.stringify(selectedAudit.after[key]),
              )
              .map((key) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>
                    {selectedAudit.before[key] !== undefined && (
                      <>{JSON.stringify(selectedAudit.before[key])} → </>
                    )}
                    {JSON.stringify(selectedAudit.after[key])}
                  </dd>
                </div>
              ))}
          </dl>
          <button
            className="text-button"
            onClick={() => setSelectedAudit(null)}
          >
            Fechar detalhes
          </button>
        </section>
      )}
      <div className="table-scroll">
        <table className="dense-table audit-table">
          <thead>
            <tr>
              <th>Data</th>

              <th>Cadastro</th>
              <th>Ação</th>
              <th>Alterações</th>
            </tr>
          </thead>
          <tbody>
            {result.items.map((a) => (
              <tr key={a.id}>
                <td>{dateLabel(a.created_at)}</td>

                <td>
                  {a.entity} #{a.entity_id}
                </td>
                <td>{a.action}</td>
                <td>
                  <button
                    className="text-button"
                    aria-label={`Ver alteração ${a.id}`}
                    onClick={() => setSelectedAudit(a)}
                  >
                    Ver dados
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!result.total && (
          <Empty>Nenhuma alteração registrada com este filtro.</Empty>
        )}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <Paginator total={result.total} page={page} setPage={setPage} size={20} />
    </div>
  );
}

export function StockHistory() {
  const { data, open } = useGreen();
  const [product, setProduct] = useState(""),
    [kind, setKind] = useState(""),
    [start, setStart] = useState(""),
    [end, setEnd] = useState(""),
    [page, setPage] = useState(1),
    [error, setError] = useState("");
  const [result, setResult] = useState<{
    total: number;
    items: (Move & { product_name: string; actor_name: string })[];
  }>({ total: 0, items: [] });
  useEffect(() => {
    let active = true;
    const query = new URLSearchParams({
      kind,
      offset: String((page - 1) * 20),
      limit: "20",
    });
    if (product) query.set("product_id", product);
    if (start) query.set("start", start);
    if (end) query.set("end", end);
    api<typeof result>(`/stock-history?${query}`)
      .then((r) => {
        if (active) {
          setResult(r);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [product, kind, start, end, page]);
  return (
    <div className="detail commercial-history">
      <div className="form-grid">
        <label>
          Produto
          <select
            value={product}
            onChange={(e) => {
              setProduct(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Todos os produtos</option>
            {data.products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.sku} · {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Tipo
          <select
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Todos</option>
            <option>Entrada</option>
            <option>Saída</option>
          </select>
        </label>
        <label>
          De
          <input
            type="date"
            value={start}
            onChange={(e) => {
              setStart(e.target.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          Até
          <input
            type="date"
            value={end}
            onChange={(e) => {
              setEnd(e.target.value);
              setPage(1);
            }}
          />
        </label>
      </div>
      <div className="table-scroll">
        <table className="dense-table stock-history-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Produto</th>

              <th>Qtd.</th>
              <th>Saldo antes → depois</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {result.items.map((m) => (
              <tr key={m.id}>
                <td>{dateLabel(m.created_at)}</td>
                <td>{m.product_name}</td>

                <td>
                  {m.quantity > 0 ? "+" : ""}
                  {m.quantity}
                </td>
                <td>
                  {m.balance_before === null
                    ? "—"
                    : `${m.balance_before} → ${m.balance_after}`}
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={`Detalhes da movimentação ${m.id}`}
                    onClick={() => open("movement-detail", m)}
                  >
                    <ClipboardList size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!result.total && <Empty>Nenhuma movimentação encontrada.</Empty>}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <Paginator total={result.total} page={page} setPage={setPage} size={20} />
    </div>
  );
}
