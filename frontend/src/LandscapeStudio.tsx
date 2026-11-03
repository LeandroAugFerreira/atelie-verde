import { useState } from "react";
import { Plus, Trash2, Upload, Download, FileText } from "lucide-react";
import { api, write } from "./api";
import { useGreen } from "./context";
import { SaveButton } from "./components";
import { LandscapePlan, downloadFile, exportMemorial } from "./LandscapePlan";
import { emptyBrief, importLandscape } from "./landscapeImport";
import type {
  LandscapeBrief,
  LayoutZone,
  Quote,
  Project,
  Service,
} from "./types";

export function LandscapeStudio({
  service: provided,
  quote,
  project,
}: {
  service?: Service;
  quote?: Quote;
  project?: Project;
}) {
  const { data, user, reload, go, toast } = useGreen();
  const service =
    provided ||
    data.services.find(
      (s) =>
        s.id ===
        (quote?.service_id ||
          data.quotes.find((q) => q.id === project?.quote_id)?.service_id),
    ) ||
    data.services.find((s) => s.category === "Projeto");
  const [brief, setBrief] = useState<LandscapeBrief>(
    quote?.brief?.width
      ? structuredClone(quote.brief)
      : project?.brief?.width
        ? structuredClone(project.brief)
        : (() => {
            const previous = quote?.plants || project?.plants || [];
            const width = 10,
              length = (quote?.area || project?.area || 80) / 10;
            return {
              ...structuredClone(emptyBrief),
              width,
              length,
              plantings: previous.map((plant, i) => ({
                ...plant,
                application: plant.application || "",
                x: (width * ((i % 5) + 1)) / 6,
                y:
                  (length * (Math.floor(i / 5) + 1)) /
                  (Math.ceil(previous.length / 5) + 1),
                diameter: Math.min(1, width, length),
              })),
            };
          })(),
  );
  const [address, setAddress] = useState(
      quote?.address || project?.address || user.address || "",
    ),
    [tab, setTab] = useState("Dados"),
    [speciesId, setSpeciesId] = useState(data.species[0]?.id || 0),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [pending, setPending] = useState<File[]>([]),
    [savedId, setSavedId] = useState<number | undefined>(quote?.id),
    [revision, setRevision] = useState(
      quote?.brief_revision || project?.brief_revision || 0,
    );
  const update = (key: keyof LandscapeBrief, value: unknown) =>
    setBrief((b) => ({ ...b, [key]: value }));
  function importFile(file: File | undefined) {
    if (!file) return;
    if (file.size > 1024 * 1024) {
      setError("Arquivo de dados limitado a 1 MB.");
      return;
    }
    file
      .text()
      .then((text) => {
        setBrief(
          importLandscape(
            text,
            file.name.toLowerCase().endsWith(".csv") ? "csv" : "json",
            data.species,
            brief,
          ),
        );
        setError("");
      })
      .catch((e) => setError((e as Error).message));
  }
  async function save() {
    setBusy(true);
    setError("");
    let id = savedId;
    try {
      if (address.trim().length < 5)
        throw new Error("Informe o endereço do projeto.");
      if (!service && !project)
        throw new Error("Selecione um serviço de paisagismo.");
      if (project) {
        const result = await write<Project>(
          `/projects/${project.id}/brief`,
          { brief, address, expected_revision: revision },
          "PUT",
        );
        setRevision(result.brief_revision);
      } else if (id) {
        const result = await write<Quote>(
          `/quotes/${id}/brief`,
          { brief, address, expected_revision: revision },
          "PUT",
        );
        setRevision(result.brief_revision);
      } else {
        const result = await write<Quote>("/quotes", {
          service_id: service!.id,
          area: brief.width * brief.length,
          address,
          description:
            brief.objective || "Solicitação de planejamento paisagístico",
          brief,
        });
        id = result.id;
        setSavedId(id);
        setRevision(result.brief_revision);
      }
      const entity = project ? "projects" : "quotes",
        entityId = project?.id || id;
      for (const file of pending) {
        const form = new FormData();
        form.append("file", file);
        await api(
          file.type === "application/pdf" ||
            file.name.toLowerCase().endsWith(".pdf")
            ? `/${entity}/${entityId}/documents`
            : `/images/${entity}/${entityId}`,
          { method: "POST", body: form },
        );
        setPending((items) => items.filter((item) => item !== file));
      }
      await reload();
      go(project ? "project" : "quotes", project?.id);
      toast(
        project
          ? "Planta do projeto atualizada."
          : "Solicitação enviada com o planejamento e os anexos.",
      );
    } catch (e) {
      setError(
        (e as Error).message +
          (id && !quote
            ? " A solicitação já foi salva; você pode continuar pelos seus orçamentos."
            : ""),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="landscape-studio">
      <div className="studio-toolbar">
        <span>
          {project
            ? "Revisão do planejamento"
            : `Paisagista ${service?.delivery_mode?.toLowerCase() || "presencial"}`}{" "}
          · {brief.width * brief.length || 0} m²
        </span>
        <div>
          <label className="button secondary small">
            <Upload size={15} />
            Importar dados e plantas
            <input
              type="file"
              accept=".json,.csv"
              aria-label="Importar dados e plantas"
              hidden
              onChange={(e) => {
                importFile(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </label>
          <button
            type="button"
            className="text-button"
            onClick={() =>
              downloadFile(
                "modelo-plantas.csv",
                "especie;quantidade;x_m;y_m;diametro_m;aplicacao\nHibisco;6;2;3;1;Canteiro frontal\nLavanda;8;5;2;1;Bordadura\n",
                "text/csv;charset=utf-8",
              )
            }
          >
            <Download size={14} />
            Modelo CSV
          </button>
        </div>
      </div>
      <div className="studio-columns">
        <section className="studio-editor">
          <nav className="studio-tabs">
            {["Dados", "Plantas", "Áreas", "Arquivos"].map((name) => (
              <button
                type="button"
                key={name}
                className={name === tab ? "selected" : ""}
                onClick={() => setTab(name)}
              >
                {name}
              </button>
            ))}
          </nav>
          <div className="studio-fields">
            {tab === "Dados" && (
              <div className="form-grid">
                <label className="full">
                  Endereço do projeto
                  <input
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    maxLength={500}
                  />
                </label>
                {[
                  ["width", "Largura (m)"],
                  ["length", "Comprimento (m)"],
                  ["north", "Orientação norte (°)"],
                ].map(([key, label]) => (
                  <label key={key}>
                    {label}
                    <input
                      type="number"
                      min={key === "north" ? 0 : 0.1}
                      max={key === "north" ? 359 : 500}
                      step={key === "north" ? 1 : 0.1}
                      value={Number(brief[key as keyof LandscapeBrief])}
                      onChange={(e) =>
                        update(
                          key as keyof LandscapeBrief,
                          Number(e.target.value),
                        )
                      }
                    />
                  </label>
                ))}
                <label>
                  Luminosidade
                  <select
                    value={brief.light}
                    onChange={(e) => update("light", e.target.value)}
                  >
                    {["Misto", "Sol pleno", "Meia-sombra", "Sombra"].map(
                      (v) => (
                        <option key={v}>{v}</option>
                      ),
                    )}
                  </select>
                </label>
                <label>
                  Drenagem
                  <select
                    value={brief.drainage}
                    onChange={(e) => update("drainage", e.target.value)}
                  >
                    {["Não avaliada", "Boa", "Regular", "Ruim"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Manutenção desejada
                  <select
                    value={brief.maintenance}
                    onChange={(e) => update("maintenance", e.target.value)}
                  >
                    {["Baixa", "Média", "Alta"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label className="full">
                  Solo e condições existentes
                  <input
                    value={brief.soil}
                    maxLength={500}
                    onChange={(e) => update("soil", e.target.value)}
                  />
                </label>
                <label className="full">
                  Objetivos e estilo
                  <textarea
                    value={brief.objective}
                    maxLength={1000}
                    rows={2}
                    onChange={(e) => update("objective", e.target.value)}
                  />
                </label>
                <label className="full">
                  Observações
                  <textarea
                    value={brief.notes}
                    maxLength={3000}
                    rows={2}
                    onChange={(e) => update("notes", e.target.value)}
                  />
                </label>
              </div>
            )}
            {tab === "Plantas" && (
              <>
                <div className="studio-add">
                  <label>
                    Espécie da biblioteca
                    <select
                      value={speciesId}
                      onChange={(e) => setSpeciesId(Number(e.target.value))}
                    >
                      {data.species.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} · {s.light}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="button primary small"
                    disabled={!speciesId || brief.plantings.length >= 200}
                    onClick={() =>
                      update("plantings", [
                        ...brief.plantings,
                        {
                          species_id: speciesId,
                          quantity: 1,
                          x: brief.width / 2,
                          y: brief.length / 2,
                          diameter: 1,
                          application: "",
                        },
                      ])
                    }
                  >
                    <Plus size={15} />
                    Adicionar planta
                  </button>
                </div>
                {brief.plantings.map((plant, i) => (
                  <div className="studio-item" key={i}>
                    <div className="section-heading">
                      <strong>
                        {i + 1}.{" "}
                        {
                          data.species.find((s) => s.id === plant.species_id)
                            ?.name
                        }
                      </strong>
                      <button
                        type="button"
                        className="icon-button"
                        aria-label={`Remover grupo de plantas ${i + 1}`}
                        onClick={() =>
                          update(
                            "plantings",
                            brief.plantings.filter((_, j) => i !== j),
                          )
                        }
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                    <div className="form-grid">
                      {[
                        ["quantity", "Quantidade"],
                        ["x", "Posição X (m)"],
                        ["y", "Posição Y (m)"],
                        ["diameter", "Diâmetro no desenho (m)"],
                      ].map(([key, label]) => (
                        <label key={key}>
                          {label}
                          <input
                            type="number"
                            min={key === "x" || key === "y" ? 0 : 0.1}
                            step={key === "quantity" ? 1 : 0.1}
                            value={plant[key as keyof typeof plant]}
                            onChange={(e) =>
                              update(
                                "plantings",
                                brief.plantings.map((p, j) =>
                                  i === j
                                    ? { ...p, [key]: Number(e.target.value) }
                                    : p,
                                ),
                              )
                            }
                          />
                        </label>
                      ))}
                      <label className="full">
                        Aplicação
                        <input
                          value={plant.application}
                          maxLength={200}
                          onChange={(e) =>
                            update(
                              "plantings",
                              brief.plantings.map((p, j) =>
                                i === j
                                  ? { ...p, application: e.target.value }
                                  : p,
                              ),
                            )
                          }
                        />
                      </label>
                    </div>
                  </div>
                ))}
              </>
            )}
            {tab === "Áreas" && (
              <>
                <button
                  type="button"
                  className="button secondary small"
                  disabled={brief.zones.length >= 100}
                  onClick={() =>
                    update("zones", [
                      ...brief.zones,
                      {
                        name: "Novo canteiro",
                        kind: "Canteiro",
                        x: 0,
                        y: 0,
                        width: Math.min(2, brief.width),
                        length: Math.min(2, brief.length),
                      },
                    ])
                  }
                >
                  <Plus size={15} />
                  Adicionar área
                </button>
                {brief.zones.map((zone, i) => (
                  <div className="studio-item" key={i}>
                    <div className="section-heading">
                      <strong>Área {i + 1}</strong>
                      <button
                        type="button"
                        className="icon-button"
                        aria-label={`Remover área ${i + 1}`}
                        onClick={() =>
                          update(
                            "zones",
                            brief.zones.filter((_, j) => i !== j),
                          )
                        }
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                    <div className="form-grid">
                      <label>
                        Nome
                        <input
                          value={zone.name}
                          maxLength={80}
                          onChange={(e) =>
                            update(
                              "zones",
                              brief.zones.map((z, j) =>
                                i === j ? { ...z, name: e.target.value } : z,
                              ),
                            )
                          }
                        />
                      </label>
                      <label>
                        Tipo
                        <select
                          value={zone.kind}
                          onChange={(e) =>
                            update(
                              "zones",
                              brief.zones.map((z, j) =>
                                i === j
                                  ? {
                                      ...z,
                                      kind: e.target
                                        .value as LayoutZone["kind"],
                                    }
                                  : z,
                              ),
                            )
                          }
                        >
                          {[
                            "Canteiro",
                            "Caminho",
                            "Deck",
                            "Gramado",
                            "Construção",
                            "Água",
                          ].map((v) => (
                            <option key={v}>{v}</option>
                          ))}
                        </select>
                      </label>
                      {[
                        ["x", "X (m)"],
                        ["y", "Y (m)"],
                        ["width", "Largura da área (m)"],
                        ["length", "Comprimento da área (m)"],
                      ].map(([key, label]) => (
                        <label key={key}>
                          {label}
                          <input
                            type="number"
                            min={key === "x" || key === "y" ? 0 : 0.1}
                            step="0.1"
                            value={zone[key as keyof LayoutZone]}
                            onChange={(e) =>
                              update(
                                "zones",
                                brief.zones.map((z, j) =>
                                  i === j
                                    ? { ...z, [key]: Number(e.target.value) }
                                    : z,
                                ),
                              )
                            }
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </>
            )}
            {tab === "Arquivos" && (
              <>
                <p className="form-hint">
                  Envie fotos do local, croquis e medidas em PDF. Os arquivos
                  ficam privados na solicitação e acompanham o projeto após
                  aprovação.
                </p>
                <label className="button secondary">
                  <Upload size={16} />
                  Selecionar fotos e documentos
                  <input
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    hidden
                    aria-label="Fotos e documentos do planejamento"
                    onChange={(e) => {
                      const files = [...(e.target.files || [])];
                      e.target.value = "";
                      if (
                        files.some(
                          (file) =>
                            file.size >
                            (file.type === "application/pdf" ||
                            file.name.toLowerCase().endsWith(".pdf")
                              ? 10
                              : 5) *
                              1024 *
                              1024,
                        )
                      ) {
                        setError("Fotos até 5 MB e PDFs até 10 MB.");
                        return;
                      }
                      if (pending.length + files.length > 12) {
                        setError("Envie até 12 anexos por envio.");
                        return;
                      }
                      setPending([...pending, ...files]);
                    }}
                  />
                </label>
                {pending.map((file, i) => (
                  <div className="detail-link" key={i}>
                    <FileText size={16} />
                    <span>{file.name}</span>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={`Remover anexo ${file.name}`}
                      onClick={() =>
                        setPending(pending.filter((_, j) => i !== j))
                      }
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>
        </section>
        <LandscapePlan
          brief={brief}
          species={data.species}
          onMove={(index, x, y) =>
            setBrief((b) => ({
              ...b,
              plantings: b.plantings.map((p, i) =>
                index === i ? { ...p, x, y } : p,
              ),
            }))
          }
        />
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="studio-footer">
        <div>
          <button
            type="button"
            className="text-button"
            onClick={() =>
              downloadFile(
                "atelie-verde-planejamento.json",
                JSON.stringify(brief, null, 2),
                "application/json",
              )
            }
          >
            <Download size={15} />
            Exportar dados
          </button>
          <button
            type="button"
            className="text-button"
            onClick={() => exportMemorial(brief, data.species, address)}
          >
            <FileText size={15} />
            Baixar memorial
          </button>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          <SaveButton
            busy={busy}
            label={
              project || quote || savedId
                ? "Salvar planejamento"
                : "Solicitar orçamento"
            }
          />
        </form>
      </div>
    </div>
  );
}
