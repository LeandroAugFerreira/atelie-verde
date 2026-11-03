import { useEffect, useState } from "react";
import {
  Leaf,
  ArrowRight,
  CalendarDays,
  Truck,
  ShieldCheck,
  Headphones,
  ShoppingCart,
  Heart,
  Grid2X2,
  Flower2,
  CookingPot,
  Layers,
  Sprout,
  Wrench,
  Package,
  Sun,
  Home,
  RefreshCw,
  Star,
  SlidersHorizontal,
  Minus,
  Plus,
  LockKeyhole,
  Search,
  ZoomIn,
  X,
  Droplets,
  Ruler,
  BarChart3,
  Check,
  MessageCircle,
  Download,
  MapPin,
} from "lucide-react";
import { useGreen } from "./context";
import {
  Sprite,
  Logo,
  Picture,
  Status,
  SearchInput,
  Paginator,
  exportCSV,
} from "./ReferenceUI";
import { Empty, Modal, Photo, SaveButton } from "./components";
import { api, write } from "./api";
import { money, dateLabel, type Product } from "./types";
import {
  PageTitle,
  ProjectsPage,
  ProjectPage,
  QuoteProfile,
} from "./AdminPages";
import { categories } from "./Forms";
import { Sources, PhotoCredits } from "./BotanicalDetails";
import { AskRafinha } from "./RafinhaAssistant";
import { matchesPlantGroup, plantGroupOptions } from "./plantGroups";

const categoryIcons = [Leaf, CookingPot, Layers, Sprout, Wrench, Package];
const categoryAssets = [
  "plants",
  "pots",
  "substrate",
  "fertilizer",
  "tools",
  "accessories",
];
const match = (query: string, ...values: unknown[]) =>
  values
    .join(" ")
    .toLocaleLowerCase("pt-BR")
    .includes(query.toLocaleLowerCase("pt-BR"));
export function HomePage() {
  const { go, open, data } = useGreen();
  return (
    <>
      <section className="shop-hero">
        <Sprite name="hero" />
        <div className="hero-shade" />
        <div className="hero-copy">
          <h1>
            Mais <span>verde</span>
            <br />
            para a sua vida
          </h1>
          <p>
            Plantas, produtos e serviços de jardinagem e paisagismo
            <br />
            para transformar seus ambientes em espaços mais saudáveis,
            <br />
            bonitos e cheios de vida.
          </p>
          <div>
            <button className="button primary" onClick={() => go("catalog")}>
              <Leaf size={20} />
              Ver produtos <ArrowRight size={20} />
            </button>
            <button
              className="button transparent"
              onClick={() => open("quote-form")}
            >
              <CalendarDays size={21} />
              Solicitar orçamento
            </button>
          </div>
        </div>
        <div className="hero-quote">
          Natureza
          <br />
          também é<br />
          bem-estar
          <i />
        </div>
      </section>
      <div className="benefits">
        {[
          {
            title: "Qualidade garantida",
            text: "Plantas e produtos selecionados",
            Icon: Sprout,
          },
          {
            title: "Entrega para todo o Brasil",
            text: "Consulte condições da demonstração",
            Icon: Truck,
          },
          {
            title: "Suporte especializado",
            text: "Orientação sobre os nossos serviços",
            Icon: ShieldCheck,
          },
          {
            title: "Ambientes mais saudáveis",
            text: "Mais verde para o seu bem-estar",
            Icon: Leaf,
          },
        ].map((b) => (
          <div key={b.title}>
            <span className="round-icon">
              <b.Icon size={30} />
            </span>
            <div>
              <strong>{b.title}</strong>
              <small>{b.text}</small>
            </div>
          </div>
        ))}
      </div>
      <div className="shop-home-content">
        <div className="section-heading">
          <div>
            <h2>Categorias da loja</h2>
            <p>Tudo o que você precisa para seu jardim em um só lugar.</p>
          </div>
          <button className="text-button" onClick={() => go("catalog")}>
            Ver todas as categorias <ArrowRight size={16} />
          </button>
        </div>
        <div className="category-grid">
          {categories.map((c, i) => (
            <button key={c} onClick={() => go("catalog", i + 1)}>
              <Sprite name={categoryAssets[i]} />
              <div>
                <h3>{c}</h3>
                <span>
                  Ver produtos <ArrowRight size={16} />
                </span>
              </div>
            </button>
          ))}
        </div>
        <div className="section-heading">
          <div>
            <h2>Serviços de jardinagem e paisagismo</h2>
            <p>
              Da manutenção ao projeto completo, cuidamos do seu espaço verde.
            </p>
          </div>
          <button className="text-button" onClick={() => go("services")}>
            Ver todos os serviços <ArrowRight size={16} />
          </button>
        </div>
        <div className="home-services">
          {[
            {
              name: "Poda de plantas",
              asset: "pruning",
              Icon: Leaf,
              text: "Mais saúde e beleza para suas plantas",
            },
            {
              name: "Manutenção de jardins",
              asset: "maintenance",
              Icon: Flower2,
              text: "Seu jardim sempre bonito e bem cuidado",
            },
            {
              name: "Irrigação automatizada",
              asset: "irrigation",
              Icon: Droplets,
              text: "Tecnologia para um jardim sempre verde",
            },
            {
              name: "Consultoria especializada",
              asset: "consulting",
              Icon: MessageCircle,
              text: "Orientação técnica para o seu espaço",
            },
            {
              name: "Projetos paisagísticos",
              asset: "landscape",
              Icon: Grid2X2,
              text: "Ambientes únicos e personalizados",
            },
          ].map((s) => (
            <button
              key={s.name}
              onClick={() => {
                const service = data.services.find(
                  (item) => item.active && item.demo_asset === s.asset,
                );
                if (service) go("service-detail", service.id);
                else go("services");
              }}
            >
              <Sprite name={s.asset} />
              <div>
                <span className="round-icon small">
                  <s.Icon size={23} />
                </span>
                <div>
                  <strong>{s.name}</strong>
                  <small>{s.text}</small>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}

export function CatalogPage() {
  const { data, selectedId, search, go, addCart, favorite } = useGreen();
  const [category] = useState(selectedId ? categories[selectedId - 1] : ""),
    [plantGroup, setPlantGroup] = useState(""),
    [maxPrice, setMaxPrice] = useState(500),
    [lights, setLights] = useState<string[]>([]),
    [environments, setEnvironments] = useState<string[]>([]),
    [difficulty, setDifficulty] = useState<string[]>([]),
    [sort, setSort] = useState("relevant"),
    [page, setPage] = useState(1),
    [onlyFavorites, setOnlyFavorites] = useState(false);
  useEffect(
    () => setPage(1),
    [
      search,
      category,
      maxPrice,
      plantGroup,
      lights,
      environments,
      difficulty,
      sort,
      onlyFavorites,
    ],
  );
  const toggle = (
    values: string[],
    value: string,
    set: (v: string[]) => void,
  ) =>
    set(
      values.includes(value)
        ? values.filter((v) => v !== value)
        : [...values, value],
    );
  const referenceOrder = [
    "hibiscus",
    "monstera",
    "sword",
    "jasmine",
    "palm",
    "lavender",
    "boxwood",
    "desert",
  ];
  const priority = (p: Product) =>
    referenceOrder.includes(p.demo_asset)
      ? referenceOrder.indexOf(p.demo_asset)
      : 100 + p.id;
  const filtered = data.products
    .filter((p) => {
      const s = data.species.find((s) => s.id === p.species_id);
      return (
        p.active &&
        (!category || p.category === category) &&
        matchesPlantGroup(s, plantGroup) &&
        p.price_cents <= maxPrice * 100 &&
        match(search, p.name, p.description, s?.scientific_name) &&
        (!lights.length || lights.includes(s?.light || "")) &&
        (!environments.length ||
          environments.some(
            (e) =>
              s?.environment === "Ambos" ||
              s?.environment ===
                (e === "Varanda"
                  ? "Externo"
                  : e === "Escritório"
                    ? "Interno"
                    : e),
          )) &&
        (!difficulty.length || difficulty.includes(s?.difficulty || "")) &&
        (!onlyFavorites || data.favorites.includes(p.id))
      );
    })
    .sort((a, b) =>
      sort === "price-up"
        ? a.price_cents - b.price_cents
        : sort === "price-down"
          ? b.price_cents - a.price_cents
          : priority(a) - priority(b),
    );
  const plantTitle = category || "Produtos";
  const filterSection = (
    title: string,
    values: { label: string; value: string }[],
    selected: string[],
    setter: (v: string[]) => void,
    Icon: typeof Leaf,
  ) => (
    <details open className="filter-section">
      <summary>
        <Icon size={19} />
        {title}
      </summary>
      {values.map(({ label, value }) => (
        <label className="checkbox-label" key={value}>
          <input
            type="checkbox"
            checked={selected.includes(value)}
            onChange={() => toggle(selected, value, setter)}
          />
          {label}
        </label>
      ))}
    </details>
  );
  return (
    <div className="catalog-layout">
      <aside className="catalog-sidebar">
        <section>
          <h2>Categorias</h2>
          <button
            className={!category ? "active" : ""}
            onClick={() => go("catalog")}
          >
            <Grid2X2 size={20} />
            <strong>Todas</strong>
            <span>({data.products.filter((p) => p.active).length})</span>
          </button>
          {categories.map((c, i) => {
            const Icon = categoryIcons[i];
            return (
              <button
                key={c}
                className={category === c ? "active" : ""}
                onClick={() => go("catalog", i + 1)}
              >
                <Icon size={20} />
                <span>{c}</span>
                <small>
                  (
                  {
                    data.products.filter((p) => p.active && p.category === c)
                      .length
                  }
                  )
                </small>
              </button>
            );
          })}
        </section>
        <section>
          <div className="section-heading">
            <h2>Filtros</h2>
            <button
              className="text-button"
              onClick={() => {
                setMaxPrice(500);
                setPlantGroup("");
                setLights([]);
                setEnvironments([]);
                setDifficulty([]);
                setOnlyFavorites(false);
              }}
            >
              <RefreshCw size={14} />
              Limpar filtros
            </button>
          </div>
          <label className="plant-type-filter">
            Tipos de plantas
            <select
              aria-label="Tipos de plantas"
              value={plantGroup}
              onChange={(e) => setPlantGroup(e.target.value)}
            >
              <option value="">Todas as espécies</option>
              {plantGroupOptions(data.species).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <div className="price-filter">
            <h4>
              <TagIcon />
              Preço
            </h4>
            <div>
              <span>R$ 0</span>
              <span>{money(maxPrice * 100)}</span>
            </div>
            <input
              aria-label="Preço máximo"
              type="range"
              min="0"
              max="500"
              value={maxPrice}
              onChange={(e) => setMaxPrice(Number(e.target.value))}
            />
          </div>
          {filterSection(
            "Luminosidade",
            ["Sol pleno", "Meia-sombra", "Sombra"].map((v) => ({
              value: v,
              label: v,
            })),
            lights,
            setLights,
            Sun,
          )}
          {filterSection(
            "Ambiente",
            ["Interno", "Externo", "Varanda", "Escritório"].map((v) => ({
              value: v,
              label: v,
            })),
            environments,
            setEnvironments,
            Home,
          )}
          {filterSection(
            "Dificuldade de cultivo",
            [
              { label: "Fácil", value: "Baixa" },
              { label: "Intermediária", value: "Média" },
              { label: "Avançada", value: "Alta" },
            ],
            difficulty,
            setDifficulty,
            Sprout,
          )}
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={onlyFavorites}
              onChange={(e) => setOnlyFavorites(e.target.checked)}
            />
            <Heart size={15} />
            Meus favoritos
          </label>
        </section>
      </aside>
      <div className="catalog-content">
        <div className="catalog-heading">
          <div>
            <h1>{plantTitle}</h1>
            <p>
              Descubra espécies incríveis para deixar seu espaço mais verde e
              cheio de vida.
            </p>
          </div>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            aria-label="Ordenar produtos"
          >
            <option value="relevant">Mais relevantes</option>
            <option value="price-up">Menor preço</option>
            <option value="price-down">Maior preço</option>
          </select>
          <span className="muted">{filtered.length} produtos</span>
        </div>
        <div className="catalog-grid">
          {filtered.slice((page - 1) * 8, page * 8).map((p) => {
            const s = data.species.find((s) => s.id === p.species_id),
              reviews = data.reviews.filter((r) => r.product_id === p.id),
              rating = reviews.length
                ? reviews.reduce((n, r) => n + r.rating, 0) / reviews.length
                : 0;
            return (
              <article className="catalog-card" key={p.id}>
                <button
                  className="catalog-photo"
                  onClick={() => go("product", p.id)}
                >
                  <Picture item={p} />
                </button>
                <button
                  className={`favorite-button ${data.favorites.includes(p.id) ? "active" : ""}`}
                  aria-label={`${data.favorites.includes(p.id) ? "Remover" : "Adicionar"} ${p.name} dos favoritos`}
                  onClick={() => favorite(p.id)}
                >
                  <Heart size={20} />
                </button>
                <div className="catalog-card-body">
                  <button
                    className="product-name"
                    onClick={() => go("product", p.id)}
                  >
                    {p.name}
                  </button>
                  <i>{s?.scientific_name || p.category}</i>
                  {s && (
                    <div className="plant-tags">
                      <span>{s.environment}</span>
                      <span>{s.light}</span>
                      <span>
                        {s.difficulty === "Baixa"
                          ? "Fácil"
                          : s.difficulty === "Média"
                            ? "Intermediária"
                            : "Avançada"}
                      </span>
                    </div>
                  )}
                  <div className="rating">
                    <Star size={17} fill="#ffb400" />
                    <strong>
                      {rating
                        ? rating.toLocaleString("pt-BR", {
                            maximumFractionDigits: 1,
                          })
                        : "Novo"}
                    </strong>
                    <span>({reviews.length})</span>
                  </div>
                  <div className="card-buy">
                    <strong>{money(p.price_cents)}</strong>
                    <button
                      className="button primary"
                      disabled={p.stock === 0}
                      onClick={() => addCart(p)}
                    >
                      <ShoppingCart size={18} />
                      {p.stock ? "Adicionar" : "Esgotado"}
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
        {!filtered.length && (
          <Empty>Nenhum produto combina com os filtros.</Empty>
        )}
        <Paginator
          total={filtered.length}
          page={page}
          setPage={setPage}
          size={8}
        />
      </div>
    </div>
  );
}
function TagIcon() {
  return <Flower2 size={17} />;
}

export function ProductPage() {
  const { data, selectedId, addCart, favorite, open, user, reload, toast } =
    useGreen();
  const p = data.products.find((p) => p.id === selectedId),
    s = data.species.find((s) => s.id === p?.species_id);
  const [quantity, setQuantity] = useState(1),
    [tab, setTab] = useState(
      p?.species_id ? "Informações da planta" : "Descrição",
    ),
    [photo, setPhoto] = useState(0),
    [zoom, setZoom] = useState(false),
    [careSources, setCareSources] = useState(false),
    [creditsOpen, setCreditsOpen] = useState(false),
    [uploads, setUploads] = useState<{ id: number; url: string }[]>([]),
    [reviewBusy, setReviewBusy] = useState(false),
    [reviewError, setReviewError] = useState("");
  useEffect(() => {
    if (p)
      api<typeof uploads>(`/images/products/${p.id}`)
        .then(setUploads)
        .catch(() => {});
  }, [p?.id]);
  if (!p) return <Empty>Produto não encontrado.</Empty>;
  const reviews = data.reviews.filter((r) => r.product_id === p.id),
    rating = reviews.length
      ? reviews.reduce((n, r) => n + r.rating, 0) / reviews.length
      : 0;
  const botanicalPhotos = s?.photos || [];
  const sourcePhotos = (
    p.image_url && !botanicalPhotos.some((row) => row.url === p.image_url)
      ? [{ url: p.image_url }, ...botanicalPhotos]
      : botanicalPhotos
  ).filter((row) => !uploads.some((upload) => upload.url === row.url));
  const thumbnails =
    sourcePhotos.length || p.image_url || p.category !== "Plantas"
      ? []
      : p.demo_asset === "hibiscus"
        ? ["hibiscusDetail", "hibiscus2", "hibiscus3", "hibiscus4", "hibiscus5"]
        : [p.demo_asset || "plants"];
  const hero =
    photo < uploads.length ? (
      <Photo url={uploads[photo].url} />
    ) : sourcePhotos.length ? (
      <Photo
        url={sourcePhotos[(photo - uploads.length) % sourcePhotos.length].url}
      />
    ) : p.image_url ? (
      <Photo url={p.image_url} />
    ) : (
      <Picture item={p} />
    );
  const infoTab = s ? "Informações da planta" : "Informações do produto";
  const rows = s
    ? [
        ["Nome popular", p.name],
        ["Nome científico", s?.scientific_name],
        ["Luminosidade", s?.light],
        ["Necessidade de água", s?.watering],
        ["Porte", s?.height || s?.size],
        ["Ambiente", s?.environment],
        ["Uso", s?.use],
        [
          "Nível de dificuldade",
          s?.difficulty === "Baixa"
            ? "Fácil"
            : s?.difficulty === "Média"
              ? "Intermediária"
              : "Avançada",
        ],
      ]
    : [
        ["Produto", p.name],
        ["Código", p.sku],
        ["Categoria", p.category],
        ["Marca", p.brand || "Não informada"],
        ["Preço", money(p.price_cents)],
        ["Disponibilidade", p.stock ? "Disponível" : "Indisponível"],
      ];
  return (
    <div className="product-page">
      <div className="product-top product-layout">
        <div className="product-gallery">
          <div className="product-large-photo">
            {hero}
            <button
              className="zoom-button"
              aria-label="Ampliar foto"
              onClick={() => setZoom(true)}
            >
              <ZoomIn size={24} />
            </button>
          </div>
          <div className="product-thumbnails">
            {uploads.map((u, i) => (
              <button
                key={u.id}
                className={photo === i ? "active" : ""}
                onClick={() => setPhoto(i)}
              >
                <Photo url={u.url} />
              </button>
            ))}
            {sourcePhotos.map((p, i) => (
              <button
                key={p.url}
                className={photo === uploads.length + i ? "active" : ""}
                onClick={() => setPhoto(uploads.length + i)}
                aria-label={`${s ? "Foto botânica" : "Foto do produto"} ${i + 1}`}
              >
                <Photo url={p.url} />
              </button>
            ))}
            {thumbnails.map((name, i) => (
              <button
                key={name}
                className={photo === uploads.length + i ? "active" : ""}
                onClick={() => setPhoto(uploads.length + i)}
                aria-label={`Foto ${i + 1}`}
              >
                <Sprite name={name} />
              </button>
            ))}
          </div>
          {!!s?.photos?.length && (
            <button
              className="text-button product-photo-credits"
              onClick={() => setCreditsOpen(true)}
            >
              Créditos das fotografias
            </button>
          )}
          {p.image_url.startsWith("/catalog-media/products/") && (
            <p className="product-image-note">
              Imagem ilustrativa do produto demonstrativo.
            </p>
          )}
        </div>
        <div className="product-detail-content">
          <div className="product-purchase">
            <h1>{p.name}</h1>
            <AskRafinha
              context={{ kind: "product", id: p.id, label: p.name }}
              label={
                s
                  ? "Perguntar ao Rafinha sobre esta planta"
                  : "Perguntar ao Rafinha sobre este produto"
              }
            />
            {s && <i className="scientific">{s.scientific_name}</i>}
            <div className="product-rating">
              <span className="stars">
                {"★".repeat(Math.round(rating))}
                {"☆".repeat(5 - Math.round(rating))}
              </span>
              <strong>
                {rating
                  ? rating.toLocaleString("pt-BR", { maximumFractionDigits: 1 })
                  : "Novo"}
              </strong>
              <span>({reviews.length} avaliações)</span>
              <button
                className="text-button"
                onClick={() => setTab("Avaliações")}
              >
                Ver todas as avaliações
              </button>
              <Status value={p.stock ? "Disponível" : "Baixo"} />
            </div>
            <p className="product-description">
              {s?.description || p.description}
            </p>
            <div className="product-price-large">
              <strong>{money(p.price_cents)}</strong>
              <span>/ unidade</span>
            </div>
            <div className="buy-line">
              <label>
                Quantidade
                <div className="quantity-picker">
                  <button
                    aria-label="Diminuir quantidade"
                    disabled={quantity <= 1}
                    onClick={() => setQuantity(quantity - 1)}
                  >
                    <Minus size={17} />
                  </button>
                  <span>{quantity}</span>
                  <button
                    aria-label="Aumentar quantidade"
                    disabled={quantity >= p.stock}
                    onClick={() => setQuantity(quantity + 1)}
                  >
                    <Plus size={17} />
                  </button>
                </div>
              </label>
              <div>
                <button
                  className="button primary full"
                  disabled={p.stock === 0}
                  onClick={() => addCart(p, quantity)}
                >
                  <ShoppingCart size={27} />
                  Adicionar ao carrinho
                </button>
                <button
                  className="wishlist-link"
                  onClick={() => favorite(p.id)}
                  aria-label={
                    data.favorites.includes(p.id)
                      ? "Adicionado à lista de desejos"
                      : "Adicionar à lista de desejos"
                  }
                >
                  <Heart
                    size={18}
                    fill={data.favorites.includes(p.id) ? "#07823c" : "none"}
                  />
                  <span>
                    {data.favorites.includes(p.id)
                      ? "Adicionado à lista de desejos"
                      : "Adicionar à lista de desejos"}
                  </span>
                </button>
              </div>
            </div>
            <div className="purchase-benefits">
              {[
                {
                  title: "Entrega para todo o Brasil",
                  text: "Consulte a demonstração",
                  Icon: Truck,
                },
                {
                  title: "Pagamento seguro",
                  text: "Sem cobrança na demonstração",
                  Icon: LockKeyhole,
                },
                {
                  title: "Compra garantida",
                  text: "Cancelamento antes da baixa",
                  Icon: ShieldCheck,
                },
                {
                  title: "Suporte especializado",
                  text: "Tire suas dúvidas",
                  Icon: Headphones,
                },
              ].map((b) => (
                <button
                  key={b.title}
                  onClick={() => open("support", { title: b.title })}
                >
                  <span className="round-icon">
                    <b.Icon size={24} />
                  </span>
                  <div>
                    <strong>{b.title}</strong>
                    <small>{b.text}</small>
                  </div>
                </button>
              ))}
            </div>
          </div>
          <div className="product-info-tabs tabs">
            {[
              "Descrição",
              infoTab,
              ...(s ? ["Cuidados"] : []),
              "Avaliações",
            ].map((t) => (
              <button
                className={tab === t ? "selected" : ""}
                key={t}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </div>
          {tab === infoTab && (
            <div className="plant-information">
              <section className="panel">
                <h2>
                  <Leaf size={24} />
                  {infoTab}
                </h2>
                <table className="information-table">
                  <tbody>
                    {rows.map(([label, value], i) => (
                      <tr key={label}>
                        <th>
                          <span>
                            {
                              [
                                <Leaf size={15} />,
                                <Flower2 size={15} />,
                                <Sun size={15} />,
                                <Droplets size={15} />,
                                <Ruler size={15} />,
                                <Home size={15} />,
                                <Sprout size={15} />,
                                <BarChart3 size={15} />,
                              ][i]
                            }
                            {label}
                          </span>
                        </th>
                        <td>{value || "Não se aplica"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </div>
          )}
          {tab === "Descrição" && (
            <section className="panel">
              <h2>{p.name}</h2>
              {[p.description, s?.description]
                .filter((text): text is string => Boolean(text?.trim()))
                .filter(
                  (text, index, texts) =>
                    texts.findIndex(
                      (other) =>
                        other
                          .trim()
                          .replace(/\s+/g, " ")
                          .toLocaleLowerCase("pt-BR") ===
                        text
                          .trim()
                          .replace(/\s+/g, " ")
                          .toLocaleLowerCase("pt-BR"),
                    ) === index,
                )
                .map((text) => (
                  <p key={text}>{text}</p>
                ))}
            </section>
          )}
          {tab === "Cuidados" && (
            <section className="panel product-care-panel">
              <div className="care-heading">
                <h2>Como cuidar</h2>
                {!!s?.sources?.length && (
                  <button
                    className="text-button"
                    onClick={() => setCareSources(true)}
                  >
                    Consultar fontes dos cuidados
                  </button>
                )}
              </div>
              <div className="product-care-intro">
                <p>
                  {s?.care ||
                    "Consulte as orientações do produto com nossa equipe."}
                </p>
                <p className="muted">
                  As condições de clima, solo, vaso e iluminação influenciam os
                  cuidados.
                </p>
              </div>
              <div className="care-grid">
                {[
                  ["Rega", s?.watering_frequency],
                  ["Substrato", s?.substrate],
                  ["Propagação", s?.propagation],
                  ["Precauções", s?.precautions],
                ]
                  .filter(([, v]) => v)
                  .map(([label, value]) => (
                    <div key={label}>
                      <h3>{label}</h3>
                      <p>{value}</p>
                    </div>
                  ))}
              </div>
            </section>
          )}
          {tab === "Avaliações" && (
            <section className="panel">
              <h2>Avaliações de clientes ({reviews.length})</h2>
              {reviews.map((r) => (
                <div className="review" key={r.id}>
                  <strong>{r.customer_name}</strong>
                  <span className="stars">
                    {"★".repeat(r.rating)}
                    {"☆".repeat(5 - r.rating)}
                  </span>
                  <p>{r.comment}</p>
                  <small>{dateLabel(r.created_at)}</small>
                </div>
              ))}
              {!reviews.length && (
                <p className="muted">
                  Este produto ainda não recebeu avaliações.
                </p>
              )}
              <form
                className="form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  setReviewBusy(true);
                  setReviewError("");
                  try {
                    await write(`/products/${p.id}/reviews`, {
                      rating: Number(f.get("rating")),
                      comment: f.get("comment"),
                    });
                    await reload();
                    toast("Avaliação publicada.");
                  } catch (e) {
                    setReviewError((e as Error).message);
                  } finally {
                    setReviewBusy(false);
                  }
                }}
              >
                <h3>Conte sua experiência</h3>
                <p className="muted">
                  Disponível para clientes que compraram este produto.
                </p>
                <label>
                  Sua nota
                  <select name="rating">
                    {[5, 4, 3, 2, 1].map((r) => (
                      <option key={r} value={r}>
                        {r} estrelas
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Avaliação
                  <textarea
                    name="comment"
                    minLength={3}
                    maxLength={1000}
                    required
                  />
                </label>
                {reviewError && <p className="error">{reviewError}</p>}
                <SaveButton busy={reviewBusy} label="Publicar avaliação" />
              </form>
            </section>
          )}
        </div>
      </div>
      {zoom && (
        <Modal title={`Foto de ${p.name}`} onClose={() => setZoom(false)} wide>
          <div className="zoomed-photo">{hero}</div>
        </Modal>
      )}
      {careSources && (
        <Modal
          title="Fontes dos cuidados"
          onClose={() => setCareSources(false)}
        >
          <Sources items={s?.sources} />
          <PhotoCredits photos={s?.photos} />
        </Modal>
      )}
      {creditsOpen && (
        <Modal
          title="Créditos das fotografias"
          onClose={() => setCreditsOpen(false)}
        >
          <PhotoCredits photos={s?.photos} expanded />
        </Modal>
      )}
    </div>
  );
}

export function ClientServicesPage() {
  const { data, open, go } = useGreen();
  return (
    <div className="client-inner">
      <PageTitle
        title="Serviços"
        subtitle="Cuidado profissional para cada espaço verde"
      >
        <button className="button primary" onClick={() => open("quote-form")}>
          <Plus size={19} />
          Solicitar orçamento
        </button>
      </PageTitle>
      <div className="client-service-grid">
        {data.services
          .filter((s) => s.active)
          .map((s) => (
            <article className="client-service-card" key={s.id}>
              <Sprite name={s.demo_asset || "maintenance"} />
              <div>
                <h2>{s.name}</h2>
                <p>{s.description}</p>
                <span className="service-mode">{s.delivery_mode}</span>
                <strong>
                  A partir de {money(s.price_cents)} / {s.unit}
                </strong>
                <button
                  className="button primary"
                  onClick={() => go("service-detail", s.id)}
                >
                  Conhecer serviço <ArrowRight size={17} />
                </button>
              </div>
            </article>
          ))}
      </div>
      <section className="panel">
        <h2>Meus agendamentos</h2>
        {data.appointments.map((a) => (
          <div className="schedule-row" key={a.id}>
            <CalendarDays size={20} />
            <strong>{a.title}</strong>
            <span>
              {dateLabel(a.date)} · {a.start_time} – {a.end_time}
            </span>
            <Status value={a.status} />
          </div>
        ))}
        {!data.appointments.length && (
          <Empty>A equipe agendará os serviços após a avaliação.</Empty>
        )}
      </section>
    </div>
  );
}
export function ClientQuotesPage() {
  const { data, open } = useGreen();
  const [selected, setSelected] = useState<number | null>(null);
  const q = data.quotes.find((q) => q.id === selected) || data.quotes[0];
  return (
    <div className="client-inner">
      <PageTitle
        title="Meus orçamentos"
        subtitle="Acompanhe solicitações, propostas e aprovações"
      >
        <button className="button primary" onClick={() => open("quote-form")}>
          <Plus size={19} />
          Solicitar orçamento
        </button>
      </PageTitle>
      <div className="split quote-layout">
        <section className="panel">
          <table className="dense-table client-quotes-table">
            <thead>
              <tr>
                <th>Serviço</th>

                <th>Status</th>
                <th>Valor</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.quotes.map((q) => (
                <tr key={q.id} onClick={() => setSelected(q.id)}>
                  <td>
                    {data.services.find((s) => s.id === q.service_id)?.name}
                  </td>

                  <td>
                    <Status value={q.status} />
                  </td>
                  <td>
                    {q.amount_cents ? money(q.amount_cents) : "Em avaliação"}
                  </td>
                  <td>
                    <button
                      className="text-button"
                      onClick={() => setSelected(q.id)}
                    >
                      Ver proposta
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data.quotes.length && <Empty>Nenhum orçamento solicitado.</Empty>}
        </section>
        {q && <QuoteProfile quote={q} />}
      </div>
    </div>
  );
}
export function ClientHistoryPage() {
  const { data, open } = useGreen();
  return (
    <div className="client-inner">
      <PageTitle
        title="Meu histórico"
        subtitle="Pedidos e compras no Ateliê Verde"
      >
        <button
          className="button secondary"
          onClick={() =>
            exportCSV(
              "minhas-compras",
              ["Pedido", "Data", "Status", "Total centavos"],
              data.orders.map((o) => [
                o.id,
                o.created_at,
                o.status,
                o.total_cents,
              ]),
            )
          }
        >
          <Download size={18} />
          Exportar CSV
        </button>
      </PageTitle>
      <section className="panel">
        <div className="table-scroll">
          <table className="dense-table client-orders-table">
            <thead>
              <tr>
                <th>Produtos</th>
                <th>Data</th>
                <th>Total</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {data.orders.map((o) => (
                <tr key={o.id}>
                  <td>
                    {o.items.map((i) => `${i.quantity}× ${i.name}`).join(", ")}
                  </td>
                  <td>{dateLabel(o.created_at)}</td>
                  <td>{money(o.total_cents)}</td>
                  <td>
                    <Status value={o.status} />
                  </td>
                  <td>
                    {o.status === "Confirmado" && (
                      <button
                        className="text-button red-text"
                        aria-label="Cancelar pedido"
                        onClick={() => open("cancel-order", o)}
                      >
                        Cancelar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!data.orders.length && (
          <Empty>Seu histórico começa com a primeira compra.</Empty>
        )}
      </section>
    </div>
  );
}
export function LibraryPage() {
  const { data, open } = useGreen();
  const [light, setLight] = useState(""),
    [size, setSize] = useState(""),
    [difficulty, setDifficulty] = useState(""),
    [objective, setObjective] = useState("");
  return (
    <>
      <PageTitle
        title="Biblioteca de espécies"
        subtitle="Selecione espécies compatíveis com as condições do projeto"
      />
      <section className="panel recommendation">
        <h2>
          <SlidersHorizontal size={24} />
          Recomendação por características
        </h2>
        <div className="form-grid four">
          {[
            {
              label: "Luminosidade",
              value: light,
              set: setLight,
              options: ["Sol pleno", "Meia-sombra", "Sombra"],
            },
            {
              label: "Porte",
              value: size,
              set: setSize,
              options: ["Pequeno", "Médio", "Grande"],
            },
            {
              label: "Manutenção",
              value: difficulty,
              set: setDifficulty,
              options: ["Baixa", "Média", "Alta"],
            },
            {
              label: "Tipo de planta",
              value: objective,
              set: setObjective,
              options: plantGroupOptions(data.species).map(
                (option) => option.value,
              ),
            },
          ].map((f) => (
            <label key={f.label}>
              {f.label}
              <select value={f.value} onChange={(e) => f.set(e.target.value)}>
                <option value="">Todos</option>
                {f.options.map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            </label>
          ))}
        </div>
        <p className="muted">
          Os resultados usam os atributos cadastrados; confirme clima, solo e
          condições reais na visita técnica.
        </p>
      </section>
      <div className="library-grid">
        {data.species
          .filter(
            (s) =>
              (!light || s.light === light) &&
              (!size || s.size === size) &&
              (!difficulty || s.difficulty === difficulty) &&
              matchesPlantGroup(s, objective),
          )
          .map((s) => (
            <button
              className="species-library-card"
              key={s.id}
              onClick={() => open("species-detail", s)}
            >
              <Picture item={s} />
              <div>
                <h3>{s.name}</h3>
                <i>{s.scientific_name}</i>
                <p>
                  {s.light} · {s.size}
                </p>
                <span>
                  Manutenção {s.difficulty.toLowerCase()}{" "}
                  <ArrowRight size={16} />
                </span>
              </div>
            </button>
          ))}
      </div>
    </>
  );
}
