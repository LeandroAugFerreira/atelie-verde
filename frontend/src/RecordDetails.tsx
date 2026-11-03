import { useGreen } from "./context";
import { dateLabel, money } from "./types";

export function MovementDetails({ record }: { record: Record<string, any> }) {
  const { data, user } = useGreen();
  const fields = [
    [
      "Produto",
      record.product_name ||
        data.products.find((p) => p.id === record.product_id)?.name ||
        "—",
    ],
    [
      "Data",
      `${dateLabel(record.created_at)} · ${new Date(record.created_at).toLocaleTimeString("pt-BR")}`,
    ],
    ["Tipo", record.quantity > 0 ? "Entrada" : "Saída"],
    ["Quantidade", `${record.quantity > 0 ? "+" : ""}${record.quantity}`],
    [
      "Saldo anterior / final",
      record.balance_before == null
        ? "Não registrado"
        : `${record.balance_before} → ${record.balance_after}`,
    ],
    ["Origem", record.origin || "Não informada"],
    ["Destino", record.destination || "Não informado"],
    [
      "Fornecedor",
      data.suppliers.find((s) => s.id === record.supplier_id)?.name ||
        "Sem vínculo",
    ],
    [
      "Projeto",
      data.projects.find((p) => p.id === record.project_id)?.name ||
        "Sem vínculo",
    ],
    ["Referência", record.reference || "Não informada"],
    ["Motivo", record.reason],
    [
      "Responsável",
      record.actor_name ||
        (record.actor_id === user.id
          ? user.name
          : data.customers.find((c) => c.id === record.actor_id)?.name) ||
        "—",
    ],
    [
      "Custo unitário",
      record.unit_cost_cents == null
        ? "Não informado"
        : money(record.unit_cost_cents),
    ],
  ];
  return (
    <div className="detail">
      <div className="record-details">
        <h3>Detalhes da movimentação</h3>
        <dl>
          {fields.map(([name, value]) => (
            <div key={name}>
              <dt>{name}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
