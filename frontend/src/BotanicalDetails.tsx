import { ExternalLink, Leaf } from "lucide-react";
import { Gallery } from "./components";
import { Picture } from "./ReferenceUI";
import { useGreen } from "./context";
import { AskRafinha } from "./RafinhaAssistant";
import type { Species, Source, PlantPhoto } from "./types";

export function Sources({ items }: { items?: Source[] }) {
  if (!items?.length) return null;
  return (
    <div className="botanical-sources">
      <h4>Fontes consultadas</h4>
      {items.map((s) => (
        <a key={s.url} href={s.url} target="_blank" rel="noreferrer">
          {s.title}
          <ExternalLink size={13} />
        </a>
      ))}
      <small>
        Consulta em 04/10/2026. As condições locais de clima, vaso e solo
        influenciam o cultivo.
      </small>
    </div>
  );
}

export function PhotoCredits({
  photos,
  expanded = false,
}: {
  photos?: PlantPhoto[];
  expanded?: boolean;
}) {
  if (!photos?.length) return null;
  return (
    <details className="photo-credits" open={expanded}>
      <summary>Créditos das fotografias</summary>
      {photos.map((p, i) => (
        <div key={p.url}>
          <a href={p.source_url} target="_blank" rel="noreferrer">
            Foto {i + 1} · {p.author}
          </a>
          <a href={p.license_url} target="_blank" rel="noreferrer">
            {p.license}
          </a>
          <small>{p.changes}</small>
        </div>
      ))}
    </details>
  );
}

export function SpeciesDetail({ species: s }: { species: Species }) {
  const { user, reload, open, data, go } = useGreen();
  const product = data.products.find((p) => p.active && p.species_id === s.id);
  return (
    <div className="detail botanical-detail">
      <Picture item={s} className="species-detail-photo" />
      <h2>{s.name}</h2>
      <AskRafinha context={{ kind: "species", id: s.id, label: s.name }} />
      <i>{s.scientific_name}</i>
      <p>{s.description}</p>
      <div className="form-grid">
        {[
          ["Luminosidade", s.light],
          ["Como regar", s.watering_frequency || s.watering],
          ["Porte adulto", s.height || s.size],
          ["Ambiente", s.environment],
          ["Manutenção", s.difficulty],
          ["Uso", s.use],
          ["Família", s.family],
          ["Origem", s.origin],
        ].map(([label, value]) => (
          <div key={label}>
            <small>{label}</small>
            <strong className="block">{value || "Não informado"}</strong>
          </div>
        ))}
      </div>
      {[
        ["Cuidados", s.care],
        ["Substrato", s.substrate],
        ["Propagação", s.propagation],
        ["Precauções", s.precautions],
      ]
        .filter(([, v]) => v)
        .map(([label, value]) => (
          <section className="care-note" key={label}>
            <h3>
              <Leaf size={16} />
              {label}
            </h3>
            <p>{value}</p>
          </section>
        ))}
      {user.role !== "admin" && product && (
        <button
          className="button primary"
          onClick={() => go("product", product.id)}
        >
          Ver na loja
        </button>
      )}
      <Sources items={s.sources} />
      <PhotoCredits photos={s.photos} />
      <Gallery
        entity="species"
        id={s.id}
        editable={user.role === "admin"}
        onChange={reload}
      />
      {user.role === "admin" && (
        <button
          className="button secondary"
          onClick={() => open("entity", { entity: "species", record: s })}
        >
          Editar espécie
        </button>
      )}
    </div>
  );
}
