import { useEffect, useState } from "react";
import { CheckCircle, AlertCircle, RefreshCw } from "lucide-react";
import { api } from "./api";
type Check = {
  counts: {
    products: number;
    orders: number;
    quotes: number;
    appointments: number;
  };
  errors: { entity: string; id: number; message: string }[];
  warnings: { entity: string; id: number; message: string }[];
};
export function DataQuality() {
  const [result, setResult] = useState<Check | null>(null),
    [error, setError] = useState(""),
    [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api<Check>("/admin/data-quality", { signal: controller.signal })
      .then(setResult)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [version]);
  return (
    <div className="detail">
      <p className="form-hint">
        Conferência de pedidos, estoque, financeiro, projetos aprovados e
        sobreposições de agenda. Receitas manuais não são contadas como unidades
        vendidas.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {result && (
        <>
          <div className="record-details">
            <h3>
              {result.errors.length ? (
                <>
                  <AlertCircle size={17} /> {result.errors.length}{" "}
                  inconsistência(s) encontrada(s)
                </>
              ) : (
                <>
                  <CheckCircle size={17} /> Registros consistentes
                </>
              )}
            </h3>
            <dl>
              <div>
                <dt>Produtos</dt>
                <dd>{result.counts.products}</dd>
              </div>
              <div>
                <dt>Pedidos</dt>
                <dd>{result.counts.orders}</dd>
              </div>
              <div>
                <dt>Orçamentos</dt>
                <dd>{result.counts.quotes}</dd>
              </div>
              <div>
                <dt>Agenda</dt>
                <dd>{result.counts.appointments}</dd>
              </div>
            </dl>
          </div>
          {[...result.errors, ...result.warnings].map((item, i) => (
            <p className="notice" key={i}>
              {item.entity} #{item.id}: {item.message}
            </p>
          ))}
        </>
      )}
      <button
        className="button secondary"
        onClick={() => {
          setError("");
          setVersion(version + 1);
        }}
      >
        <RefreshCw size={16} />
        Conferir novamente
      </button>
    </div>
  );
}
