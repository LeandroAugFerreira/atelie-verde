import type { Species } from "./types";

export function matchesPlantGroup(species: Species | undefined, group: string) {
  return !group || Boolean(species?.plant_groups?.includes(group));
}

export function plantGroupOptions(species: Species[]) {
  return [...new Set(species.flatMap((s) => s.plant_groups || []))]
    .sort((a, b) => a.localeCompare(b, "pt-BR"))
    .map((value) => ({ value, label: value }));
}
