import { useEffect, useState } from "react";
import { FileText, Download, Trash2, Upload } from "lucide-react";
import { api } from "./api";
import { useGreen } from "./context";
import { dateLabel } from "./types";

export function QuoteDocuments({
  id,
  editable,
}: {
  id: number;
  editable: boolean;
}) {
  const { toast } = useGreen();
  const [docs, setDocs] = useState<
      { id: number; name: string; created_at: string }[]
    >([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const load = () => api<typeof docs>(`/quotes/${id}/documents`).then(setDocs);
  useEffect(() => {
    let alive = true;
    setDocs([]);
    setError("");
    api<typeof docs>(`/quotes/${id}/documents`)
      .then((d) => {
        if (alive) setDocs(d);
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [id]);
  async function download(doc: (typeof docs)[number]) {
    try {
      const response = await fetch(`/api/documents/${doc.id}/content`, {
        headers: {
          Authorization: `Bearer ${sessionStorage.getItem("greenscape-token")}`,
        },
      });
      if (!response.ok) throw new Error("Documento indisponível.");
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast((e as Error).message);
    }
  }
  return (
    <section className="quote-documents">
      <div className="section-heading">
        <h3>
          <FileText size={18} />
          Documentos da solicitação
        </h3>
        {editable && (
          <label className="button secondary small">
            <Upload size={15} />
            {busy ? "Enviando…" : "Anexar PDF"}
            <input
              type="file"
              accept="application/pdf"
              aria-label="Anexar documento PDF"
              hidden
              disabled={busy}
              onChange={async (e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (!file) return;
                setBusy(true);
                setError("");
                try {
                  if (file.size > 10 * 1024 * 1024)
                    throw new Error("Documento limitado a 10 MB.");
                  const form = new FormData();
                  form.append("file", file);
                  await api(`/quotes/${id}/documents`, {
                    method: "POST",
                    body: form,
                  });
                  await load();
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            />
          </label>
        )}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {docs.map((doc) => (
        <div className="detail-link" key={doc.id}>
          <FileText size={17} />
          <strong title={doc.name}>{doc.name}</strong>
          <span>{dateLabel(doc.created_at)}</span>
          <button
            className="text-button"
            onClick={() => download(doc)}
            aria-label={`Baixar ${doc.name}`}
          >
            <Download size={15} />
            Baixar
          </button>
          {editable && (
            <button
              className="icon-button"
              disabled={busy}
              aria-label={`Excluir ${doc.name}`}
              onClick={async () => {
                setBusy(true);
                try {
                  await api(`/documents/${doc.id}`, { method: "DELETE" });
                  await load();
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <Trash2 size={15} />
            </button>
          )}
        </div>
      ))}
      {!docs.length && (
        <p className="form-hint">
          Anexe planta, croqui, medidas ou referências em PDF, até 10 MB.
        </p>
      )}
    </section>
  );
}
