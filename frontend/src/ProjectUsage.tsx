import { useEffect, useState } from "react";
import { PackageOpen, Plus } from "lucide-react";
import { useGreen } from "./context";
import { api } from "./api";
import { Panel, Paginator } from "./ReferenceUI";
import { Empty } from "./components";
import { dateLabel, money, type Project } from "./types";

type Usage = {
  total: number;
  units: number;
  cost_cents: number;
  uncosted_moves: number;
  items: {
    id: number;
    product_name: string;
    quantity: number;
    unit: string;
    created_at: string;
    unit_cost_cents: number | null;
    total_cost_cents: number | null;
    actor_name: string;
    reason: string;
  }[];
};
export function ProjectUsage({ project }: { project: Project }) {
  const { data, open } = useGreen();
  const [page, setPage] = useState(1),
    [error, setError] = useState(""),
    [usage, setUsage] = useState<Usage | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    api<Usage>(
      `/projects/${project.id}/stock-usage?offset=${(page - 1) * 10}&limit=10`,
      { signal: controller.signal },
    )
      .then((r) => {
        setUsage(r);
        setError("");
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [project.id, page, data.moves]);
  return (
    <Panel
      title="Consumo real de plantas e materiais"
      Icon={PackageOpen}
      className="project-usage-panel"
      actions={
        ["Execução", "Manutenção"].includes(project.status) && (
          <button
            className="button primary"
            onClick={() => open("project-consumption", project)}
          >
            <Plus size={16} />
            Registrar consumo
          </button>
        )
      }
    >
      <div className="usage-summary">
        <span>
          Movimentações <b>{usage?.total ?? "—"}</b>
        </span>
        <span>
          Custo registrado <b>{usage ? money(usage.cost_cents) : "—"}</b>
        </span>
        <span>
          Orçamento do projeto <b>{money(project.budget_cents)}</b>
        </span>
      </div>
      <p className="form-hint">
        O planejamento não baixa estoque. O consumo registra saídas reais e
        mantém o custo daquela utilização, sem gerar uma nova despesa
        financeira.
        {usage?.uncosted_moves
          ? ` Há ${usage.uncosted_moves} movimentação(ões) sem custo informado; o total é parcial.`
          : ""}
      </p>
      {!["Execução", "Manutenção"].includes(project.status) && (
        <p className="form-hint">
          Novos consumos podem ser registrados nas etapas Execução e Manutenção.
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <div className="table-scroll">
        <table className="dense-table usage-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Produto</th>
              <th>Quantidade</th>

              <th>Custo total</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {usage?.items.map((m) => (
              <tr key={m.id}>
                <td>{dateLabel(m.created_at)}</td>
                <td>{m.product_name}</td>
                <td>
                  {-m.quantity} {m.unit}
                </td>

                <td>
                  {m.total_cost_cents === null
                    ? "—"
                    : money(m.total_cost_cents)}
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={`Detalhes do consumo ${m.product_name}`}
                    onClick={() => open("movement-detail", m)}
                  >
                    <PackageOpen size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {usage && !usage.total && (
          <Empty>Nenhum consumo registrado para este projeto.</Empty>
        )}
      </div>
      <Paginator
        page={page}
        setPage={setPage}
        total={usage?.total || 0}
        size={10}
      />
    </Panel>
  );
}
