import { useRef, useState } from "react";
import { Download } from "lucide-react";
import type { LandscapeBrief, Species } from "./types";

const colors: Record<string, string> = {
  Canteiro: "#dbccb5",
  Caminho: "#dedbd4",
  Deck: "#c7966d",
  Gramado: "#b9d790",
  Construção: "#cdd6df",
  Água: "#a6dbe7",
};
export function downloadFile(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function LandscapePlan({
  brief,
  species,
  onMove,
}: {
  brief: LandscapeBrief;
  species: Species[];
  onMove?: (index: number, x: number, y: number) => void;
}) {
  const svg = useRef<SVGSVGElement>(null),
    [drag, setDrag] = useState<number | null>(null);
  const width = Math.max(1, Number(brief.width) || 1),
    length = Math.max(1, Number(brief.length) || 1),
    pad = Math.max(width, length) * 0.12,
    font = Math.max(width, length) * 0.028;
  function move(e: React.PointerEvent<SVGGElement>, index: number) {
    if (drag !== index || !onMove || !svg.current) return;
    const matrix = svg.current.getScreenCTM();
    if (!matrix) return;
    const point = svg.current.createSVGPoint();
    point.x = e.clientX;
    point.y = e.clientY;
    const local = point.matrixTransform(matrix.inverse());
    onMove(
      index,
      Math.round(Math.max(0, Math.min(width, local.x - pad)) * 10) / 10,
      Math.round(Math.max(0, Math.min(length, local.y - pad)) * 10) / 10,
    );
  }
  return (
    <div className="landscape-preview">
      <div className="section-heading">
        <h3>Planta 2D do espaço</h3>
        <button
          type="button"
          className="text-button"
          onClick={() => {
            if (svg.current)
              downloadFile(
                "atelie-verde-planta.svg",
                svg.current.outerHTML,
                "image/svg+xml",
              );
          }}
        >
          <Download size={15} />
          Baixar planta
        </button>
      </div>
      <svg
        ref={svg}
        xmlns="http://www.w3.org/2000/svg"
        viewBox={`0 0 ${width + 2 * pad} ${length + 2 * pad}`}
        role="img"
        aria-label="Planta 2D do projeto paisagístico"
        className="landscape-svg"
      >
        <title>
          Planejamento paisagístico — {width} × {length} metros
        </title>
        <rect
          x={pad}
          y={pad}
          width={width}
          height={length}
          fill="#e8f1de"
          stroke="#527851"
          strokeWidth={font * 0.12}
        />
        <text
          x={pad + width / 2}
          y={pad * 0.65}
          fontSize={font}
          textAnchor="middle"
          fill="#294d32"
        >
          {width} m
        </text>
        <text
          x={pad * 0.5}
          y={pad + length / 2}
          fontSize={font}
          textAnchor="middle"
          transform={`rotate(-90 ${pad * 0.5} ${pad + length / 2})`}
          fill="#294d32"
        >
          {length} m
        </text>
        {brief.zones.map((zone, i) => (
          <g key={`z${i}`}>
            <rect
              x={pad + zone.x}
              y={pad + zone.y}
              width={zone.width}
              height={zone.length}
              rx={font * 0.2}
              fill={colors[zone.kind] || colors.Canteiro}
              stroke="#789376"
              strokeWidth={font * 0.1}
            />
            <text
              x={pad + zone.x + zone.width / 2}
              y={pad + zone.y + zone.length / 2}
              fontSize={font * 0.7}
              textAnchor="middle"
              fill="#42563e"
            >
              {zone.name}
            </text>
          </g>
        ))}
        {brief.plantings.map((plant, i) => {
          const name =
            species.find((s) => s.id === plant.species_id)?.name || "Espécie";
          return (
            <g
              key={`p${i}`}
              onPointerDown={
                onMove
                  ? (e) => {
                      e.currentTarget.setPointerCapture(e.pointerId);
                      setDrag(i);
                    }
                  : undefined
              }
              onPointerMove={(e) => move(e, i)}
              onPointerUp={() => setDrag(null)}
              onPointerCancel={() => setDrag(null)}
              style={{
                cursor: onMove ? "grab" : "default",
                touchAction: "none",
              }}
            >
              <title>
                {name} · {plant.quantity} unidade(s) · {plant.application}
              </title>
              <circle
                cx={pad + plant.x}
                cy={pad + plant.y}
                r={plant.diameter / 2}
                fill={i % 2 ? "#589c66" : "#237e49"}
                fillOpacity="0.8"
                stroke="#fff"
                strokeWidth={font * 0.14}
              />
              <text
                x={pad + plant.x}
                y={pad + plant.y + font * 0.3}
                textAnchor="middle"
                fontSize={font}
                fontWeight="bold"
                fill="white"
              >
                {i + 1}
              </text>
            </g>
          );
        })}
        <g
          transform={`translate(${pad + width + pad * 0.45},${pad * 0.65}) rotate(${brief.north})`}
        >
          <path
            d={`M0 ${font * 1.6} L0 0 M${-font * 0.3} ${font * 0.5} L0 0 L${font * 0.3} ${font * 0.5}`}
            stroke="#294d32"
            strokeWidth={font * 0.12}
            fill="none"
          />
          <text
            y={-font * 0.25}
            textAnchor="middle"
            fontSize={font * 0.75}
            fill="#294d32"
          >
            N
          </text>
        </g>
      </svg>
      <p className="form-hint">
        Prévia esquemática em metros. Cada número representa um grupo de
        plantas; a distribuição e os espaçamentos precisam da revisão do
        paisagista.
        {onMove && " Arraste os círculos para posicionar as plantas."}
      </p>
      <ol className="landscape-legend">
        {brief.plantings.map((plant, i) => (
          <li key={i}>
            <b>{i + 1}</b>
            <span>
              {species.find((s) => s.id === plant.species_id)?.name} ·{" "}
              {plant.quantity} un.
              <small>{plant.application || "Aplicação a definir"}</small>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function exportMemorial(
  brief: LandscapeBrief,
  species: Species[],
  address: string,
) {
  const esc = (value: unknown) =>
    String(value ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c]!,
    );
  const rows = brief.plantings
    .map((p, i) => {
      const s = species.find((s) => s.id === p.species_id);
      return `<tr><td>${i + 1}</td><td>${esc(s?.name)}<br><i>${esc(s?.scientific_name)}</i></td><td>${p.quantity}</td><td>${esc(p.application)}</td><td>${esc(s?.light)} / ${esc(s?.watering_frequency)}</td></tr>`;
    })
    .join("");
  const plan =
    (
      document.querySelector<SVGSVGElement>(".modal .landscape-svg") ||
      document.querySelector<SVGSVGElement>(".landscape-svg")
    )?.outerHTML || "";
  downloadFile(
    "atelie-verde-memorial.html",
    `<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Ateliê Verde — Memorial do planejamento</title><style>body{font:15px Arial;color:#143b25;max-width:1000px;margin:40px auto;padding:20px}svg{width:100%;height:420px}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}p{line-height:1.6}@media print{body{margin:0}button{display:none}}</style><h1>Ateliê Verde · Memorial do planejamento</h1><p>Local: ${esc(address)}</p><p>Área: ${brief.width * brief.length} m² (${brief.width} × ${brief.length} m). Luminosidade: ${esc(brief.light)}. Solo: ${esc(brief.soil)}. Drenagem: ${esc(brief.drainage)}. Manutenção: ${esc(brief.maintenance)}.</p><h2>Objetivos</h2><p>${esc(brief.objective)}</p>${plan}<h2>Espécies selecionadas</h2><table><tr><th>#</th><th>Espécie</th><th>Qtd.</th><th>Aplicação</th><th>Cuidados</th></tr>${rows}</table><h2>Áreas</h2><ul>${brief.zones.map((z) => `<li>${esc(z.name)} (${esc(z.kind)}): ${z.width} × ${z.length} m</li>`).join("")}</ul><h2>Observações</h2><p>${esc(brief.notes)}</p><p>Prévia de planejamento, sujeita à revisão técnica do paisagista. Abra este documento no navegador e use Imprimir para salvar uma cópia PDF.</p></html>`,
    "text/html;charset=utf-8",
  );
}
