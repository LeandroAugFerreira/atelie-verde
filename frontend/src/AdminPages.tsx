import { useEffect, useState } from "react";
import { RafinhaSettings } from "./RafinhaAssistant";
import { AdminAISettings } from "./AdminAISettings";
import {
  BarChart3,
  Wrench,
  Folder,
  ShoppingCart,
  Trophy,
  AlertCircle,
  Box,
  PackageOpen,
  ArrowLeftRight,
  Tag,
  Plus,
  Upload,
  FilePlus,
  Users,
  UserPlus,
  RefreshCw,
  Search,
  Pencil,
  MoreHorizontal,
  MapPin,
  Phone,
  Mail,
  CalendarDays,
  Clock,
  Leaf,
  FileText,
  CheckCircle,
  DollarSign,
  ArrowRight,
  X,
  Download,
  PieChart,
  TrendingDown,
  Filter,
  Sprout,
  Home,
  Image as ImageIcon,
  ClipboardList,
  Flag,
  ArrowLeft,
  Wallet,
  Ruler,
  Settings,
  Check,
} from "lucide-react";
import { useGreen } from "./context";
import { NavigationBreadcrumb } from "./NavigationBreadcrumb";
import { api, write } from "./api";
import {
  Kpi,
  Panel,
  Picture,
  Period,
  YearSelect,
  QuickPeriod,
  Status,
  Paginator,
  SearchInput,
  Avatar,
  CashChart,
  Donut,
  Sprite,
  exportCSV,
} from "./ReferenceUI";
import { Empty, Gallery, SaveButton } from "./components";
import {
  money,
  dateLabel,
  stages,
  type Ledger,
  type Project,
  type User,
  type Quote,
} from "./types";

import { AdminFilters, filterOptions } from "./AdminFilters";
import { ProjectCover } from "./ProjectCover";
import { ProjectUsage } from "./ProjectUsage";
import { CategorySales } from "./CategorySales";
import { categories } from "./Forms";
import { matchesPlantGroup, plantGroupOptions } from "./plantGroups";
import { ProjectPlan } from "./ProjectPlan";
import { QuoteDocuments } from "./QuoteDocuments";

const normalize = (value: string) =>
  value
    .trim()
    .toLocaleLowerCase("pt-BR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
const match = (search: string, ...values: unknown[]) =>
  normalize(values.join(" ")).includes(normalize(search)) ||
  (/^[\d./()\s+-]+$/.test(search) &&
    search.replace(/\D/g, "").length >= 3 &&
    values.some((value) =>
      String(value || "")
        .replace(/\D/g, "")
        .includes(search.replace(/\D/g, "")),
    ));
export function PageTitle({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children?: React.ReactNode;
}) {
  const { user } = useGreen();
  return (
    <div className="page-title">
      <div>
        <div className="page-title-headline">
          <h1>{title}</h1>
          {user.role === "admin" && <NavigationBreadcrumb />}
        </div>
        <p>{subtitle}</p>
      </div>
      <div className="title-actions">{children}</div>
    </div>
  );
}
function GoLink({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button className="text-button" onClick={onClick}>
      {children}
      <ArrowRight size={15} />
    </button>
  );
}
export function DashboardPage() {
  const { data, go } = useGreen();
  const a = data.analytics;
  if (!a) return null;
  const low = data.products.filter((p) => p.active && p.stock <= p.low_stock);
  return (
    <>
      <PageTitle title="Dashboard" subtitle="Visão geral do negócio">
        <Period />
      </PageTitle>
      <div className="kpis">
        <Kpi
          title="Faturamento"
          value={money(a.income)}
          Icon={BarChart3}
          change={a.growth}
        />
        <Kpi
          title="Serviços realizados"
          value={a.services_completed}
          Icon={Wrench}
          plant={1}
        />
        <Kpi
          title="Projetos em andamento"
          value={a.projects_active}
          Icon={Folder}
          plant={2}
        />
        <Kpi
          title="Produtos vendidos"
          value={a.products_sold}
          Icon={ShoppingCart}
          plant={3}
        />
      </div>
      <div className="split charts">
        <Panel
          title="Faturamento mensal"
          Icon={BarChart3}
          actions={<YearSelect />}
        >
          <CashChart />
        </Panel>
        <Panel
          title="Vendas por categoria"
          className="category-panel"
          actions={<QuickPeriod />}
        >
          <CategorySales values={a.categories} />
        </Panel>
      </div>
      <div className="split equal">
        <Panel
          title="Produtos mais vendidos"
          Icon={Trophy}
          actions={
            <GoLink onClick={() => go("products")}>
              Ver todos os produtos
            </GoLink>
          }
        >
          <div className="table-scroll">
            <table className="dense-table sales-table">
              <thead>
                <tr>
                  <th>Produto</th>

                  <th>Vendidos</th>
                  <th>Receita</th>
                </tr>
              </thead>
              <tbody>
                {a.top_products.map((p, i) => (
                  <tr key={p.product.id}>
                    <td>
                      <span className="cell-product">
                        <Picture item={p.product} />
                        {p.product.name}
                      </span>
                    </td>

                    <td>{p.quantity}</td>
                    <td>{money(p.revenue_cents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!a.top_products.length && <Empty>Sem vendas no período.</Empty>}
          </div>
        </Panel>
        <Panel
          title="Estoque baixo"
          Icon={AlertCircle}
          actions={
            <GoLink onClick={() => go("inventory")}>Ver todo o estoque</GoLink>
          }
        >
          <div className="table-scroll">
            <table className="dense-table low-stock-table">
              <thead>
                <tr>
                  <th>Produto</th>

                  <th>Estoque atual</th>

                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {low.slice(0, 5).map((p) => (
                  <tr key={p.id}>
                    <td>
                      <span className="cell-product">
                        <Picture item={p} />
                        {p.name}
                      </span>
                    </td>

                    <td className="red-text">{p.stock}</td>

                    <td>
                      <Status value={p.stock <= 3 ? "Crítico" : "Atenção"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!low.length && <Empty>Estoque em dia.</Empty>}
          </div>
        </Panel>
      </div>
    </>
  );
}

export function InventoryPage({
  productsOnly = false,
}: {
  productsOnly?: boolean;
}) {
  const { data, search, setSearch, open, reload, toast, selectedId } =
    useGreen();
  const [status, setStatus] = useState(""),
    [category, setCategory] = useState(
      selectedId ? categories[selectedId - 1] || "" : "",
    ),
    [supplierFilter, setSupplierFilter] = useState(""),
    [group, setGroup] = useState(""),
    [page, setPage] = useState(1),
    [importing, setImporting] = useState(false);
  useEffect(
    () => setPage(1),
    [search, status, category, group, supplierFilter],
  );
  const filtered = data.products.filter((p) => {
    const plant = data.species.find((s) => s.id === p.species_id);
    return (
      match(
        search,
        p.name,
        p.category,
        p.sku,
        p.brand,
        p.variant,
        p.barcode || "",
        data.suppliers.find((s) => s.id === p.supplier_id)?.name,
        plant?.scientific_name,
      ) &&
      (!supplierFilter || String(p.supplier_id) === supplierFilter) &&
      (!category || p.category === category) &&
      matchesPlantGroup(plant, group) &&
      (!status ||
        (status === "Inativo"
          ? !p.active
          : p.active &&
            (status === "Esgotado"
              ? p.stock === 0
              : status === "Baixo"
                ? p.stock > 0 && p.stock <= p.low_stock
                : p.stock > p.low_stock)))
    );
  });
  async function importFile(file: File) {
    setImporting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const result = await api<{ imported: number }>("/products-import", {
        method: "POST",
        body: form,
      });
      await reload();
      toast(`${result.imported} produtos importados.`);
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setImporting(false);
    }
  }
  return (
    <>
      <PageTitle
        title={productsOnly ? "Produtos" : "Estoque"}
        subtitle={
          productsOnly
            ? "Catálogo, informações e preços dos produtos"
            : "Controle de entradas, saídas e níveis de produtos"
        }
      >
        <button
          className="button primary"
          onClick={() => open("entity", { entity: "products" })}
        >
          <Plus size={20} />
          Novo produto
        </button>
        {!productsOnly && (
          <>
            <label className="button secondary">
              <Upload size={19} />
              {importing ? "Importando…" : "Importar planilha"}
              <input
                hidden
                type="file"
                accept=".csv,.xlsx"
                disabled={importing}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) importFile(f);
                  e.target.value = "";
                }}
              />
            </label>
            <button className="button secondary" onClick={() => open("stock")}>
              <FilePlus size={19} />
              Registrar movimentação
            </button>
          </>
        )}
      </PageTitle>
      <div className="kpis">
        <Kpi
          title="Total em estoque"
          value={data.products
            .reduce((s, p) => s + p.stock, 0)
            .toLocaleString("pt-BR")}
          Icon={Box}
        />
        <Kpi
          title="Itens com estoque baixo"
          value={
            data.products.filter((p) => p.active && p.stock <= p.low_stock)
              .length
          }
          Icon={AlertCircle}
          red
          plant={1}
        />
        <Kpi
          title="Movimentações do período"
          value={data.analytics?.stock_moves_month || 0}
          Icon={ArrowLeftRight}
          plant={2}
        />
        <Kpi
          title="Categorias"
          value={new Set(data.products.map((p) => p.category)).size}
          Icon={Tag}
          caption="tipos de produtos cadastrados"
          plant={3}
        />
      </div>
      <div className={`split ${productsOnly ? "single" : "stock-layout"}`}>
        <Panel
          className="inventory-panel"
          title={productsOnly ? "Produtos cadastrados" : "Produtos em estoque"}
          Icon={Box}
        >
          <AdminFilters
            search={search}
            onSearch={setSearch}
            placeholder="Buscar produto, SKU ou espécie…"
            count={filtered.length}
            onClear={() => {
              setSearch("");
              setStatus("");
              setCategory("");
              setGroup("");
              setSupplierFilter("");
            }}
            fields={[
              {
                label: "Fornecedor",
                value: supplierFilter,
                onChange: setSupplierFilter,
                options: [
                  { value: "", label: "Todos os fornecedores" },
                  ...data.suppliers.map((s) => ({
                    value: String(s.id),
                    label: s.name,
                  })),
                ],
              },
              {
                label: "Categoria",
                value: category,
                onChange: setCategory,
                options: filterOptions(
                  data.products.map((p) => p.category),
                  "Todas as categorias",
                ),
              },
              {
                label: "Estoque / situação",
                value: status,
                onChange: setStatus,
                options: filterOptions(
                  ["Normal", "Baixo", "Esgotado", "Inativo"],
                  "Todas as situações",
                ),
              },
              {
                label: "Tipo de planta",
                value: group,
                onChange: setGroup,
                options: [
                  { value: "", label: "Todas as espécies" },
                  ...plantGroupOptions(data.species),
                ],
              },
            ]}
          />
          <div className="table-scroll">
            <table className="dense-table inventory-table">
              <thead>
                <tr>
                  <th>Produto</th>

                  <th>Preço</th>
                  <th>Saldo</th>

                  <th>Status</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {!filtered.length && (
                  <tr>
                    <td colSpan={5}>
                      <Empty>
                        Nenhum produto encontrado. Ajuste ou limpe os filtros.
                      </Empty>
                    </td>
                  </tr>
                )}
                {filtered.slice((page - 1) * 5, page * 5).map((p) => (
                  <tr key={p.id}>
                    <td>
                      <span className="cell-product">
                        <Picture item={p} />
                        <span title={p.name}>
                          {p.name}
                          <small className="row-code" title={p.sku}>
                            {p.sku}
                          </small>
                        </span>
                      </span>
                    </td>

                    <td>{money(p.price_cents)}</td>
                    <td>{p.stock}</td>

                    <td>
                      <Status
                        value={
                          !p.active
                            ? "Inativo"
                            : p.stock <= p.low_stock
                              ? "Baixo"
                              : "Normal"
                        }
                      />
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="icon-button bordered"
                          aria-label={`Editar ${p.name}`}
                          onClick={() =>
                            open("entity", { entity: "products", record: p })
                          }
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          className="icon-button bordered"
                          aria-label={`Movimentar ${p.name}`}
                          onClick={() => open("stock", p)}
                        >
                          <MoreHorizontal size={16} />
                        </button>
                        <button
                          className="icon-button"
                          aria-label={`Fotos de ${p.name}`}
                          onClick={() => open("product-photos", p)}
                        >
                          <ImageIcon size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Paginator
            total={filtered.length}
            page={page}
            setPage={setPage}
            size={5}
          />
          <button
            className="text-button small"
            onClick={() =>
              exportCSV(
                "modelo-produtos",
                [
                  "name",
                  "sku",
                  "category",
                  "price_cents",
                  "stock",
                  "low_stock",
                  "location",
                ],
                [
                  [
                    "Novo produto",
                    "PL-NOVO",
                    "Plantas",
                    2990,
                    10,
                    5,
                    "A1 - Plantas",
                  ],
                ],
              )
            }
          >
            Baixar modelo de importação CSV
          </button>
        </Panel>
        {!productsOnly && (
          <Panel
            title="Movimentações recentes"
            Icon={ArrowLeftRight}
            actions={<GoLink onClick={() => open("moves")}>Ver todas</GoLink>}
          >
            <div className="table-scroll">
              <table className="dense-table recent-moves-table">
                <thead>
                  <tr>
                    <th>Data</th>

                    <th>Produto</th>
                    <th>Qtd.</th>
                  </tr>
                </thead>
                <tbody>
                  {data.moves.slice(0, 7).map((m) => (
                    <tr key={m.id}>
                      <td>
                        {dateLabel(m.created_at)}
                        <small>
                          {new Date(m.created_at).toLocaleTimeString("pt-BR", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </small>
                      </td>

                      <td>
                        {data.products.find((p) => p.id === m.product_id)?.name}
                        <small>{m.reason}</small>
                      </td>
                      <td
                        className={m.quantity > 0 ? "green-text" : "red-text"}
                      >
                        {m.quantity > 0 ? "+" : ""}
                        {m.quantity}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        )}
      </div>
    </>
  );
}

export function CustomersPage() {
  const { data, search, setSearch, open } = useGreen();
  const [selected, setSelected] = useState<number | null>(null),
    [page, setPage] = useState(1),
    [status, setStatus] = useState(""),
    [city, setCity] = useState(""),
    [link, setLink] = useState("");
  const list = data.customers.filter(
    (c) =>
      match(
        search,
        c.name,
        c.city,
        c.email,
        c.phone,
        c.customer_code || "",
        c.document || "",
        c.contact_name,
      ) &&
      (!status || c.active === (status === "Ativo")) &&
      (!city || c.city === city) &&
      (!link ||
        data.projects.some((p) => p.customer_id === c.id) ===
          (link === "Com projetos")),
  );
  const customer = list.find((c) => c.id === selected) || list[0];
  useEffect(() => setPage(1), [search, status, city, link]);
  const a = data.analytics;
  return (
    <>
      <PageTitle
        title="Clientes"
        subtitle="Cadastros, relacionamento e histórico"
      >
        <button
          className="button primary"
          onClick={() => open("entity", { entity: "customers" })}
        >
          <Plus size={20} />
          Novo cliente
        </button>
        <button
          className="button secondary"
          onClick={() =>
            exportCSV(
              "clientes",
              ["Cliente", "Cidade", "Telefone", "E-mail", "Status"],
              list.map((c) => [
                c.name,
                c.city,
                c.phone,
                c.email,
                c.active ? "Ativo" : "Inativo",
              ]),
            )
          }
        >
          <Upload size={18} />
          Exportar CSV
        </button>
      </PageTitle>
      <div className="kpis">
        <Kpi
          title="Clientes ativos"
          value={a?.customers_active || 0}
          Icon={Users}
        />
        <Kpi
          title="Novos no período"
          value={a?.customers_new || 0}
          Icon={UserPlus}
          plant={1}
        />
        <Kpi
          title="Clientes recorrentes"
          value={a?.customers_recurring || 0}
          Icon={RefreshCw}
          plant={2}
        />
        <Kpi
          title="Ticket médio"
          value={money(a?.average_ticket || 0)}
          Icon={BarChart3}
          plant={3}
        />
      </div>
      <div className="split detail-layout">
        <Panel
          className="customers-panel"
          title="Lista de clientes"
          Icon={Users}
        >
          <AdminFilters
            search={search}
            onSearch={setSearch}
            placeholder="Buscar nome, e-mail ou telefone…"
            count={list.length}
            onClear={() => {
              setSearch("");
              setStatus("");
              setCity("");
              setLink("");
            }}
            fields={[
              {
                label: "Status do cliente",
                value: status,
                onChange: setStatus,
                options: filterOptions(["Ativo", "Inativo"], "Todos os status"),
              },
              {
                label: "Cidade",
                value: city,
                onChange: setCity,
                options: filterOptions(
                  data.customers.map((c) => c.city),
                  "Todas as cidades",
                ),
              },
              {
                label: "Projetos",
                value: link,
                onChange: setLink,
                options: filterOptions(
                  ["Com projetos", "Sem projetos"],
                  "Todos os clientes",
                ),
              },
            ]}
          />
          <div className="table-scroll">
            <table className="dense-table customers-table">
              <thead>
                <tr>
                  <th>Cliente</th>
                  <th>Cidade</th>

                  <th>Total gasto</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {!list.length && (
                  <tr>
                    <td colSpan={5}>
                      <Empty>
                        Nenhum cliente encontrado. Ajuste ou limpe os filtros.
                      </Empty>
                    </td>
                  </tr>
                )}
                {list.slice((page - 1) * 10, page * 10).map((c, i) => (
                  <tr
                    key={c.id}
                    className={customer?.id === c.id ? "selected-row" : ""}
                    onClick={() => setSelected(c.id)}
                  >
                    <td>
                      <span className="cell-person">
                        <Avatar name={c.name} url={c.avatar_url} />
                        <span title={c.name}>{c.name}</span>
                      </span>
                    </td>
                    <td>{c.city || "Não informado"}</td>

                    <td>
                      {money(
                        data.ledger
                          .filter(
                            (l) =>
                              l.customer_id === c.id &&
                              l.direction === "Receita" &&
                              l.status === "Pago",
                          )
                          .reduce((s, l) => s + l.amount_cents, 0),
                      )}
                    </td>
                    <td>
                      <Status value={c.active ? "Ativo" : "Inativo"} />
                    </td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label={`Detalhes de ${c.name}`}
                        onClick={() => setSelected(c.id)}
                      >
                        <MoreHorizontal size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Paginator total={list.length} page={page} setPage={setPage} />
        </Panel>
        {customer ? (
          <CustomerProfile customer={customer} />
        ) : (
          <Empty>Nenhum cliente selecionado.</Empty>
        )}
      </div>
    </>
  );
}
function CustomerProfile({ customer: c }: { customer: User }) {
  const { data, open, go } = useGreen();
  const [tab, setTab] = useState("Histórico");
  const projects = data.projects.filter((p) => p.customer_id === c.id),
    appointments = data.appointments.filter((a) => a.customer_id === c.id),
    paid = data.ledger.filter(
      (l) =>
        l.customer_id === c.id &&
        l.direction === "Receita" &&
        l.status === "Pago",
    );
  return (
    <Panel
      title="Perfil do cliente"
      Icon={Users}
      actions={
        <button
          className="button primary small"
          onClick={() => open("entity", { entity: "customers", record: c })}
        >
          <Pencil size={15} />
          Editar
        </button>
      }
    >
      <div className="profile-header">
        <Avatar name={c.name} url={c.avatar_url} />
        <div>
          <h3>{c.name}</h3>
          <Status value={c.active ? "Cliente ativo" : "Inativo"} />
          <p>
            <Phone size={13} />
            {c.phone}
          </p>
          <p>
            <Mail size={13} />
            {c.email}
          </p>
          <p>
            <MapPin size={13} />
            {c.city}
          </p>
          <p>
            <CalendarDays size={13} />
            Cliente desde {dateLabel(c.created_at)}
          </p>
        </div>
      </div>
      <details className="customer-commercial">
        <summary>Dados comerciais</summary>
        <p>
          {c.customer_code || "—"} · {c.customer_type}
        </p>
        <p>CPF/CNPJ: {c.document || "Não informado"}</p>
        <p>
          {[c.address, c.district, c.city, c.state, c.postal_code]
            .filter(Boolean)
            .join(" · ") || "Endereço não informado"}
        </p>
        <p>
          Portal:{" "}
          {c.portal_enabled
            ? "Acesso habilitado"
            : "Cadastro comercial sem acesso"}
        </p>
      </details>
      <div className="profile-metrics">
        <div>
          <Folder size={21} />
          <strong>{projects.length}</strong>
          <small>Projetos</small>
        </div>
        <div>
          <ShoppingCart size={21} />
          <strong>{appointments.length}</strong>
          <small>Serviços</small>
        </div>
        <div>
          <Wallet size={21} />
          <strong>{money(paid.reduce((s, l) => s + l.amount_cents, 0))}</strong>
          <small>Total gasto</small>
        </div>
      </div>
      <div className="tabs compact">
        {["Histórico", "Projetos", "Serviços", "Observações"].map((t) => (
          <button
            className={tab === t ? "selected" : ""}
            key={t}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "Histórico" &&
        paid.slice(0, 4).map((l) => (
          <div className="profile-history" key={l.id}>
            <span>
              {l.paid_date.slice(8)}
              <small>
                {new Date(l.paid_date + "T12:00:00").toLocaleDateString(
                  "pt-BR",
                  { month: "short", year: "numeric" },
                )}
              </small>
            </span>
            <span className="round-icon small">
              <Wrench size={18} />
            </span>
            <div>
              <strong>{l.description}</strong>
              <small>{l.source} · recebido</small>
            </div>
            <strong>{money(l.amount_cents)}</strong>
          </div>
        ))}
      {tab === "Projetos" &&
        projects.map((p) => (
          <button
            className="detail-link"
            key={p.id}
            onClick={() => go("project", p.id)}
          >
            {p.name}
            <Status value={p.status} />
          </button>
        ))}
      {tab === "Serviços" &&
        appointments.map((a) => (
          <div className="detail-link" key={a.id}>
            {a.title}
            <Status value={a.status} />
          </div>
        ))}
      {tab === "Observações" && (
        <p className="notes">{c.notes || "Nenhuma observação registrada."}</p>
      )}
      <div className="notes">
        <FileText size={23} />
        <div>
          <strong>Observações</strong>
          <p>{c.notes || "Adicione preferências e observações no cadastro."}</p>
        </div>
      </div>
    </Panel>
  );
}

export function ServicesPage() {
  const { data, search, setSearch, open } = useGreen();
  const [status, setStatus] = useState(""),
    [category, setCategory] = useState(""),
    [responsible, setResponsible] = useState(""),
    [offset, setOffset] = useState(0),
    [day, setDay] = useState(0);
  const monday = new Date();
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7) + offset * 7);
  const days = Array.from({ length: 5 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(d.getDate() + i);
    return d;
  });
  const date = days[day].toLocaleDateString("sv-SE");
  const appointments = data.appointments.filter((a) => a.date === date);
  const filtered = data.services.filter(
    (s) =>
      match(search, s.name, s.description, s.responsible) &&
      (!status || s.active === (status === "Ativo")) &&
      (!category || s.category === category) &&
      (!responsible || s.responsible === responsible),
  );
  const a = data.analytics;
  return (
    <>
      <PageTitle
        title="Serviços"
        subtitle="Catálogo, execução e acompanhamento"
      >
        <button
          className="button secondary"
          onClick={() => open("appointment")}
        >
          <CalendarDays size={18} />
          Agendar serviço
        </button>
        <button
          className="button primary"
          onClick={() => open("entity", { entity: "services" })}
        >
          <Plus size={19} />
          Novo serviço
        </button>
      </PageTitle>
      <div className="kpis">
        <Kpi
          title="Serviços ativos"
          value={data.services.filter((s) => s.active).length}
          Icon={Leaf}
        />
        <Kpi
          title="Concluídos no período"
          value={a?.services_completed || 0}
          Icon={CheckCircle}
          plant={1}
        />
        <Kpi
          title="Equipes em campo"
          value={a?.teams || 0}
          Icon={Users}
          plant={2}
        />
        <Kpi
          title="Faturamento do serviço"
          value={money(a?.service_income || 0)}
          Icon={BarChart3}
          plant={3}
        />
      </div>
      <div className="split service-layout">
        <Panel
          className="services-panel"
          title="Serviços cadastrados"
          Icon={Leaf}
        >
          <AdminFilters
            search={search}
            onSearch={setSearch}
            placeholder="Buscar serviço ou responsável…"
            count={filtered.length}
            onClear={() => {
              setSearch("");
              setStatus("");
              setCategory("");
              setResponsible("");
            }}
            fields={[
              {
                label: "Status do serviço",
                value: status,
                onChange: setStatus,
                options: filterOptions(["Ativo", "Inativo"], "Todos os status"),
              },
              {
                label: "Categoria",
                value: category,
                onChange: setCategory,
                options: filterOptions(
                  data.services.map((s) => s.category),
                  "Todas as categorias",
                ),
              },
              {
                label: "Responsável",
                value: responsible,
                onChange: setResponsible,
                options: filterOptions(
                  data.services.map((s) => s.responsible),
                  "Todos os responsáveis",
                ),
              },
            ]}
          />
          <div className="table-scroll">
            <table className="dense-table services-table">
              <thead>
                <tr>
                  <th>Serviço</th>

                  <th>Preço inicial</th>

                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {!filtered.length && (
                  <tr>
                    <td colSpan={4}>
                      <Empty>
                        Nenhum serviço encontrado. Ajuste ou limpe os filtros.
                      </Empty>
                    </td>
                  </tr>
                )}
                {filtered.map((s, i) => (
                  <tr key={s.id}>
                    <td>
                      <span className="cell-product">
                        <Sprite name={s.demo_asset} />
                        <span>
                          {s.name}
                          <small>{s.description.slice(0, 38)}</small>
                        </span>
                      </span>
                    </td>

                    <td>{money(s.price_cents)}</td>

                    <td>
                      <Status value={s.active ? "Ativo" : "Inativo"} />
                    </td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label={`Editar ${s.name}`}
                        onClick={() =>
                          open("entity", { entity: "services", record: s })
                        }
                      >
                        <MoreHorizontal size={17} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="table-note">
            Mostrando {filtered.length} serviços cadastrados
          </p>
        </Panel>
        <Panel
          title="Agenda da semana"
          Icon={CalendarDays}
          actions={
            <GoLink onClick={() => open("agenda")}>Ver agenda completa</GoLink>
          }
        >
          <div className="week-strip">
            <button
              className="icon-button bordered"
              aria-label="Semana anterior"
              onClick={() => setOffset(offset - 1)}
            >
              <ArrowLeft size={16} />
            </button>
            {days.map((d, i) => (
              <button
                key={i}
                className={day === i ? "active" : ""}
                onClick={() => setDay(i)}
              >
                <strong>{["Seg", "Ter", "Qua", "Qui", "Sex"][i]}</strong>
                <small>
                  {d.toLocaleDateString("pt-BR", {
                    day: "2-digit",
                    month: "short",
                  })}
                </small>
              </button>
            ))}
            <button
              className="icon-button bordered"
              aria-label="Próxima semana"
              onClick={() => setOffset(offset + 1)}
            >
              <ArrowRight size={16} />
            </button>
          </div>
          <div className="appointments">
            {appointments.map((a) => (
              <button
                className="appointment"
                key={a.id}
                onClick={() => open("appointment", a)}
              >
                <span>
                  {a.start_time}
                  <small>{a.end_time}</small>
                </span>
                <Sprite
                  name={
                    data.services.find((s) => s.id === a.service_id)
                      ?.demo_asset || "plants"
                  }
                />
                <div>
                  <strong>{a.title}</strong>
                  <small>
                    {data.customers.find((c) => c.id === a.customer_id)?.name}
                  </small>
                  <small>
                    {data.services.find((s) => s.id === a.service_id)?.category}{" "}
                    · {a.status}
                  </small>
                </div>
                <MapPin size={14} />
              </button>
            ))}
            {!appointments.length && (
              <Empty>Sem serviços agendados neste dia.</Empty>
            )}
          </div>
          <div className="notes">
            <span className="round-icon">
              <CalendarDays size={27} />
            </span>
            <div>
              <h3>Mais produtividade no campo</h3>
              <p>
                Acompanhe visitas, aloque equipes e mantenha seus serviços em
                dia.
              </p>
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}

export function QuotesPage() {
  const { data, search, setSearch, open } = useGreen();
  const [selected, setSelected] = useState<number | null>(null),
    [page, setPage] = useState(1),
    [status, setStatus] = useState(""),
    [service, setService] = useState(""),
    [from, setFrom] = useState(""),
    [to, setTo] = useState("");
  useEffect(() => setPage(1), [search, status, service, from, to]);
  const filtered = data.quotes.filter(
    (q) =>
      match(
        search,
        `ORC-${new Date(q.created_at).getFullYear()}-${String(q.id).padStart(3, "0")}`,
        data.customers.find((c) => c.id === q.customer_id)?.name,
        data.services.find((s) => s.id === q.service_id)?.name,
      ) &&
      (!status || q.status === status) &&
      (!service || q.service_id === Number(service)) &&
      (!from || q.created_at.slice(0, 10) >= from) &&
      (!to || q.created_at.slice(0, 10) <= to),
  );
  const quote = filtered.find((q) => q.id === selected) || filtered[0];
  return (
    <>
      <PageTitle
        title="Orçamentos"
        subtitle="Solicitações, propostas e aprovações"
      >
        <button className="button primary" onClick={() => open("admin-quote")}>
          <Plus size={20} />
          Novo orçamento
        </button>
      </PageTitle>
      <div className="kpis">
        <Kpi
          title="Orçamentos pendentes"
          value={data.quotes.filter((q) => q.status === "Solicitado").length}
          Icon={FileText}
        />
        <Kpi
          title="Orçamentos aprovados"
          value={data.quotes.filter((q) => q.status === "Aprovado").length}
          Icon={CheckCircle}
          plant={1}
        />
        <Kpi
          title="Em revisão"
          value={data.quotes.filter((q) => q.status === "Em análise").length}
          Icon={Clock}
          plant={2}
        />
        <Kpi
          title="Valor potencial"
          value={money(
            data.quotes
              .filter((q) => !["Aprovado", "Rejeitado"].includes(q.status))
              .reduce((s, q) => s + q.amount_cents, 0),
          )}
          Icon={DollarSign}
          plant={3}
        />
      </div>
      <div className="split quote-layout">
        <section className="panel quotes-panel">
          <AdminFilters
            search={search}
            onSearch={setSearch}
            placeholder="Buscar código, cliente ou serviço…"
            count={filtered.length}
            onClear={() => {
              setSearch("");
              setStatus("");
              setService("");
              setFrom("");
              setTo("");
            }}
            fields={[
              {
                label: "Status do orçamento",
                value: status,
                onChange: setStatus,
                options: filterOptions(
                  [
                    "Solicitado",
                    "Em análise",
                    "Enviado",
                    "Aprovado",
                    "Rejeitado",
                  ],
                  "Todos os status",
                ),
              },
              {
                label: "Serviço",
                value: service,
                onChange: setService,
                options: [
                  { value: "", label: "Todos os serviços" },
                  ...data.services.map((s) => ({
                    value: String(s.id),
                    label: s.name,
                  })),
                ],
              },
              {
                label: "Solicitado a partir de",
                value: from,
                onChange: setFrom,
                type: "date",
              },
              {
                label: "Solicitado até",
                value: to,
                onChange: setTo,
                type: "date",
              },
            ]}
          />
          <div className="table-scroll">
            <table className="dense-table quotes-table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Cliente</th>

                  <th>Valor estimado</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {!filtered.length && (
                  <tr>
                    <td colSpan={5}>
                      <Empty>
                        Nenhum orçamento encontrado. Ajuste ou limpe os filtros.
                      </Empty>
                    </td>
                  </tr>
                )}
                {filtered.slice((page - 1) * 10, page * 10).map((q) => (
                  <tr
                    key={q.id}
                    className={quote?.id === q.id ? "selected-row" : ""}
                    onClick={() => setSelected(q.id)}
                  >
                    <td>
                      ORC-{new Date(q.created_at).getFullYear()}-
                      {String(q.id).padStart(3, "0")}
                    </td>
                    <td>
                      {data.customers.find((c) => c.id === q.customer_id)?.name}
                    </td>

                    <td>{money(q.amount_cents)}</td>
                    <td>
                      <Status value={q.status} />
                    </td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label={`Detalhes do orçamento ${q.id}`}
                        onClick={() => setSelected(q.id)}
                      >
                        <MoreHorizontal size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Paginator total={filtered.length} page={page} setPage={setPage} />
        </section>
        {quote ? (
          <QuoteProfile quote={quote} />
        ) : (
          <Empty>Nenhum orçamento encontrado.</Empty>
        )}
      </div>
    </>
  );
}
export function QuoteProfile({ quote: q }: { quote: Quote }) {
  const { data, user, open, act, busy, reload } = useGreen();
  const client = data.customers.find((c) => c.id === q.customer_id),
    service = data.services.find((s) => s.id === q.service_id);
  return (
    <section className="panel quote-profile">
      <div className="section-heading">
        <h3>ORC-{String(q.id).padStart(3, "0")}</h3>
        <Status value={q.status} />
      </div>
      <h4>
        <Users size={17} />
        Informações do cliente
      </h4>
      <strong>{client?.name || user.name}</strong>
      <p className="muted inline">
        <CalendarDays size={13} />
        Solicitado em {dateLabel(q.created_at)}
      </p>
      <div className="panel-content">
        <p className="muted inline">
          <Mail size={13} />
          {client?.email || user.email}
        </p>
        <p className="muted inline">
          <Phone size={13} />
          {client?.phone || user.phone}
        </p>
        <p className="muted inline">
          <MapPin size={13} />
          {q.address}
        </p>
        <div className="quote-summary">
          <div>
            <h4>
              <Leaf size={17} />
              Tipo de serviço
            </h4>
            <span>{service?.name}</span>
          </div>
          <div>
            <h4>
              <Clock size={17} />
              Área
            </h4>
            <span>{q.area} m²</span>
          </div>
        </div>
        <h4>
          <FileText size={17} />
          Descrição do cliente
        </h4>
        <blockquote>
          {q.description || "Sem observações adicionais."}
        </blockquote>
        {q.brief?.width && (
          <div className="quote-plan-actions">
            <button
              className="button secondary small"
              onClick={() => open("landscape-view", q)}
            >
              <Ruler size={15} />
              Visualizar planejamento
            </button>
            {["Solicitado", "Em análise"].includes(q.status) && (
              <button
                className="text-button"
                onClick={() => open("landscape-studio", { quote: q, service })}
              >
                <Pencil size={15} />
                Editar levantamento
              </button>
            )}
          </div>
        )}
        <QuoteDocuments
          id={q.id}
          editable={["Solicitado", "Em análise"].includes(q.status)}
        />
        <Gallery
          entity="quotes"
          id={q.id}
          editable={
            user.role === "admin" ||
            ["Solicitado", "Em análise"].includes(q.status)
          }
          onChange={reload}
        />
        <div className="quote-summary">
          <div>
            <h4>
              <Leaf size={16} />
              Espécies sugeridas
            </h4>
            {q.plants.map((p, i) => {
              const s = data.species.find((s) => s.id === p.species_id);
              return s ? (
                <div className="mini-item" key={i}>
                  <Picture item={s} />
                  {s.name}
                </div>
              ) : null;
            })}
            {!q.plants.length && <span className="muted">A definir</span>}
          </div>
          <div>
            <h4>
              <Box size={16} />
              Materiais
            </h4>
            {q.materials.map((m, i) => (
              <div className="mini-item" key={i}>
                <Box size={16} />
                {m.name}
              </div>
            ))}
            {!q.materials.length && <span className="muted">A definir</span>}
          </div>
        </div>
        <p>
          Valor proposto:{" "}
          <strong>
            {q.amount_cents ? money(q.amount_cents) : "Em avaliação"}
          </strong>
        </p>
        {user.role === "admin" &&
          q.status !== "Aprovado" &&
          q.status !== "Rejeitado" && (
            <>
              <button
                className="button primary full"
                onClick={() => open("price-quote", q)}
              >
                <FileText size={19} />
                Gerar proposta <ArrowRight size={18} />
              </button>
              {q.status === "Solicitado" && (
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() =>
                    act(
                      `/quotes/${q.id}/status`,
                      { status: "Em análise" },
                      "PATCH",
                    )
                  }
                >
                  Iniciar análise
                </button>
              )}
            </>
          )}
        {q.status === "Enviado" && (
          <div className="row-actions">
            <button
              className="button primary"
              disabled={busy}
              onClick={() =>
                act(
                  `/quotes/${q.id}/approve`,
                  {},
                  "POST",
                  "Orçamento aprovado e projeto criado.",
                )
              }
            >
              <CheckCircle size={17} />
              Aprovar
            </button>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() =>
                act(`/quotes/${q.id}/status`, { status: "Rejeitado" }, "PATCH")
              }
            >
              Rejeitar
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

export function FinancePage() {
  const { data, open } = useGreen();
  const a = data.analytics;
  if (!a) return null;
  return (
    <>
      <PageTitle
        title="Financeiro"
        subtitle="Receitas, despesas e fluxo de caixa"
      >
        <Period />
        <button
          className="button secondary green-border"
          onClick={() => open("ledger", { direction: "Despesa" })}
        >
          <Plus size={20} />
          Nova despesa
        </button>
        <button
          className="button primary"
          onClick={() => open("ledger", { direction: "Receita" })}
        >
          <Plus size={20} />
          Nova receita
        </button>
      </PageTitle>
      <div className="kpis">
        <Kpi
          title="Receita do período"
          value={money(a.income)}
          Icon={BarChart3}
          change={a.growth}
        />
        <Kpi
          title="Despesas do período"
          value={money(a.expense)}
          Icon={TrendingDown}
          red
          plant={1}
        />
        <Kpi
          title="Lucro líquido"
          value={money(a.profit)}
          Icon={PieChart}
          plant={2}
          caption="Receitas recebidas menos despesas pagas"
        />
        <Kpi
          title="Inadimplência"
          value={money(a.overdue_income)}
          Icon={AlertCircle}
          red
          plant={3}
          caption="Contas a receber vencidas"
        />
      </div>
      <div className="split charts">
        <Panel
          title="Fluxo de caixa mensal"
          Icon={BarChart3}
          actions={
            <div className="chart-legend">
              <i className="green-dot" />
              Receitas <i className="red-dot" />
              Despesas <i className="line-dot" />
              Saldo
            </div>
          }
        >
          <CashChart financial />
        </Panel>
        <Panel title="Receitas por origem" Icon={PieChart}>
          <Donut
            values={a.origins}
            center={money(a.income)}
            subtitle="receita total"
          />
        </Panel>
      </div>
      <div className="split equal">
        <AccountTable title="Contas a receber" items={a.accounts_receivable} />
        <AccountTable title="Contas a pagar" items={a.accounts_payable} />
      </div>
    </>
  );
}
function AccountTable({ title, items }: { title: string; items: Ledger[] }) {
  const { open } = useGreen();
  const today = new Date().toLocaleDateString("sv-SE"),
    late = items.filter((i) => i.due_date < today),
    normal = items.filter((i) => i.due_date >= today);
  return (
    <Panel
      title={title}
      Icon={FileText}
      actions={
        <GoLink onClick={() => open("accounts", { items, title })}>
          Ver todas
        </GoLink>
      }
    >
      <div className="account-summary">
        <span>
          <strong>{normal.length}</strong> em aberto{" "}
          <b>{money(normal.reduce((s, i) => s + i.amount_cents, 0))}</b>
        </span>
        <span className="red">
          <strong>{late.length}</strong> em atraso{" "}
          <b>{money(late.reduce((s, i) => s + i.amount_cents, 0))}</b>
        </span>
      </div>
      <div className="table-scroll">
        <table className="dense-table accounts-table">
          <thead>
            <tr>
              <th>{title.includes("receber") ? "Cliente" : "Fornecedor"}</th>

              <th>Vencimento</th>
              <th>Valor</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.slice(0, 5).map((l, i) => (
              <tr key={l.id}>
                <td>{l.counterparty}</td>

                <td>{dateLabel(l.due_date)}</td>
                <td>{money(l.amount_cents)}</td>
                <td>
                  <Status
                    value={l.due_date < today ? "Atrasado" : "Pendente"}
                  />
                </td>
                <td>
                  <button
                    className="text-button"
                    onClick={() => open("pay-ledger", l)}
                  >
                    Baixar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

export function ProjectsPage() {
  const { data, search, setSearch, open, go, user } = useGreen();
  const [filter, setFilter] = useState("Todos");
  const [customer, setCustomer] = useState("");
  const filtered = data.projects.filter(
    (p) =>
      (filter === "Todos" || p.status === filter) &&
      (!customer || p.customer_id === Number(customer)) &&
      match(
        search,
        p.name,
        p.address,
        data.customers.find((c) => c.id === p.customer_id)?.name,
      ),
  );
  return (
    <>
      <PageTitle
        title="Projetos"
        subtitle="Planejamento, execução e acompanhamento do paisagismo"
      >
        {user.role === "admin" && (
          <button
            className="button primary"
            onClick={() => open("project-form")}
          >
            <Plus size={20} />
            Novo projeto
          </button>
        )}
      </PageTitle>
      {user.role === "admin" ? (
        <AdminFilters
          search={search}
          onSearch={setSearch}
          placeholder="Buscar projeto, endereço ou cliente…"
          count={filtered.length}
          onClear={() => {
            setSearch("");
            setFilter("Todos");
            setCustomer("");
          }}
          fields={[
            {
              label: "Etapa",
              value: filter === "Todos" ? "" : filter,
              onChange: (v) => setFilter(v || "Todos"),
              options: filterOptions(stages, "Todas as etapas"),
            },
            {
              label: "Cliente",
              value: customer,
              onChange: setCustomer,
              options: [
                { value: "", label: "Todos os clientes" },
                ...data.customers.map((c) => ({
                  value: String(c.id),
                  label: c.name,
                })),
              ],
            },
          ]}
        />
      ) : (
        <div className="tabs">
          {["Todos", ...stages].map((s) => (
            <button
              className={filter === s ? "selected" : ""}
              key={s}
              onClick={() => setFilter(s)}
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <div className="project-grid">
        {!filtered.length && (
          <Empty>Nenhum projeto encontrado. Ajuste ou limpe os filtros.</Empty>
        )}
        {filtered.map((p) => (
          <button
            className="project-card"
            key={p.id}
            onClick={() => go("project", p.id)}
          >
            <ProjectCover project={p} />
            <div>
              <Status value={p.status} />
              <h3>{p.name}</h3>
              <p>
                <MapPin size={14} />
                {p.address}
              </p>
              <div className="project-card-meta">
                <strong>{p.area} m²</strong>
                <strong>{money(p.budget_cents)}</strong>
              </div>
              <div className="progress">
                <i style={{ width: `${stages.indexOf(p.status) * 20}%` }} />
              </div>
              <span>
                Ver projeto <ArrowRight size={16} />
              </span>
            </div>
          </button>
        ))}
      </div>
    </>
  );
}
export function ProjectPage() {
  const { data, selectedId, user, go, open, act, busy, reload } = useGreen();
  const p = data.projects.find((p) => p.id === selectedId);
  const [tab, setTab] = useState("Espécies selecionadas");
  if (!p) return <Empty>Projeto não encontrado.</Empty>;
  const c = data.customers.find((c) => c.id === p.customer_id) || user;
  const tabs = [
    ["Visão geral", Home],
    ["Espécies selecionadas", Leaf],
    ["Materiais", Box],
    ["Serviços", Wrench],
    ["Cronograma", CalendarDays],
    ["Fotos", ImageIcon],
    ["Documentos", FileText],
    ["Planta 2D", Ruler],
    ...(user.role === "admin" ? [["Consumo", PackageOpen] as const] : []),
  ] as const;
  const index = stages.indexOf(p.status);
  return (
    <>
      <div className="detail-breadcrumb">
        <div>
          <button className="button secondary" onClick={() => go("projects")}>
            <ArrowLeft size={16} />
            Voltar para projetos
          </button>
          {user.role === "admin" && (
            <button
              className="button primary"
              onClick={() => open("project-form", p)}
            >
              <Pencil size={18} />
              Editar projeto
            </button>
          )}
        </div>
      </div>
      <PageTitle title={p.name} subtitle={p.description} />
      <div className="kpis project-kpis">
        <Kpi title="Cliente" value={c.name} Icon={Users} caption={c.email} />
        <Kpi
          title="Endereço"
          value={p.address.split(" · ")[0]}
          Icon={MapPin}
          caption={
            p.address.split(" · ").slice(1).join(" · ") ||
            "Local de execução do projeto"
          }
          plant={1}
        />
        <Kpi
          title="Área do projeto"
          value={`${p.area} m²`}
          Icon={Box}
          caption="Área do paisagismo"
          plant={2}
        />
        <Kpi
          title="Orçamento"
          value={money(p.budget_cents)}
          Icon={DollarSign}
          caption={p.status}
          plant={3}
        />
      </div>
      <div className="stage-flow">
        {stages.map((s, i) => {
          const Icon = [
            FileText,
            CheckCircle,
            ClipboardList,
            Wrench,
            Flag,
            Leaf,
          ][i];
          return (
            <button
              key={s}
              className={`${i < index ? "completed" : ""} ${i === index ? "current" : ""}`}
              disabled={user.role !== "admin" || i !== index + 1 || busy}
              onClick={() =>
                act(
                  `/projects/${p.id}/status`,
                  { status: s },
                  "PATCH",
                  "Etapa atualizada.",
                )
              }
            >
              <span>
                <Icon size={23} />
              </span>
              <strong>{s}</strong>
              <small>
                {i < index
                  ? "Concluído"
                  : i === index
                    ? "Em andamento"
                    : "Pendente"}
              </small>
            </button>
          );
        })}
      </div>
      <nav className="project-tabs">
        {tabs.map(([name, Icon]) => (
          <button
            key={name}
            className={tab === name ? "active" : ""}
            onClick={() => setTab(name)}
          >
            <Icon size={21} />
            {name}
          </button>
        ))}
      </nav>
      {tab === "Espécies selecionadas" && (
        <Panel
          title={`Espécies selecionadas (${p.plants.length})`}
          actions={
            user.role === "admin" ? (
              <button
                className="button primary"
                onClick={() => open("project-form", p)}
              >
                <Plus size={18} />
                Adicionar espécie
              </button>
            ) : undefined
          }
        >
          <p className="panel-subtitle">
            Plantas definidas para este projeto de paisagismo.
          </p>
          <div className="table-scroll">
            <table className="dense-table species-table">
              <thead>
                <tr>
                  <th>Nome popular</th>

                  <th>Quantidade</th>
                  <th>Aplicação</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {p.plants.map((plant, i) => {
                  const s = data.species.find((s) => s.id === plant.species_id);
                  return s ? (
                    <tr key={i}>
                      <td>
                        <span className="cell-product">
                          <Picture item={s} />
                          <span title={s.name}>{s.name}</span>
                        </span>
                      </td>

                      <td>{plant.quantity} unidades</td>
                      <td>{plant.application || s.use}</td>
                      <td>
                        <button
                          className="icon-button bordered"
                          aria-label={`Detalhes de ${s.name}`}
                          onClick={() => open("species-detail", s)}
                        >
                          <MoreHorizontal size={16} />
                        </button>
                      </td>
                    </tr>
                  ) : null;
                })}
              </tbody>
            </table>
          </div>
          {!p.plants.length && (
            <Empty>As espécies serão definidas no planejamento.</Empty>
          )}
        </Panel>
      )}
      {tab === "Visão geral" && (
        <Panel title="Visão geral do projeto">
          <p>{p.description}</p>
          <div className="overview-grid">
            <div>
              <h3>Período previsto</h3>
              <p>
                {dateLabel(p.start_date)} a {dateLabel(p.end_date)}
              </p>
            </div>
            <div>
              <h3>Espécies e plantas</h3>
              <p>
                {p.plants.length} espécies ·{" "}
                {p.plants.reduce((n, s) => n + s.quantity, 0)} plantas
              </p>
            </div>
            <div>
              <h3>Custos planejados</h3>
              <p>
                {money(
                  [...p.materials, ...p.services].reduce(
                    (n, c) => n + c.quantity * c.unit_price_cents,
                    0,
                  ),
                )}
              </p>
            </div>
          </div>
          <ProjectHistory id={p.id} />
        </Panel>
      )}
      {(tab === "Materiais" || tab === "Serviços") && (
        <Panel
          title={tab}
          Icon={tab === "Materiais" ? Box : Wrench}
          actions={
            user.role === "admin" ? (
              <button
                className="button primary"
                onClick={() => open("project-form", p)}
              >
                <Plus size={18} />
                Adicionar {tab.toLowerCase()}
              </button>
            ) : undefined
          }
        >
          <div className="table-scroll">
            <table className="dense-table costs-table">
              <thead>
                <tr>
                  <th>Descrição</th>
                  <th>Quantidade</th>

                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {(tab === "Materiais" ? p.materials : p.services).map(
                  (m, i) => (
                    <tr key={i}>
                      <td>{m.name}</td>
                      <td>{m.quantity}</td>

                      <td>{money(m.unit_price_cents * m.quantity)}</td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
      {tab === "Cronograma" && (
        <Panel
          title="Cronograma"
          Icon={CalendarDays}
          actions={
            user.role === "admin" ? (
              <button
                className="button secondary"
                onClick={() => open("project-form", p)}
              >
                Editar cronograma
              </button>
            ) : undefined
          }
        >
          {p.tasks.map((t, i) => (
            <div className="schedule-row" key={i}>
              <span className="round-icon small">
                {t.done ? <Check size={18} /> : <CalendarDays size={18} />}
              </span>
              <strong>{t.title}</strong>
              <span>{dateLabel(t.date)}</span>
              <Status value={t.done ? "Concluído" : "Pendente"} />
            </div>
          ))}
          {!p.tasks.length && <Empty>Cronograma em definição.</Empty>}
        </Panel>
      )}
      {tab === "Fotos" && (
        <Panel title="Fotos do projeto" Icon={ImageIcon}>
          {p.reference_image_url && (
            <figure className="project-reference">
              <img
                src={p.reference_image_url}
                alt={`Referência visual — ${p.name}`}
              />
              <figcaption>{p.reference_image_note}</figcaption>
            </figure>
          )}
          <Gallery
            entity="projects"
            id={p.id}
            editable={user.role === "admin"}
            onChange={reload}
          />
        </Panel>
      )}
      {tab === "Documentos" && <ProjectDocuments project={p} />}
      {tab === "Planta 2D" && <ProjectPlan project={p} />}
      {tab === "Consumo" && user.role === "admin" && (
        <ProjectUsage project={p} />
      )}
    </>
  );
}
function ProjectHistory({ id }: { id: number }) {
  const [events, setEvents] = useState<
    { id: number; status: string; created_at: string }[]
  >([]);
  useEffect(() => {
    api<typeof events>(`/projects/${id}/events`)
      .then(setEvents)
      .catch(() => {});
  }, [id]);
  return (
    <>
      <h3>Histórico de etapas</h3>
      {events.map((e) => (
        <div className="detail-link" key={e.id}>
          <Status value={e.status} />
          <span>{dateLabel(e.created_at)}</span>
        </div>
      ))}
    </>
  );
}
function ProjectDocuments({ project }: { project: Project }) {
  const { user, toast } = useGreen();
  const [docs, setDocs] = useState<
      { id: number; name: string; created_at: string }[]
    >([]),
    [busy, setBusy] = useState(false);
  const load = () =>
    api<typeof docs>(`/projects/${project.id}/documents`).then(setDocs);
  useEffect(() => {
    load().catch((e) => toast(e.message));
  }, [project.id]);
  async function upload(file: File) {
    setBusy(true);
    try {
      const f = new FormData();
      f.append("file", file);
      await api(`/projects/${project.id}/documents`, {
        method: "POST",
        body: f,
      });
      await load();
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function download(id: number, name: string) {
    const res = await fetch(`/api/documents/${id}/content`, {
      headers: {
        Authorization: `Bearer ${sessionStorage.getItem("greenscape-token")}`,
      },
    });
    if (!res.ok) {
      toast("Documento indisponível.");
      return;
    }
    const url = URL.createObjectURL(await res.blob()),
      link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <Panel
      title="Documentos"
      Icon={FileText}
      actions={
        user.role === "admin" ? (
          <label className="button primary">
            <Plus size={17} />
            {busy ? "Enviando…" : "Adicionar PDF"}
            <input
              hidden
              type="file"
              accept="application/pdf"
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) upload(f);
              }}
            />
          </label>
        ) : undefined
      }
    >
      {docs.map((d) => (
        <div className="detail-link" key={d.id}>
          <FileText size={20} />
          <strong>{d.name}</strong>
          <span>{dateLabel(d.created_at)}</span>
          <button
            className="text-button"
            onClick={() => download(d.id, d.name)}
          >
            <Download size={17} />
            Baixar
          </button>
          {user.role === "admin" && (
            <button
              className="text-button red-text"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api(`/documents/${d.id}`, { method: "DELETE" });
                  await load();
                } catch (e) {
                  toast((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Excluir
            </button>
          )}
        </div>
      ))}
      {!docs.length && <Empty>Nenhum documento anexado.</Empty>}
      <p className="muted small">
        PDF · até 10 MB · acesso restrito ao cliente e administrador.
      </p>
    </Panel>
  );
}

export function ReportsPage() {
  const { data, open } = useGreen();
  const a = data.analytics;
  return (
    <>
      <PageTitle
        title="Relatórios"
        subtitle="Indicadores e exportações da operação"
      >
        <Period />
        <button
          className="button secondary"
          onClick={() => open("data-quality")}
        >
          <CheckCircle size={17} />
          Consistência dos dados
        </button>
        <button className="button secondary" onClick={() => open("audit")}>
          <ClipboardList size={18} />
          Histórico de alterações
        </button>
      </PageTitle>
      <div className="kpis">
        <Kpi
          title="Receitas recebidas"
          value={money(a?.income || 0)}
          Icon={BarChart3}
        />
        <Kpi
          title="Despesas pagas"
          value={money(a?.expense || 0)}
          Icon={TrendingDown}
          plant={1}
        />
        <Kpi
          title="Clientes recorrentes"
          value={a?.customers_recurring || 0}
          Icon={Users}
          plant={2}
        />
        <Kpi
          title="Ticket médio"
          value={money(a?.average_ticket || 0)}
          Icon={ShoppingCart}
          plant={3}
        />
      </div>
      <Panel title="Exportar relatórios" Icon={FileText}>
        <div className="report-grid">
          {[
            {
              name: "Vendas e pedidos",
              headers: [
                "Pedido",
                "Data",
                "Cliente",
                "Status",
                "Total centavos",
              ],
              rows: data.orders.map((o) => [
                o.id,
                o.created_at,
                data.customers.find((c) => c.id === o.customer_id)?.name,
                o.status,
                o.total_cents,
              ]),
            },
            {
              name: "Estoque e produtos",
              headers: ["SKU", "Produto", "Categoria", "Saldo", "Mínimo"],
              rows: data.products.map((p) => [
                p.sku,
                p.name,
                p.category,
                p.stock,
                p.low_stock,
              ]),
            },
            {
              name: "Financeiro completo",
              headers: [
                "Tipo",
                "Origem",
                "Descrição",
                "Vencimento",
                "Valor centavos",
                "Status",
                "Pagamento",
              ],
              rows: data.ledger.map((l) => [
                l.direction,
                l.source,
                l.description,
                l.due_date,
                l.amount_cents,
                l.status,
                l.paid_date,
              ]),
            },
            {
              name: "Projetos de paisagismo",
              headers: [
                "Projeto",
                "Cliente",
                "Área",
                "Orçamento centavos",
                "Status",
              ],
              rows: data.projects.map((p) => [
                p.name,
                data.customers.find((c) => c.id === p.customer_id)?.name,
                p.area,
                p.budget_cents,
                p.status,
              ]),
            },
          ].map((report) => (
            <button
              className="report-card"
              key={report.name}
              onClick={() =>
                exportCSV(report.name, report.headers, report.rows)
              }
            >
              <Download size={26} />
              <h3>{report.name}</h3>
              <span>
                Exportar CSV <ArrowRight size={15} />
              </span>
            </button>
          ))}
        </div>
        <p className="muted">
          As exportações incluem o histórico completo. Os indicadores acima
          respeitam o período selecionado.
        </p>
      </Panel>
    </>
  );
}
export function SettingsPage() {
  const { data, reload, toast } = useGreen();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <>
      <PageTitle
        title="Configurações"
        subtitle="Dados da empresa e alertas da operação"
      />
      <Panel title="Sua empresa" Icon={Settings}>
        <form
          className="form"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            const f = new FormData(e.currentTarget);
            try {
              await write(
                "/settings",
                {
                  name: f.get("name"),
                  email: f.get("email"),
                  phone: f.get("phone"),
                  address: f.get("address"),
                  low_stock_alert: f.has("low_stock_alert"),
                  quote_alert: f.has("quote_alert"),
                },
                "PUT",
              );
              await reload();
              toast("Configurações salvas.");
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <div className="form-grid">
            {[
              ["name", "Nome da empresa"],
              ["email", "E-mail"],
              ["phone", "Telefone"],
              ["address", "Endereço"],
            ].map(([key, label]) => (
              <label key={key}>
                {label}
                <input
                  name={key}
                  type={key === "email" ? "email" : "text"}
                  defaultValue={String(data.settings[key] || "")}
                  required={key === "name"}
                />
              </label>
            ))}
          </div>
          <h3>Alertas no sistema</h3>
          <label className="checkbox-label">
            <input
              type="checkbox"
              name="low_stock_alert"
              defaultChecked={data.settings.low_stock_alert !== false}
            />
            Mostrar alertas de estoque baixo
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              name="quote_alert"
              defaultChecked={data.settings.quote_alert !== false}
            />
            Mostrar novos pedidos de orçamento
          </label>
          {error && <p className="error">{error}</p>}
          <div className="form-footer">
            <span>As preferências controlam o painel de notificações.</span>
            <SaveButton busy={busy} />
          </div>
        </form>
        <AdminAISettings />
        <RafinhaSettings />
      </Panel>
    </>
  );
}
