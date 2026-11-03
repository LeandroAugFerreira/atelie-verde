import { useId, useState } from "react";
import { Filter, RotateCcw, ChevronDown } from "lucide-react";
import { SearchInput } from "./ReferenceUI";

export type FilterField = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options?: { value: string; label: string }[];
  type?: "date";
};

export const filterOptions = (values: string[], all = "Todos") => [
  { value: "", label: all },
  ...[...new Set(values)]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "pt-BR"))
    .map((value) => ({ value, label: value })),
];

export function AdminFilters({
  search,
  onSearch,
  placeholder,
  fields,
  count,
  onClear,
}: {
  search: string;
  onSearch: (value: string) => void;
  placeholder: string;
  fields: FilterField[];
  count: number;
  onClear: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const id = useId();
  const active = fields.filter((f) => f.value).length;
  return (
    <div
      className="admin-filters"
      onKeyDown={(e) => {
        if (e.key === "Escape") setExpanded(false);
      }}
    >
      <div className="admin-filter-bar">
        <SearchInput
          placeholder={placeholder}
          value={search}
          onChange={onSearch}
        />
        <button
          className={`button secondary filter-toggle ${active ? "has-filters" : ""}`}
          aria-expanded={expanded}
          aria-controls={id}
          onClick={() => setExpanded(!expanded)}
        >
          <Filter size={16} />
          Filtros{active > 0 && <span>{active}</span>}
          <ChevronDown size={14} />
        </button>
        {(active > 0 || search.trim()) && (
          <button
            className="text-button filter-clear"
            aria-label="Limpar filtros"
            onClick={onClear}
          >
            <RotateCcw size={14} />
            Limpar
          </button>
        )}
        <span className="filter-count" role="status">
          {count} {count === 1 ? "resultado" : "resultados"}
        </span>
      </div>
      {expanded && (
        <div
          id={id}
          className="admin-filter-fields"
          role="region"
          aria-label="Filtros avançados"
        >
          {fields.map((f) => (
            <label key={f.label}>
              {f.label}
              {f.type === "date" ? (
                <input
                  aria-label={f.label}
                  type="date"
                  value={f.value}
                  onChange={(e) => f.onChange(e.target.value)}
                />
              ) : (
                <select
                  aria-label={f.label}
                  value={f.value}
                  onChange={(e) => f.onChange(e.target.value)}
                >
                  {f.options?.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              )}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
