import type { LandscapeBrief, LayoutPlant, Species } from "./types";
export const emptyBrief: LandscapeBrief = {
  width: 10,
  length: 8,
  north: 0,
  light: "Misto",
  soil: "Não avaliado",
  drainage: "Não avaliada",
  maintenance: "Baixa",
  objective: "",
  notes: "",
  plantings: [],
  zones: [],
};
const normalize = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
function csv(text: string) {
  const delimiter = text.split(/\r?\n/)[0].includes(";") ? ";" : ",";
  const rows: string[][] = [];
  let row: string[] = [],
    value = "",
    quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') {
        value += '"';
        i++;
      } else quoted = !quoted;
    } else if (c === delimiter && !quoted) {
      row.push(value);
      value = "";
    } else if ((c === "\n" || c === "\r") && !quoted) {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(value);
      if (row.some(Boolean)) rows.push(row);
      row = [];
      value = "";
    } else value += c;
  }
  if (quoted) throw new Error("CSV com aspas incompletas.");
  row.push(value);
  if (row.some(Boolean)) rows.push(row);
  const headers =
    rows.shift()?.map((h) => normalize(h.replace(/^\uFEFF/, ""))) || [];
  return rows.map((row) =>
    Object.fromEntries(headers.map((key, i) => [key, row[i] ?? ""])),
  );
}
export function importLandscape(
  text: string,
  format: string,
  species: Species[],
  base: LandscapeBrief,
): LandscapeBrief {
  const parsed = format === "csv" ? csv(text) : JSON.parse(text);
  if (!Array.isArray(parsed) && (!parsed || typeof parsed !== "object"))
    throw new Error(
      "Importe um objeto de planejamento ou uma lista de plantas.",
    );
  if (
    !Array.isArray(parsed) &&
    Object.keys(parsed).some(
      (key) => !Object.keys(emptyBrief).includes(key) && key !== "plantas",
    )
  )
    throw new Error(
      "O JSON possui campos não reconhecidos. Use o arquivo exportado pelo planejador.",
    );
  const items = Array.isArray(parsed)
    ? parsed
    : parsed.plantings || parsed.plantas || [];
  if (!Array.isArray(items) || items.length > 200)
    throw new Error("Importe até 200 grupos de plantas.");
  const result: LandscapeBrief = {
    ...base,
    ...(!Array.isArray(parsed) ? parsed : {}),
    plantings: [],
  };
  delete (result as unknown as Record<string, unknown>).plantas;
  result.width = Number(result.width);
  result.length = Number(result.length);
  if (
    !Number.isFinite(Number(result.width)) ||
    !Number.isFinite(Number(result.length)) ||
    result.width <= 0 ||
    result.length <= 0 ||
    result.width > 500 ||
    result.length > 500
  )
    throw new Error("Informe largura e comprimento válidos.");
  const number = (value: unknown, fallback: number) =>
    value === undefined || value === ""
      ? fallback
      : Number(String(value).replace(",", "."));
  if (
    !Number.isInteger(result.north) ||
    result.north < 0 ||
    result.north > 359 ||
    !["Misto", "Sol pleno", "Meia-sombra", "Sombra"].includes(result.light) ||
    !["Não avaliada", "Boa", "Regular", "Ruim"].includes(result.drainage) ||
    !["Baixa", "Média", "Alta"].includes(result.maintenance) ||
    typeof result.soil !== "string" ||
    typeof result.objective !== "string" ||
    typeof result.notes !== "string"
  )
    throw new Error(
      "Confira orientação e informações do terreno no arquivo JSON.",
    );
  if (!Array.isArray(result.zones) || result.zones.length > 100)
    throw new Error("Importe até 100 áreas.");
  result.zones = result.zones.map((zone, i) => {
    if (
      !zone ||
      typeof zone.name !== "string" ||
      zone.name.length < 2 ||
      !Object.keys({
        Canteiro: 1,
        Caminho: 1,
        Deck: 1,
        Gramado: 1,
        Construção: 1,
        Água: 1,
      }).includes(zone.kind)
    )
      throw new Error(`Área ${i + 1}: confira nome e tipo.`);
    const z = {
      ...zone,
      x: Number(zone.x),
      y: Number(zone.y),
      width: Number(zone.width),
      length: Number(zone.length),
    };
    if (
      ![z.x, z.y, z.width, z.length].every(Number.isFinite) ||
      z.x < 0 ||
      z.y < 0 ||
      z.width <= 0 ||
      z.length <= 0 ||
      z.x + z.width > result.width ||
      z.y + z.length > result.length
    )
      throw new Error(
        `Área ${i + 1}: confira as medidas e os limites do terreno.`,
      );
    return z;
  });
  result.plantings = items.map((row: Record<string, unknown>, i: number) => {
    const match = species.find(
      (s) =>
        s.id === Number(row.species_id) ||
        [s.name, s.scientific_name].some(
          (name) =>
            normalize(name) ===
            normalize(
              String(row.especie || row.species_name || row.name || ""),
            ),
        ),
    );
    if (!match)
      throw new Error(`Linha ${i + 1}: espécie não encontrada na biblioteca.`);
    const plant: LayoutPlant = {
      species_id: match.id,
      quantity: number(row.quantity ?? row.quantidade, 1),
      x: number(row.x ?? row.x_m, (result.width * ((i % 5) + 1)) / 6),
      y: number(
        row.y ?? row.y_m,
        (result.length * (Math.floor(i / 5) + 1)) /
          (Math.ceil(items.length / 5) + 1),
      ),
      diameter: number(row.diameter ?? row.diametro_m, 1),
      application: String(row.application ?? row.aplicacao ?? ""),
    };
    if (
      !Number.isInteger(plant.quantity) ||
      plant.quantity < 1 ||
      plant.quantity > 10000 ||
      !Number.isFinite(plant.x) ||
      !Number.isFinite(plant.y) ||
      plant.x < 0 ||
      plant.y < 0 ||
      plant.x > result.width ||
      plant.y > result.length ||
      !Number.isFinite(plant.diameter) ||
      plant.diameter <= 0 ||
      plant.diameter > 100
    )
      throw new Error(
        `Linha ${i + 1}: confira quantidade, posições e diâmetro.`,
      );
    return plant;
  });
  return result;
}
