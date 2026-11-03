import { useEffect, useId, useState, type ReactNode } from "react";
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Leaf,
  Search,
  CalendarDays,
  ArrowUp,
  TrendingUp,
  ImageOff,
  type LucideIcon,
} from "lucide-react";
import { useGreen } from "./context";
import { Photo } from "./components";
import { money, dateLabel, type Product, type Species } from "./types";

// Full-size catalog illustrations replace tiny crops from the reference screenshots.
const catalogImages: Record<string, string> = {
  pruning: "/catalog-media/pruning-v2.png",
  maintenance: "/projects/jardim-frontal.png",
  irrigation: "/catalog-media/irrigation-v2.png",
  consulting: "/catalog-media/consulting-v2.png",
  landscape: "/projects/area-externa.png",
  installation: "/catalog-media/installation-v2.png",
  pots: "/catalog-media/pots-v2.png",
  substrate: "/catalog-media/substrate-v2.png",
  fertilizer: "/catalog-media/fertilizer-v2.png",
  tools: "/catalog-media/tools-v2.png",
  accessories: "/catalog-media/accessories-v2.png",
  plants: "/plants/monstera-deliciosa-2.jpeg",
  peace: "/plants/spathiphyllum-wallisii-1.jpg",
  zamioculca: "/plants/zamioculcas-zamiifolia-1.jpg",
  agapanthus: "/plants/agapanthus-africanus-1.jpg",
  lantana: "/plants/lantana-camara-1.jpg",
};
const regions: Record<string, [number, number, number, number, number]> = {
  hero: [1, 595, 64, 880, 311],
  poster: [2, 0, 658, 277, 282],
  hibiscus: [3, 372, 184, 307, 212],
  monstera: [3, 700, 184, 301, 212],
  sword: [3, 1023, 184, 301, 212],
  jasmine: [3, 1341, 184, 300, 212],
  palm: [3, 372, 584, 307, 167],
  lavender: [3, 700, 584, 301, 167],
  boxwood: [3, 1023, 584, 301, 167],
  desert: [3, 1341, 584, 300, 167],
  zamioculca: [5, 394, 502, 47, 49],
  succulent: [3, 700, 584, 301, 167],
  peace: [8, 1253, 799, 25, 22],
  agapanthus: [8, 1253, 843, 25, 22],
  lantana: [9, 414, 878, 49, 35],
  plants: [1, 65, 551, 245, 102],
  pots: [1, 329, 551, 246, 102],
  substrate: [1, 594, 551, 229, 102],
  fertilizer: [1, 844, 551, 244, 102],
  tools: [1, 1105, 551, 236, 102],
  accessories: [1, 1361, 551, 247, 102],
  pruning: [1, 65, 804, 294, 65],
  maintenance: [1, 376, 804, 302, 65],
  irrigation: [1, 698, 804, 286, 65],
  consulting: [1, 1004, 804, 296, 65],
  landscape: [1, 1324, 804, 283, 65],
  installation: [7, 364, 617, 49, 47],
  hibiscusDetail: [4, 77, 117, 697, 368],
  hibiscus2: [4, 240, 499, 110, 74],
  hibiscus3: [4, 365, 499, 108, 74],
  hibiscus4: [4, 492, 499, 111, 74],
  hibiscus5: [4, 618, 499, 111, 74],
  plant1: [2, 570, 241, 52, 92],
  plant2: [2, 886, 242, 70, 91],
  plant3: [2, 1208, 239, 83, 96],
  plant4: [2, 1581, 239, 64, 98],
  avatar0: [6, 1215, 429, 101, 114],
  avatar1: [6, 341, 504, 26, 27],
  avatar2: [6, 341, 535, 26, 27],
};
export function Sprite({
  name,
  className = "",
  title,
}: {
  name: string;
  className?: string;
  title?: string;
}) {
  const r = regions[name] || regions.plants;
  const clipId = useId();
  if (catalogImages[name]) {
    return (
      <img
        className={`sprite ${className}`}
        src={catalogImages[name]}
        alt={title || ""}
        aria-hidden={!title}
        decoding="async"
      />
    );
  }
  return (
    <svg
      className={`sprite ${className}`}
      viewBox={`${r[1]} ${r[2]} ${r[3]} ${r[4]}`}
      preserveAspectRatio={
        name === "poster" ? "xMidYMin slice" : "xMidYMid slice"
      }
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={!title}
    >
      <defs>
        <clipPath id={clipId}>
          <rect x={r[1]} y={r[2]} width={r[3]} height={r[4]} />
        </clipPath>
      </defs>
      <image
        href={`/references/ref-${r[0]}.png`}
        width="1672"
        height="941"
        clipPath={`url(#${clipId})`}
      />
    </svg>
  );
}
export function Picture({
  item,
  className = "",
}: {
  item: Pick<Product | Species, "image_url" | "demo_asset" | "id"> & {
    category?: string;
    name?: string;
  };
  className?: string;
}) {
  return (
    <div
      className={`picture ${item.image_url?.startsWith("/catalog-media/products/") ? "item-picture" : ""} ${className}`}
    >
      {item.image_url ? (
        <Photo
          url={item.image_url}
          alt={item.name ? `Foto de ${item.name}` : "Foto cadastrada"}
        />
      ) : item.category && item.category !== "Plantas" ? (
        <div
          className="item-photo-placeholder"
          role="img"
          aria-label={`Sem foto de ${item.name || "produto"}`}
        >
          <ImageOff size={24} />
          <span>Imagem ainda não cadastrada</span>
        </div>
      ) : item.demo_asset ? (
        <Sprite name={item.demo_asset} />
      ) : (
        <Photo variant={item.id} />
      )}
    </div>
  );
}
export function Logo({
  dark = false,
  standalone = false,
}: {
  dark?: boolean;
  standalone?: boolean;
}) {
  return (
    <div
      className={`logo ${dark ? "light" : ""} ${standalone ? "standalone-logo" : ""}`}
    >
      <img
        className="company-logo"
        src={
          standalone
            ? "/rafinha/atelie-verde-logo-transparent.png"
            : "/rafinha/atelie-verde-logo.jpeg"
        }
        alt={standalone ? "Ateliê Verde — Jardinagem ao Paisagismo" : ""}
      />
      {!standalone && (
        <span>
          Ateliê Verde<small>Gestão de Jardinagem e Paisagismo</small>
        </span>
      )}
    </div>
  );
}
export function Avatar({
  name,
  url,
}: {
  name: string;
  index?: number;
  url?: string;
}) {
  return (
    <span className="avatar-photo" aria-label={name}>
      {url ? (
        <Photo url={url} />
      ) : (
        <span className="avatar-initials">
          {name
            .trim()
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((n) => n[0])
            .join("")
            .toUpperCase()}
        </span>
      )}
    </span>
  );
}
export function Status({ value }: { value: string }) {
  const label = value === "Solicitado" ? "Pendente" : value;
  const color = [
    "Aprovado",
    "Ativo",
    "Normal",
    "Disponível",
    "Confirmado",
    "Pago",
    "Em dia",
    "Concluído",
    "Cliente ativo",
  ].includes(label)
    ? "green"
    : [
          "Baixo",
          "Crítico",
          "Rejeitado",
          "Atrasado",
          "Cancelado",
          "Inativo",
        ].includes(label)
      ? "red"
      : ["Enviado"].includes(label)
        ? "purple"
        : ["Em análise", "Em execução"].includes(label)
          ? "blue"
          : "amber";
  return (
    <span className={`status ${color}`}>
      <i />
      {label}
    </span>
  );
}
export function Kpi({
  title,
  value,
  Icon,
  plant = 0,
  caption,
  change,
  red = false,
}: {
  title: string;
  value: string | number;
  Icon: LucideIcon;
  plant?: number;
  caption?: string;
  change?: number | null;
  red?: boolean;
}) {
  return (
    <article className="kpi">
      <span className={`round-icon ${red ? "red" : ""}`}>
        <Icon size={24} />
      </span>
      <div>
        <span>{title}</span>
        <strong>{value}</strong>
        {change !== undefined && change !== null ? (
          <>
            <b className={change < 0 || red ? "red-text" : "green-text"}>
              <ArrowUp size={15} />
              {change > 0 ? "+" : ""}
              {change.toLocaleString("pt-BR")}%
            </b>
            <small title="Em relação ao período anterior">
              vs. período anterior
            </small>
          </>
        ) : (
          <small>{caption || "Dados do período selecionado"}</small>
        )}
      </div>
      <img
        className="kpi-plant decorative-plant"
        src={`/decor/${["zamioculca", "buxinho", "costela", "rafis"][plant % 4]}.png`}
        alt=""
        aria-hidden="true"
      />
    </article>
  );
}
export function Panel({
  title,
  Icon = Leaf,
  children,
  actions,
  className = "",
}: {
  title: string;
  Icon?: LucideIcon;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <h2>
          <span className="round-icon small">
            <Icon size={22} />
          </span>
          {title}
        </h2>
        {actions}
      </div>
      <div className="panel-content">{children}</div>
    </section>
  );
}
export function SearchInput({
  placeholder = "Buscar…",
  value,
  onChange,
}: {
  placeholder?: string;
  value: string;
  onChange: (s: string) => void;
}) {
  return (
    <label className="search-input">
      <Search size={16} />
      <input
        aria-label={placeholder}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
export function Period() {
  const { period, setPeriod } = useGreen();
  return (
    <div className="period-picker">
      <CalendarDays size={17} />
      <input
        type="date"
        aria-label="Início do período"
        value={period.start}
        onChange={(e) => setPeriod({ ...period, start: e.target.value })}
      />
      <span>–</span>
      <input
        type="date"
        aria-label="Fim do período"
        value={period.end}
        onChange={(e) => setPeriod({ ...period, end: e.target.value })}
      />
    </div>
  );
}

export function YearSelect() {
  const { period, setPeriod } = useGreen();
  const current = new Date().getFullYear();
  return (
    <select
      aria-label="Ano do gráfico"
      value={period.end.slice(0, 4)}
      onChange={(e) =>
        setPeriod({
          start: e.target.value + "-01-01",
          end: e.target.value + "-12-31",
        })
      }
    >
      {Array.from({ length: 5 }, (_, i) => current - i).map((year) => (
        <option key={year}>{year}</option>
      ))}
    </select>
  );
}
export function QuickPeriod() {
  const { period, setPeriod } = useGreen();
  const [expanded, setExpanded] = useState(false),
    [draft, setDraft] = useState(period);
  const today = new Date().toLocaleDateString("sv-SE");
  const month = today.slice(0, 8) + "01",
    year = today.slice(0, 4) + "-01-01";
  const lastDate = new Date(today + "T12:00:00");
  lastDate.setDate(lastDate.getDate() - 29);
  const last30 = lastDate.toLocaleDateString("sv-SE");
  const value =
    period.start === month && period.end === today
      ? "month"
      : period.start === year &&
          (period.end === today || period.end === today.slice(0, 4) + "-12-31")
        ? "year"
        : period.start === last30 && period.end === today
          ? "last30"
          : "custom";
  return (
    <div className="quick-period">
      <select
        aria-label="Período do gráfico"
        value={value}
        onChange={(e) => {
          if (e.target.value === "custom") {
            setDraft(period);
            setExpanded(true);
          } else {
            setExpanded(false);
            setPeriod({
              start:
                e.target.value === "month"
                  ? month
                  : e.target.value === "year"
                    ? year
                    : last30,
              end: today,
            });
          }
        }}
      >
        <option value="month">Este mês</option>
        <option value="year">Este ano</option>
        <option value="last30">Últimos 30 dias</option>
        <option value="custom">Personalizado</option>
      </select>
      {value === "custom" && !expanded && (
        <button
          className="icon-button"
          aria-label="Editar período personalizado"
          onClick={() => {
            setDraft(period);
            setExpanded(true);
          }}
        >
          <CalendarDays size={14} />
        </button>
      )}
      {expanded && (
        <div
          className="quick-period-popover"
          role="group"
          aria-label="Período personalizado"
        >
          <label>
            De
            <input
              aria-label="Início do filtro do gráfico"
              type="date"
              value={draft.start}
              onChange={(e) => setDraft({ ...draft, start: e.target.value })}
            />
          </label>
          <label>
            Até
            <input
              aria-label="Fim do filtro do gráfico"
              type="date"
              min={draft.start}
              value={draft.end}
              onChange={(e) => setDraft({ ...draft, end: e.target.value })}
            />
          </label>
          <button
            className="button primary small"
            disabled={!draft.start || !draft.end || draft.end < draft.start}
            onClick={() => {
              setPeriod(draft);
              setExpanded(false);
            }}
          >
            Aplicar
          </button>
          <button className="text-button" onClick={() => setExpanded(false)}>
            Cancelar
          </button>
        </div>
      )}
    </div>
  );
}

export function Paginator({
  total,
  page,
  setPage,
  size = 10,
}: {
  total: number;
  page: number;
  setPage: (p: number) => void;
  size?: number;
}) {
  const pages = Math.max(1, Math.ceil(total / size));
  useEffect(() => {
    if (page > pages) setPage(pages);
  }, [page, pages, setPage]);
  const windowStart = Math.max(1, Math.min(page - 2, pages - 4));
  return (
    <div className="pagination">
      <span>
        Mostrando {total ? Math.min((page - 1) * size + 1, total) : 0} a{" "}
        {Math.min(page * size, total)} de {total} registros
      </span>
      <div>
        <button
          disabled={page <= 1}
          aria-label="Página anterior"
          onClick={() => setPage(page - 1)}
        >
          <ChevronLeft size={17} />
        </button>
        {page > 3 && pages > 5 && (
          <button aria-label="Primeira página" onClick={() => setPage(1)}>
            1
          </button>
        )}
        {Array.from(
          { length: Math.min(5, pages) },
          (_, i) => windowStart + i,
        ).map((p) => (
          <button
            key={p}
            className={p === page ? "active" : ""}
            aria-current={p === page ? "page" : undefined}
            onClick={() => setPage(p)}
          >
            {p}
          </button>
        ))}
        {windowStart + 4 < pages && (
          <button aria-label="Última página" onClick={() => setPage(pages)}>
            … {pages}
          </button>
        )}
        <button
          disabled={page >= pages}
          aria-label="Próxima página"
          onClick={() => setPage(page + 1)}
        >
          <ChevronRight size={17} />
        </button>
      </div>
    </div>
  );
}
export function Donut({
  values,
  center,
  subtitle,
}: {
  values: Record<string, number>;
  center: string;
  subtitle: string;
}) {
  const entries = Object.entries(values).filter(([, v]) => v > 0),
    total = entries.reduce((s, [, v]) => s + v, 0);
  const colors = [
    "#00803d",
    "#4e9a62",
    "#6a9e7c",
    "#87b299",
    "#83cc66",
    "#a9ddb1",
  ];
  let previous = 0;
  const sectors = entries.map(([name, v], i) => {
    const start = previous;
    previous += (v / Math.max(total, 1)) * 100;
    return `${colors[i % colors.length]} ${start}% ${previous}%`;
  });
  return (
    <div className="donut-wrap">
      <div
        className="donut"
        style={{
          background: total
            ? `conic-gradient(${sectors.join(",")})`
            : "#e9f1ed",
        }}
      >
        <div>
          <strong>
            {typeof center === "string" && center.startsWith("R$")
              ? "Total"
              : center}
          </strong>
          <span>{subtitle}</span>
        </div>
      </div>
      <div className="donut-legend">
        {typeof center === "string" && center.startsWith("R$") && (
          <p className="donut-total">{center}</p>
        )}
        {entries.map(([name, v], i) => (
          <div key={name}>
            <i style={{ background: colors[i % colors.length] }} />
            <span>{name}</span>
            <strong>{Math.round((v / total) * 100)}%</strong>
          </div>
        ))}
        {!entries.length && <p className="muted">Sem valores no período.</p>}
      </div>
    </div>
  );
}
export { CashChart } from "./CashChart";
export function exportCSV(
  filename: string,
  headers: string[],
  rows: unknown[][],
) {
  const escape = (value: unknown) => {
    const s = String(value ?? "");
    return '"' + (/^[=+@-]/.test(s) ? "'" : "") + s.replaceAll('"', '""') + '"';
  };
  const url = URL.createObjectURL(
    new Blob(
      [
        "\uFEFF" +
          [headers, ...rows].map((r) => r.map(escape).join(";")).join("\r\n"),
      ],
      { type: "text/csv;charset=utf-8" },
    ),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = filename + ".csv";
  a.click();
  URL.revokeObjectURL(url);
}
