import { useEffect, useRef, useState } from "react";
import { useGreen } from "./context";
import { money, dateLabel } from "./types";

export function CashChart({ financial = false }: { financial?: boolean }) {
  const { data, period } = useGreen();
  const svg = useRef<SVGSVGElement>(null);
  const [size, setSize] = useState({ width: 610, height: 208 });
  const [hover, setHover] = useState<number | null>(null);
  useEffect(() => {
    if (!svg.current) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) setSize({ width, height });
    });
    observer.observe(svg.current);
    return () => observer.disconnect();
  }, []);
  const values = data.analytics?.monthly || [];
  const max = Math.max(
    ...values.map((m) => Math.max(m.income, m.expense)),
    100,
  );
  const min = financial
    ? Math.min(0, ...values.map((m) => m.income - m.expense))
    : 0;
  const bottom = size.height - 24;
  const y = (value: number) =>
    bottom - ((value - min) / (max - min)) * Math.max(10, bottom - 14);
  const step = (size.width - 74) / Math.max(values.length - 1, 1);
  const x = (i: number) => 50 + i * step;
  const bar = Math.max(3, Math.min(15, step * 0.3));
  const points = values
    .map((m, i) => `${x(i)},${y(financial ? m.income - m.expense : m.income)}`)
    .join(" ");
  const active = hover === null ? undefined : values[hover];
  const tooltipX =
    hover === null ? 50 : Math.max(0, Math.min(x(hover), size.width - 210));
  return (
    <div className="chart-wrap">
      <svg
        ref={svg}
        viewBox={`0 0 ${size.width} ${size.height}`}
        className="cash-chart"
        aria-label="Valores mensais"
        role="img"
      >
        {(size.height < 120 ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1]).map(
          (fraction) => (
            <g key={fraction}>
              <line
                x1="48"
                x2={size.width - 10}
                y1={y(min + (max - min) * fraction)}
                y2={y(min + (max - min) * fraction)}
                stroke="#e8eeee"
              />
              <text
                x="42"
                y={y(min + (max - min) * fraction) + 3}
                textAnchor="end"
              >
                {Math.round(
                  (min + (max - min) * fraction) / 100,
                ).toLocaleString("pt-BR")}
              </text>
            </g>
          ),
        )}
        {!financial && values.length > 0 && (
          <polygon
            points={`${x(0)},${y(0)} ${points} ${x(values.length - 1)},${y(0)}`}
            fill="#149350"
            opacity=".10"
          />
        )}
        {values.map((m, i) => (
          <g
            key={m.month}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          >
            <rect
              x={x(i) - step / 2}
              y="0"
              width={step}
              height={bottom + 10}
              fill="transparent"
            />
            {financial && (
              <>
                <rect
                  x={x(i) - bar - 1}
                  y={y(m.income)}
                  width={bar}
                  height={Math.max(0, y(0) - y(m.income))}
                  rx="2"
                  fill="#68b87a"
                />
                <rect
                  x={x(i) + 1}
                  y={y(m.expense)}
                  width={bar}
                  height={Math.max(0, y(0) - y(m.expense))}
                  rx="2"
                  fill="#ff7f88"
                />
              </>
            )}
            <text x={x(i)} y={size.height - 6} textAnchor="middle">
              {new Date(m.month + "-15T12:00:00")
                .toLocaleDateString("pt-BR", { month: "short" })
                .replace(".", "")}
            </text>
          </g>
        ))}
        <polyline
          points={points}
          fill="none"
          stroke="#06613a"
          strokeWidth="2"
        />
        {values.map((m, i) => (
          <circle
            key={m.month}
            cx={x(i)}
            cy={y(financial ? m.income - m.expense : m.income)}
            r="3"
            stroke="#005c30"
            strokeWidth="1.5"
            fill="#73ba8b"
          />
        ))}
        {active && (
          <g pointerEvents="none">
            <rect
              x={tooltipX}
              y="0"
              width="210"
              height={financial ? 64 : 44}
              rx="6"
              fill="#033f28"
            />
            <text x={tooltipX + 10} y="14" className="tooltip-text">
              {dateLabel(active.month + "-01").slice(3)}
            </text>
            <text x={tooltipX + 10} y="29" className="tooltip-text">
              Receitas: {money(active.income)}
            </text>
            {financial && (
              <text x={tooltipX + 10} y="45" className="tooltip-text">
                Despesas: {money(active.expense)}
              </text>
            )}
            {financial && (
              <text x={tooltipX + 10} y="59" className="tooltip-text">
                Saldo: {money(active.income - active.expense)}
              </text>
            )}
          </g>
        )}
      </svg>
      <span className="chart-year">
        Ano {period.end.slice(0, 4)} · valores em R$
      </span>
    </div>
  );
}
