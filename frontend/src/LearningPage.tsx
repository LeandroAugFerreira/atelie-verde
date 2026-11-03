import { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  Clock,
  Sprout,
  ArrowRight,
} from "lucide-react";
import { useGreen } from "./context";
import { api } from "./api";
import { Picture, SearchInput } from "./ReferenceUI";
import { Empty } from "./components";
import { Sources, PhotoCredits } from "./BotanicalDetails";
import { AskRafinha } from "./RafinhaAssistant";

export function LearningPage() {
  const { data, go, reload, toast, selectedId } = useGreen();
  const [selected, setSelected] = useState<number | null>(null),
    [category, setCategory] = useState("Todos"),
    [search, setSearch] = useState(""),
    [busy, setBusy] = useState(false);
  const done = new Set(data.learningProgress.map((p) => p.article_id));
  const filtered = data.articles.filter(
    (a) =>
      (category === "Todos" ||
        a.category === category ||
        (category === "Concluídos" && done.has(a.id))) &&
      `${a.title} ${a.summary}`
        .toLocaleLowerCase("pt-BR")
        .includes(search.toLocaleLowerCase("pt-BR")),
  );
  const article = data.articles.find((a) => a.id === selected) || filtered[0];
  const plant = data.species.find((s) => s.id === article?.species_id);
  const reader = useRef<HTMLElement>(null);
  useEffect(() => {
    if (selectedId && data.articles.some((a) => a.id === selectedId))
      setSelected(selectedId);
    else setSelected(null);
  }, [selectedId]);
  useEffect(() => {
    reader.current?.scrollTo({ top: 0 });
  }, [article?.id]);
  async function complete() {
    if (!article) return;
    setBusy(true);
    try {
      await api(`/learning/${article.id}/complete`, {
        method: done.has(article.id) ? "DELETE" : "PUT",
      });
      await reload();
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="learning-page client-inner">
      <div className="learning-intro">
        <span className="round-icon">
          <BookOpen size={27} />
        </span>
        <div>
          <h1>Aprender a cultivar</h1>
          <p>
            Conhecimento para cuidar de cada folha, do primeiro vaso ao jardim.
          </p>
        </div>
        <div className="learning-progress">
          <strong>
            {done.size} de {data.articles.length}
          </strong>
          <span>guias concluídos</span>
          <progress value={done.size} max={data.articles.length || 1} />
        </div>
      </div>
      <div className="learning-layout">
        <aside className="panel learning-list">
          <div className="panel-heading">
            <h2>Explore os guias</h2>
          </div>
          <SearchInput
            value={search}
            onChange={(value) => {
              setSearch(value);
              go("learn");
            }}
            placeholder="Buscar tema ou técnica…"
          />
          <div className="learning-filters" aria-label="Categorias dos guias">
            {[
              "Todos",
              ...new Set(data.articles.map((a) => a.category)),
              "Concluídos",
            ].map((c) => (
              <button
                key={c}
                className={category === c ? "active" : ""}
                onClick={() => {
                  setCategory(c);
                  go("learn");
                }}
              >
                {c}
              </button>
            ))}
          </div>
          <div className="guide-list" tabIndex={0} aria-label="Lista de guias">
            {filtered.map((a) => (
              <button
                className={`guide-card ${article?.id === a.id ? "selected" : ""}`}
                key={a.id}
                onClick={() => go("learn", a.id)}
              >
                <div className="guide-thumbnail">
                  {data.species.find((s) => s.id === a.species_id) && (
                    <Picture
                      item={data.species.find((s) => s.id === a.species_id)!}
                    />
                  )}
                </div>
                <div>
                  <small>
                    {a.category} · {a.minutes} min
                  </small>
                  <strong>{a.title}</strong>
                  <p>{a.summary}</p>
                </div>
                {done.has(a.id) && (
                  <CheckCircle2 size={18} aria-label="Concluído" />
                )}
              </button>
            ))}
            {!filtered.length && <Empty>Nenhum guia encontrado.</Empty>}
          </div>
          <button className="button secondary" onClick={() => go("species")}>
            <Sprout size={18} />
            Biblioteca de espécies
            <ArrowRight size={15} />
          </button>
        </aside>
        <article
          ref={reader}
          className="panel guide-reader"
          tabIndex={0}
          aria-label="Conteúdo do guia"
        >
          {article ? (
            <>
              <div className="guide-hero">
                {plant && <Picture item={plant} />}
                <div>
                  <span className="eyebrow">
                    ATELIÊ VERDE · CADERNO DE CULTIVO
                  </span>
                  <h2>{article.title}</h2>
                  <span className="inline">
                    <Clock size={14} />
                    {article.minutes} minutos de leitura · {article.category}
                  </span>
                </div>
              </div>
              <div className="guide-body">
                <AskRafinha
                  context={{
                    kind: "article",
                    id: article.id,
                    label: article.title,
                  }}
                  label="Tirar uma dúvida sobre este guia"
                />
                <p className="guide-summary">{article.summary}</p>
                {article.sections.map((s, i) => (
                  <section key={s.title}>
                    <h3>
                      <span>{String(i + 1).padStart(2, "0")}</span>
                      {s.title}
                    </h3>
                    <p>{s.text}</p>
                    {s.steps.length > 0 && (
                      <ol>
                        {s.steps.map((step) => (
                          <li key={step}>{step}</li>
                        ))}
                      </ol>
                    )}
                  </section>
                ))}
                <Sources items={article.sources} />
                {plant && <PhotoCredits photos={plant.photos} />}
                <div className="guide-footer">
                  <button
                    className={`button ${done.has(article.id) ? "secondary" : "primary"}`}
                    disabled={busy}
                    onClick={complete}
                  >
                    <CheckCircle2 size={18} />
                    {done.has(article.id)
                      ? "Concluído · marcar como não lido"
                      : "Marcar como concluído"}
                  </button>
                  <button className="text-button" onClick={() => go("species")}>
                    Conheça as espécies
                    <Sprout size={17} />
                  </button>
                </div>
              </div>
            </>
          ) : (
            <Empty>Os guias aparecerão aqui.</Empty>
          )}
        </article>
      </div>
    </div>
  );
}
