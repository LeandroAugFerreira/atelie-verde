import { useCallback, useEffect, useRef, useState } from "react";
import {
  Home,
  Truck,
  PackageOpen,
  Users,
  Leaf,
  FileText,
  Folder,
  BarChart3,
  PieChart,
  Settings,
  Search,
  Bell,
  ChevronDown,
  ShoppingCart,
  Plus,
  LogOut,
  Menu,
  X,
  ArrowRight,
  Trash2,
  Check,
  CalendarDays,
  Sprout,
  Image as ImageIcon,
  MessageCircle,
} from "lucide-react";
import { api, ApiError, setToken, write } from "./api";
import { Green, useGreen, type Page } from "./context";
import { Logo, Sprite, Avatar, Picture, Status } from "./ReferenceUI";
import { Modal, Empty, Gallery, SaveButton } from "./components";
import { EntityForm, ProjectForm, QuoteForm } from "./Forms";
import {
  AppointmentForm,
  LedgerForm,
  AdminQuoteForm,
} from "./OperationalForms";
import {
  DashboardPage,
  InventoryPage,
  CustomersPage,
  ServicesPage,
  QuotesPage,
  FinancePage,
  ProjectsPage,
  ProjectPage,
  ReportsPage,
  SettingsPage,
} from "./AdminPages";
import {
  HomePage,
  CatalogPage,
  ProductPage,
  ClientServicesPage,
  ClientQuotesPage,
  ClientHistoryPage,
  LibraryPage,
} from "./ClientPages";
import {
  money,
  dateLabel,
  type AppData,
  type User,
  type Product,
  type Quote,
} from "./types";

import { LearningPage } from "./LearningPage";
import { RafinhaAssistant, askRafinha } from "./RafinhaAssistant";
import { ProfileForm } from "./ProfileForm";
import { SpeciesDetail } from "./BotanicalDetails";
import { MovementDetails } from "./RecordDetails";
import { DataQuality } from "./DataQuality";
import { ServiceDetailPage } from "./ServiceDetail";
import { NavigationBreadcrumb } from "./NavigationBreadcrumb";
import { LandscapeStudio } from "./LandscapeStudio";
import { QuoteDocuments } from "./QuoteDocuments";
import { LandscapeOverview } from "./ProjectPlan";
import { SuppliersPage, AuditHistory, StockHistory } from "./CommercialPages";
import {
  CommercialPartyForm,
  CommercialProductForm,
  CommercialStockForm,
} from "./CommercialForms";

const initial: AppData = {
  products: [],
  species: [],
  services: [],
  projects: [],
  quotes: [],
  orders: [],
  customers: [],
  suppliers: [],
  moves: [],
  appointments: [],
  ledger: [],
  reviews: [],
  favorites: [],
  analytics: null,
  settings: {},
  articles: [],
  learningProgress: [],
};
const adminNav = [
  ["dashboard", "Dashboard", Home],
  ["inventory", "Estoque", PackageOpen],
  ["suppliers", "Fornecedores", Truck],
  ["customers", "Clientes", Users],
  ["services", "Serviços", Leaf],
  ["quotes", "Orçamentos", FileText],
  ["projects", "Projetos", Folder],
  ["finance", "Financeiro", BarChart3],
  ["reports", "Relatórios", PieChart],
  ["settings", "Configurações", Settings],
] as const;
function Login({
  onLogin,
  notice,
}: {
  onLogin: (u: User) => void;
  notice?: string;
}) {
  const [register, setRegister] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function login(body: unknown, newUser = false) {
    setBusy(true);
    setError("");
    try {
      const response = await write<{ access_token: string; user: User }>(
        `/auth/${newUser ? "register" : "login"}`,
        body,
      );
      setToken(response.access_token);
      onLogin(response.user);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-layout">
      <div className="login-visual">
        <Sprite name="hero" />
        <div className="login-shade" />
        <div className="login-story">
          <Logo standalone />
          <h1>
            Mais verde
            <br />
            para a sua vida.
          </h1>
        </div>
        <p className="login-caption">
          Da primeira planta ao jardim dos sonhos.
          <br />
          Tudo cresce melhor quando está conectado.
        </p>
      </div>
      <div className="login-form">
        <Logo standalone />
        <h2>
          {register ? "Crie seu espaço verde" : "Bem-vindo ao Ateliê Verde"}
        </h2>
        <p>
          Entre para comprar, acompanhar projetos ou gerenciar sua operação.
        </p>
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            login(Object.fromEntries(new FormData(e.currentTarget)), register);
          }}
        >
          {notice && (
            <p className="notice" role="status">
              {notice}
            </p>
          )}
          {register && (
            <label>
              Nome completo
              <input name="name" autoComplete="name" required minLength={2} />
            </label>
          )}
          <label>
            E-mail
            <input name="email" type="email" autoComplete="username" required />
          </label>
          <label>
            Senha
            <input
              name="password"
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              required
              minLength={register ? 10 : undefined}
            />
          </label>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <SaveButton busy={busy} label={register ? "Criar conta" : "Entrar"} />
        </form>
        <button className="text-button" onClick={() => setRegister(!register)}>
          {register ? "Já tenho uma conta" : "Criar uma conta de cliente"}
        </button>
        <div className="demo-login">
          <span>Explore a demonstração</span>
          <div>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() =>
                login({
                  email: "admin@atelieverde.local",
                  password: "AtelieVerde@2026",
                })
              }
            >
              Administrador <ArrowRight size={16} />
            </button>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() =>
                login({
                  email: "cliente@atelieverde.local",
                  password: "AtelieVerde@2026",
                })
              }
            >
              Cliente <ArrowRight size={16} />
            </button>
          </div>
          <small>Dados fictícios · nenhuma cobrança online</small>
        </div>
      </div>
    </div>
  );
}
export default function App() {
  const reloadVersion = useRef(0),
    reloadAbort = useRef<AbortController | null>(null),
    checkoutAttempt = useRef({ fingerprint: "", key: "" });
  const [user, setUser] = useState<User | null>(null),
    [checking, setChecking] = useState(true),
    [bootError, setBootError] = useState(""),
    [data, setData] = useState(initial),
    [page, setPage] = useState<Page>("dashboard"),
    [selectedId, setSelectedId] = useState<number | null>(null),
    [search, setSearch] = useState(""),
    [modal, setModal] = useState<{ kind: string; item?: any } | null>(null),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [toastText, setToast] = useState(""),
    [mobile, setMobile] = useState(false),
    [userMenu, setUserMenu] = useState(false),
    [notifications, setNotifications] = useState(false),
    [cart, setCart] = useState<Record<number, number>>({});
  const today = new Date().toLocaleDateString("sv-SE");
  const [period, setPeriod] = useState({
    start: today.slice(0, 8) + "01",
    end: today,
  });
  const isAdmin = user?.role === "admin";
  const go = useCallback((next: Page, id?: number) => {
    setPage(next);
    setSelectedId(id ?? null);
    setSearch("");
    setMobile(false);
    setUserMenu(false);
    setModal(null);
    document
      .querySelectorAll(
        ".page-canvas, .panel, .catalog-grid, .shop-home-content, .client-inner",
      )
      .forEach((el) => el.scrollTo(0, 0));
  }, []);
  const open = useCallback((kind: string, item?: any) => {
    setError("");
    setModal(kind ? { kind, item } : null);
  }, []);
  const close = useCallback(() => setModal(null), []);
  useEffect(() => {
    const ask = () => setModal(null);
    window.addEventListener("atelie-ask-rafinha", ask);
    return () => window.removeEventListener("atelie-ask-rafinha", ask);
  }, []);
  useEffect(() => {
    api<User>("/auth/me")
      .then((u) => {
        setUser(u);
        setPage(u.role === "admin" ? "dashboard" : "home");
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 0) setBootError(e.message);
        else setToken("");
      })
      .finally(() => setChecking(false));
  }, []);
  const reload = useCallback(async () => {
    if (!user) return;
    const version = ++reloadVersion.current;
    reloadAbort.current?.abort();
    const controller = new AbortController();
    reloadAbort.current = controller;
    setLoading(true);
    try {
      const paths = [
        "/species",
        "/services",
        "/projects",
        "/quotes",
        "/orders",
        "/appointments",
        "/reviews",
        "/favorites",
        ...(isAdmin
          ? [
              "/admin/products",
              "/customers",
              "/stock-moves",
              "/ledger",
              `/analytics?start=${period.start}&end=${period.end}`,
              "/settings",
              "/suppliers",
            ]
          : ["/products"]),
        "/learning",
        "/learning/progress",
      ];
      const r = await Promise.all(
        paths.map((p) => api<any>(p, { signal: controller.signal })),
      );
      if (version !== reloadVersion.current || controller.signal.aborted)
        return;
      setError("");
      setData({
        ...initial,
        species: r[0],
        services: r[1],
        projects: r[2],
        quotes: r[3],
        orders: r[4],
        appointments: r[5],
        reviews: r[6],
        favorites: r[7],
        products: r[8],
        customers: isAdmin ? r[9] : [user],
        moves: isAdmin ? r[10] : [],
        ledger: isAdmin ? r[11] : [],
        analytics: isAdmin ? r[12] : null,
        settings: isAdmin ? r[13] : {},
        suppliers: isAdmin ? r[14] : [],
        articles: r[r.length - 2],
        learningProgress: r[r.length - 1],
      });
    } catch (e) {
      if (version !== reloadVersion.current || controller.signal.aborted)
        return;
      setError((e as Error).message);
    } finally {
      if (version === reloadVersion.current) setLoading(false);
    }
  }, [user, isAdmin, period.start, period.end]);
  useEffect(() => {
    reload();
    return () => {
      reloadAbort.current?.abort();
    };
  }, [reload]);
  useEffect(() => {
    const expired = () => {
      logout();
      setToast("Sua sessão expirou. Entre novamente para continuar.");
    };
    window.addEventListener("atelie-session-expired", expired);
    return () => window.removeEventListener("atelie-session-expired", expired);
  }, []);
  useEffect(() => {
    if (toastText) {
      const timer = setTimeout(() => setToast(""), 5500);
      return () => clearTimeout(timer);
    }
  }, [toastText]);
  async function act(
    path: string,
    body: unknown = {},
    method = "POST",
    message = "Alteração salva.",
  ) {
    setBusy(true);
    setError("");
    try {
      await write(path, body, method);
      await reload();
      setToast(message);
      setModal(null);
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  const saved = async () => {
    await reload();
    setModal(null);
    setToast("Cadastro salvo com sucesso.");
  };
  function addCart(p: Product, quantity = 1) {
    if ((cart[p.id] || 0) + quantity > p.stock) {
      setToast("A quantidade excede o estoque disponível.");
      return;
    }
    setCart({ ...cart, [p.id]: (cart[p.id] || 0) + quantity });
    setToast(`${p.name} adicionado ao carrinho.`);
  }
  async function favorite(id: number) {
    try {
      await api(`/favorites/${id}`, {
        method: data.favorites.includes(id) ? "DELETE" : "POST",
      });
      await reload();
    } catch (e) {
      setToast((e as Error).message);
    }
  }
  function logout() {
    ++reloadVersion.current;
    reloadAbort.current?.abort();
    checkoutAttempt.current = { fingerprint: "", key: "" };
    setToken("");
    setToast("");
    setLoading(false);
    setNotifications(false);
    setMobile(false);
    setUser(null);
    setData(initial);
    setCart({});
    setModal(null);
    setUserMenu(false);
    setSearch("");
    setError("");
  }
  if (checking)
    return (
      <div className="app-loading">
        <Leaf size={34} />
        <span>Preparando seu espaço verde…</span>
      </div>
    );
  if (!user && bootError)
    return (
      <div className="app-loading" role="alert">
        <Leaf size={34} />
        <h2>Não foi possível conectar</h2>
        <p>{bootError}</p>
        <button
          className="button primary"
          onClick={() => window.location.reload()}
        >
          Tentar novamente
        </button>
      </div>
    );
  if (!user)
    return (
      <Login
        notice={toastText}
        onLogin={(u) => {
          setToast("");
          setUser(u);
          setPage(u.role === "admin" ? "dashboard" : "home");
        }}
      />
    );
  const alerts = [
    ...(data.settings.low_stock_alert !== false
      ? data.products
          .filter((p) => p.active && p.stock <= p.low_stock)
          .map((p) => ({
            text: `${p.name}: ${p.stock} unidades`,
            page: "inventory" as Page,
          }))
      : []),
    ...(data.settings.quote_alert !== false
      ? data.quotes
          .filter((q) => q.status === "Solicitado")
          .map((q) => ({
            text: `Novo orçamento #${q.id}`,
            page: "quotes" as Page,
          }))
      : []),
  ];
  const cartCount = Object.values(cart).reduce((n, q) => n + q, 0),
    cartTotal = Object.entries(cart).reduce(
      (n, [id, q]) =>
        n +
        (data.products.find((p) => p.id === Number(id))?.price_cents || 0) * q,
      0,
    );
  const pageView = isAdmin
    ? (
        {
          dashboard: <DashboardPage />,
          products: <InventoryPage productsOnly />,
          suppliers: <SuppliersPage />,
          inventory: <InventoryPage />,
          customers: <CustomersPage />,
          services: <ServicesPage />,
          quotes: <QuotesPage />,
          projects: <ProjectsPage />,
          project: <ProjectPage />,
          finance: <FinancePage />,
          reports: <ReportsPage />,
          settings: <SettingsPage />,
          species: <LibraryPage />,
        } as Partial<Record<Page, React.ReactNode>>
      )[page]
    : (
        {
          home: <HomePage />,
          catalog: <CatalogPage key={selectedId} />,
          product: <ProductPage key={selectedId} />,
          services: <ClientServicesPage />,
          "service-detail": <ServiceDetailPage />,
          quotes: <ClientQuotesPage />,
          projects: (
            <div className="client-inner">
              <ProjectsPage />
            </div>
          ),
          project: (
            <div className="client-inner">
              <ProjectPage />
            </div>
          ),
          history: <ClientHistoryPage />,
          learn: <LearningPage />,
          species: (
            <div className="client-inner">
              <LibraryPage />
            </div>
          ),
        } as Partial<Record<Page, React.ReactNode>>
      )[page];
  return (
    <Green.Provider
      value={{
        user,
        data,
        page,
        go,
        open,
        act,
        reload,
        busy,
        search,
        setSearch,
        cart,
        setCart,
        addCart,
        favorite,
        period,
        setPeriod,
        selectedId,
        toast: setToast,
      }}
    >
      <div className={`app ${isAdmin ? "admin-app" : "client-app"}`}>
        {isAdmin && (
          <>
            {mobile && (
              <div
                className="sidebar-backdrop"
                onClick={() => setMobile(false)}
              />
            )}
            <aside className={`admin-sidebar ${mobile ? "open" : ""}`}>
              <div className="sidebar-decoration" aria-hidden="true">
                <img src="/decor/sidebar-foliage.png" alt="" />
              </div>
              <Logo dark />
              <nav>
                {adminNav.map(([key, label, Icon]) => (
                  <button
                    key={key}
                    className={
                      page === key || (page === "project" && key === "projects")
                        ? "active"
                        : ""
                    }
                    onClick={() => go(key)}
                  >
                    <Icon size={25} />
                    {label}
                  </button>
                ))}
              </nav>
              <div className="sidebar-poster">
                <span>
                  Natureza
                  <br />
                  também é<br />
                  bem-estar
                </span>
              </div>
            </aside>
          </>
        )}
        <header className="app-header">
          {isAdmin ? (
            <>
              <button
                className="icon-button mobile-toggle"
                aria-label="Abrir menu"
                onClick={() => setMobile(!mobile)}
              >
                <Menu />
              </button>
              <label className="system-search">
                <Search size={21} />
                <input
                  placeholder="Buscar no sistema…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </label>
              <div className="header-spacer" />
              <div className="notification-control">
                <button
                  className="icon-button"
                  aria-label="Notificações"
                  onClick={() => setNotifications(!notifications)}
                >
                  <Bell size={25} />
                  {alerts.length > 0 && <i />}
                </button>
                {notifications && (
                  <div className="dropdown notifications">
                    <strong>Notificações ({alerts.length})</strong>
                    {alerts.slice(0, 8).map((a, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          go(a.page);
                          setNotifications(false);
                        }}
                      >
                        <Leaf size={15} />
                        {a.text}
                      </button>
                    ))}
                    {!alerts.length && (
                      <p className="muted">Tudo em dia por aqui.</p>
                    )}
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <button className="logo-link" onClick={() => go("home")}>
                <Logo standalone />
              </button>
              <nav className="client-nav">
                {[
                  ["home", "Loja"],
                  ["catalog", "Produtos"],
                  ["services", "Serviços"],
                  ["projects", "Projetos"],
                  ["learn", "Aprender"],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    className={
                      page === key ||
                      (page === "product" && key === "catalog") ||
                      (page === "service-detail" && key === "services")
                        ? "active"
                        : ""
                    }
                    onClick={() => go(key as Page)}
                  >
                    {label}
                  </button>
                ))}
              </nav>
              <label className="system-search">
                <Search size={21} />
                <input
                  placeholder="Buscar plantas, vasos, serviços…"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    if (page === "home") setPage("catalog");
                  }}
                />
              </label>
              <button
                className="header-cart"
                aria-label={`Carrinho com ${cartCount} itens`}
                onClick={() => open("cart")}
              >
                <ShoppingCart size={29} />
                {cartCount > 0 && <span>{cartCount}</span>}
              </button>
            </>
          )}
          <div className="header-user">
            <button
              onClick={() => setUserMenu(!userMenu)}
              aria-label="Abrir menu da conta"
            >
              <Avatar name={user.name} url={user.avatar_url} />
              <span>
                <strong>
                  {isAdmin
                    ? "Administrador"
                    : `Olá, ${user.name.split(" ")[0]}`}
                </strong>
                <small>{isAdmin ? user.email : "Cliente"}</small>
              </span>
              <ChevronDown size={16} />
            </button>
            {userMenu && (
              <div className="dropdown user-dropdown">
                <button
                  onClick={() => {
                    setUserMenu(false);
                    open("profile");
                  }}
                >
                  <Users size={17} />
                  Editar Perfil
                </button>
                {!isAdmin && (
                  <>
                    <button
                      onClick={() => {
                        setUserMenu(false);
                        askRafinha();
                      }}
                    >
                      <MessageCircle size={17} />
                      Rafinha · preferências e conversa
                    </button>
                    <button onClick={() => go("quotes")}>
                      <FileText size={17} />
                      Meus orçamentos
                    </button>
                    <button onClick={() => go("history")}>
                      <CalendarDays size={17} />
                      Histórico de compras
                    </button>
                    <button onClick={() => go("species")}>
                      <Sprout size={17} />
                      Biblioteca de espécies
                    </button>
                  </>
                )}
                <button onClick={logout}>
                  <LogOut size={17} />
                  Sair
                </button>
              </div>
            )}
          </div>
        </header>
        <main className={isAdmin ? "admin-content" : "client-content"}>
          {loading && <div className="loading-line" />}
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button className="text-button" onClick={reload}>
                Atualizar
              </button>
              <button
                className="icon-button"
                aria-label="Fechar aviso"
                onClick={() => setError("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {(!isAdmin || page === "species") && <NavigationBreadcrumb />}
          <section
            className={`page-canvas page-${page}`}
            aria-label="Conteúdo da página"
            tabIndex={0}
          >
            {pageView || <Empty>Escolha uma área no menu.</Empty>}
            {isAdmin && page === "products" && (
              <div className="library-shortcut">
                <button className="text-button" onClick={() => go("species")}>
                  <Sprout size={18} />
                  Abrir biblioteca de espécies
                </button>
                <button
                  className="text-button"
                  onClick={() => open("entity", { entity: "species" })}
                >
                  <Plus size={17} />
                  Nova espécie
                </button>
              </div>
            )}
          </section>
        </main>
        {!isAdmin && (
          <RafinhaAssistant key={user.id} blocked={!!modal || mobile} />
        )}
        {toastText && (
          <div className="toast" role="status">
            <Check size={18} />
            {toastText}
          </div>
        )}
        {modal && (
          <Modal
            title={modalTitle(modal)}
            wide={[
              "project-form",
              "agenda",
              "moves",
              "accounts",
              "price-quote",
              "landscape-studio",
              "landscape-view",
            ].includes(modal.kind)}
            onClose={close}
          >
            {modal.kind === "profile" && (
              <ProfileForm
                user={user}
                onChange={setUser}
                onSaved={(u) => {
                  setUser(u);
                  close();
                  setToast("Perfil atualizado.");
                }}
              />
            )}
            {modal.kind === "entity" &&
              (modal.item.entity === "products" ? (
                <CommercialProductForm
                  item={modal.item.record}
                  species={data.species}
                  suppliers={data.suppliers}
                  onSaved={saved}
                />
              ) : ["customers", "suppliers"].includes(modal.item.entity) ? (
                <CommercialPartyForm
                  kind={modal.item.entity}
                  item={modal.item.record}
                  onSaved={saved}
                />
              ) : (
                <EntityForm
                  kind={modal.item.entity}
                  item={modal.item.record}
                  species={data.species}
                  onSaved={saved}
                />
              ))}
            {modal.kind === "project-form" && (
              <ProjectForm
                item={modal.item}
                customers={data.customers}
                species={data.species}
                onSaved={saved}
              />
            )}
            {modal.kind === "appointment" && (
              <AppointmentForm item={modal.item} />
            )}
            {modal.kind === "ledger" && (
              <LedgerForm direction={modal.item.direction} />
            )}
            {modal.kind === "admin-quote" && <AdminQuoteForm />}
            {modal.kind === "price-quote" && (
              <PriceQuoteForm quote={modal.item} />
            )}
            {modal.kind === "quote-form" && (
              <QuoteForm
                services={data.services.filter((s) => s.active)}
                selectedService={modal.item?.id}
                onSaved={async (id) => {
                  await reload();
                  open("quote-photos", { id });
                  setToast("Orçamento solicitado. Adicione fotos do local.");
                }}
              />
            )}
            {modal.kind === "landscape-studio" && (
              <LandscapeStudio
                service={modal.item?.service}
                quote={modal.item?.quote}
                project={modal.item?.project}
              />
            )}
            {modal.kind === "landscape-view" && (
              <div className="detail">
                <LandscapeOverview record={modal.item} />
              </div>
            )}
            {modal.kind === "quote-photos" && (
              <div className="detail">
                <Gallery
                  entity="quotes"
                  id={modal.item.id}
                  editable
                  onChange={reload}
                />
                <QuoteDocuments id={modal.item.id} editable />
                <button className="button primary" onClick={() => go("quotes")}>
                  Acompanhar orçamento
                </button>
              </div>
            )}
            {modal.kind === "stock" && (
              <CommercialStockForm item={modal.item} />
            )}
            {modal.kind === "project-consumption" && (
              <CommercialStockForm project={modal.item} />
            )}
            {modal.kind === "audit" && <AuditHistory />}
            {modal.kind === "data-quality" && <DataQuality />}
            {modal.kind === "movement-detail" && (
              <MovementDetails record={modal.item} />
            )}
            {modal.kind === "cart" && (
              <div className="detail">
                {cartCount > 0 ? (
                  <>
                    <div className="cart-lines">
                      {Object.entries(cart).map(([id, q]) => {
                        const p = data.products.find(
                          (p) => p.id === Number(id),
                        );
                        return p ? (
                          <div className="cart-line" key={id}>
                            <Picture item={p} />
                            <div>
                              <strong>{p.name}</strong>
                              <small>{money(p.price_cents)} / unidade</small>
                            </div>
                            <input
                              aria-label={`Quantidade de ${p.name}`}
                              type="number"
                              min="1"
                              max={p.stock}
                              value={q}
                              onChange={(e) =>
                                setCart({
                                  ...cart,
                                  [id]: Math.max(1, Number(e.target.value)),
                                })
                              }
                            />
                            <strong>{money(q * p.price_cents)}</strong>
                            <button
                              className="icon-button"
                              aria-label={`Remover ${p.name}`}
                              onClick={() => {
                                const next = { ...cart };
                                delete next[Number(id)];
                                setCart(next);
                              }}
                            >
                              <Trash2 size={17} />
                            </button>
                          </div>
                        ) : null;
                      })}
                    </div>
                    <div className="cart-total">
                      <strong>Total do pedido</strong>
                      <strong>{money(cartTotal)}</strong>
                    </div>
                    <p className="notice">
                      Demonstração sem cobrança online ou transporte real. A
                      confirmação registra uma conta a receber e baixa o
                      estoque.
                    </p>
                    {error && <p className="error">{error}</p>}
                    <div className="form-footer">
                      <button className="button secondary" onClick={close}>
                        Continuar comprando
                      </button>
                      <button
                        className="button primary"
                        disabled={busy}
                        onClick={async () => {
                          const items = Object.entries(cart)
                            .map(([id, quantity]) => ({
                              product_id: Number(id),
                              quantity,
                            }))
                            .sort((a, b) => a.product_id - b.product_id);
                          const fingerprint = JSON.stringify(items);
                          if (
                            checkoutAttempt.current.fingerprint !== fingerprint
                          )
                            checkoutAttempt.current = {
                              fingerprint,
                              key: crypto.randomUUID(),
                            };
                          if (
                            await act(
                              "/orders",
                              {
                                request_key: checkoutAttempt.current.key,
                                items: Object.entries(cart).map(
                                  ([id, quantity]) => ({
                                    product_id: Number(id),
                                    quantity,
                                  }),
                                ),
                              },
                              "POST",
                              "Pedido confirmado.",
                            )
                          ) {
                            setCart({});
                            go(isAdmin ? "finance" : "history");
                          }
                        }}
                      >
                        Confirmar pedido <ArrowRight size={17} />
                      </button>
                    </div>
                  </>
                ) : (
                  <Empty>Seu carrinho está esperando um pouco de verde.</Empty>
                )}
              </div>
            )}
            {modal.kind === "pay-ledger" && (
              <form
                className="form"
                onSubmit={(e) => {
                  e.preventDefault();
                  act(
                    `/ledger/${modal.item.id}/pay?paid_date=${new FormData(e.currentTarget).get("paid_date")}`,
                    {},
                    "PATCH",
                    "Pagamento registrado.",
                  );
                }}
              >
                <p>
                  {modal.item.description} ·{" "}
                  <strong>{money(modal.item.amount_cents)}</strong>
                </p>
                <label>
                  Data do pagamento
                  <input
                    name="paid_date"
                    type="date"
                    defaultValue={today}
                    required
                  />
                </label>
                {error && <p className="error">{error}</p>}
                <div className="form-footer">
                  <span>A baixa entra no fluxo de caixa.</span>
                  <SaveButton busy={busy} />
                </div>
              </form>
            )}
            {modal.kind === "cancel-order" && (
              <div className="detail">
                <p>
                  Cancelar o pedido <strong>#{modal.item.id}</strong>, de{" "}
                  <strong>{money(modal.item.total_cents)}</strong>?
                </p>
                <p>
                  As unidades serão devolvidas ao estoque. Pedidos pagos
                  precisam de reembolso e não podem ser cancelados
                  automaticamente.
                </p>
                {error && <p className="error">{error}</p>}
                <div className="form-footer">
                  <button className="button secondary" onClick={close}>
                    Manter pedido
                  </button>
                  <button
                    className="button primary"
                    disabled={busy}
                    onClick={() =>
                      act(
                        `/orders/${modal.item.id}/cancel`,
                        {},
                        "POST",
                        "Pedido cancelado. Estoque devolvido.",
                      )
                    }
                  >
                    Confirmar cancelamento
                  </button>
                </div>
              </div>
            )}
            {modal.kind === "species-detail" && (
              <SpeciesDetail species={modal.item} />
            )}
            {modal.kind === "product-photos" && (
              <div className="detail">
                <Picture item={modal.item} className="species-detail-photo" />
                <h2>{modal.item.name}</h2>
                <Gallery
                  entity="products"
                  id={modal.item.id}
                  editable
                  onChange={reload}
                />
              </div>
            )}
            {modal.kind === "agenda" && (
              <div className="detail">
                <button
                  className="button primary"
                  onClick={() => open("appointment")}
                >
                  <Plus size={17} />
                  Novo agendamento
                </button>
                <div className="table-scroll">
                  <table className="dense-table agenda-table">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Horário</th>
                        <th>Serviço</th>

                        <th>Status</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {data.appointments.map((a) => (
                        <tr key={a.id}>
                          <td>{dateLabel(a.date)}</td>
                          <td>
                            {a.start_time}–{a.end_time}
                          </td>
                          <td>{a.title}</td>

                          <td>
                            <Status value={a.status} />
                          </td>
                          <td>
                            <button
                              className="text-button"
                              onClick={() => open("appointment", a)}
                            >
                              Editar
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {modal.kind === "moves" && <StockHistory />}
            {modal.kind === "accounts" && (
              <div className="detail table-scroll">
                <table className="dense-table account-details-table">
                  <thead>
                    <tr>
                      <th>Cliente / fornecedor</th>

                      <th>Vencimento</th>
                      <th>Valor</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {modal.item.items.map((l: any) => (
                      <tr key={l.id}>
                        <td>{l.counterparty}</td>

                        <td>{dateLabel(l.due_date)}</td>
                        <td>{money(l.amount_cents)}</td>
                        <td>
                          <button
                            className="text-button"
                            onClick={() => open("pay-ledger", l)}
                          >
                            Registrar pagamento
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {modal.kind === "support" && (
              <div className="detail">
                <p>
                  O Ateliê Verde está em ambiente de demonstração. Compras
                  registram pedidos e contas a receber; pagamentos e entregas
                  reais dependem de integrações futuras.
                </p>
                <p>
                  Você pode solicitar orientação, visitas técnicas e serviços
                  pelo módulo de orçamentos.
                </p>
                <button
                  className="button primary"
                  onClick={() => open("quote-form")}
                >
                  Solicitar atendimento
                </button>
              </div>
            )}
            {error && (
              <p className="error modal-error" role="alert">
                {error}
              </p>
            )}
          </Modal>
        )}
      </div>
    </Green.Provider>
  );
}
function modalTitle(modal: { kind: string; item?: any }) {
  return (
    (
      {
        entity: modal.item?.record ? "Editar cadastro" : "Novo cadastro",
        "project-form": "Planejamento do projeto",
        cart: "Seu carrinho",
        profile: "Editar Perfil",
        "quote-form": "Novo orçamento",
        "landscape-studio": "Planejamento com paisagista",
        "landscape-view": "Planta 2D e memorial",
        "admin-quote": "Novo orçamento",
        "quote-photos": "Fotos do local",
        stock: "Registrar movimentação",
        "project-consumption": "Registrar consumo no projeto",
        "price-quote": "Gerar proposta",
        appointment: "Agendamento de serviço",
        agenda: "Agenda completa",
        ledger: `Nova ${modal.item?.direction?.toLowerCase()}`,
        "pay-ledger": "Registrar pagamento",
        "cancel-order": "Cancelar pedido",
        "species-detail": "Biblioteca de espécies",
        "product-photos": "Fotos do produto",
        accounts: modal.item?.title,
        moves: "Movimentações de estoque",
        audit: "Histórico de alterações",
        "data-quality": "Consistência dos dados",
        "movement-detail": "Detalhes da movimentação",
      } as Record<string, string>
    )[modal.kind] ||
    modal.item?.title ||
    "Informações"
  );
}
function PriceQuoteForm({ quote }: { quote: Quote }) {
  const { data, act, busy } = useGreen();
  const [plants, setPlants] = useState(quote.plants),
    [materials, setMaterials] = useState(quote.materials);
  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault();
        act(
          `/quotes/${quote.id}/price`,
          {
            amount_cents: Math.round(
              Number(new FormData(e.currentTarget).get("amount")) * 100,
            ),
            plants,
            materials,
          },
          "PATCH",
          "Proposta enviada.",
        );
      }}
    >
      <label>
        Valor da proposta (R$)
        <input
          type="number"
          name="amount"
          step="0.01"
          min="0.01"
          defaultValue={quote.amount_cents / 100 || ""}
          required
        />
      </label>
      <div className="section-heading">
        <h3>Espécies sugeridas</h3>
        <button
          type="button"
          className="text-button"
          onClick={() => {
            if (data.species.length)
              setPlants([
                ...plants,
                {
                  species_id: data.species[0].id,
                  quantity: 1,
                  application: "",
                },
              ]);
          }}
        >
          <Plus size={15} />
          Adicionar espécie
        </button>
      </div>
      {plants.map((p, i) => (
        <div className="plant-row" key={i}>
          <select
            aria-label="Espécie sugerida"
            value={p.species_id}
            onChange={(e) =>
              setPlants(
                plants.map((r, j) =>
                  i === j ? { ...r, species_id: Number(e.target.value) } : r,
                ),
              )
            }
          >
            {data.species.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} · {s.light}
              </option>
            ))}
          </select>
          <input
            aria-label="Quantidade"
            type="number"
            min="1"
            value={p.quantity}
            onChange={(e) =>
              setPlants(
                plants.map((r, j) =>
                  i === j ? { ...r, quantity: Number(e.target.value) } : r,
                ),
              )
            }
          />
          <button
            type="button"
            aria-label="Remover espécie"
            className="icon-button"
            onClick={() => setPlants(plants.filter((_, j) => i !== j))}
          >
            <Trash2 size={15} />
          </button>
        </div>
      ))}
      <div className="section-heading">
        <h3>Materiais</h3>
        <button
          type="button"
          className="text-button"
          onClick={() =>
            setMaterials([
              ...materials,
              { name: "", quantity: 1, unit_price_cents: 0 },
            ])
          }
        >
          <Plus size={15} />
          Adicionar material
        </button>
      </div>
      {materials.map((m, i) => (
        <div className="cost-row" key={i}>
          <input
            aria-label="Nome do material"
            required
            minLength={2}
            value={m.name}
            onChange={(e) =>
              setMaterials(
                materials.map((r, j) =>
                  i === j ? { ...r, name: e.target.value } : r,
                ),
              )
            }
          />
          <input
            aria-label="Quantidade do material"
            type="number"
            min="0.01"
            step="0.01"
            value={m.quantity}
            onChange={(e) =>
              setMaterials(
                materials.map((r, j) =>
                  i === j ? { ...r, quantity: Number(e.target.value) } : r,
                ),
              )
            }
          />
          <input
            aria-label="Valor unitário em reais"
            type="number"
            min="0"
            step="0.01"
            value={m.unit_price_cents / 100}
            onChange={(e) =>
              setMaterials(
                materials.map((r, j) =>
                  i === j
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
            aria-label="Remover material"
            onClick={() => setMaterials(materials.filter((_, j) => i !== j))}
          >
            <Trash2 size={15} />
          </button>
        </div>
      ))}
      <div className="form-footer">
        <span>A aprovação transforma a proposta em projeto.</span>
        <SaveButton busy={busy} label="Enviar proposta" />
      </div>
    </form>
  );
}
