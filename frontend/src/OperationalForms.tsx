import { useState, type FormEvent } from "react";
import { useGreen } from "./context";
import { SaveButton } from "./components";
import { write } from "./api";
import type { Appointment, Ledger } from "./types";

export function AppointmentForm({ item }: { item?: Appointment }) {
  const { data, reload, open, toast } = useGreen();
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const today = new Date().toLocaleDateString("sv-SE");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    try {
      await write(
        `/appointments${item ? "/" + item.id : ""}`,
        {
          ...Object.fromEntries(f),
          service_id: Number(f.get("service_id")),
          customer_id: Number(f.get("customer_id")),
          amount_cents: Math.round(Number(f.get("amount")) * 100),
        },
        item ? "PUT" : "POST",
      );
      await reload();
      open("");
      toast("Agendamento salvo.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="form" onSubmit={submit}>
      <div className="form-grid">
        <label>
          Título
          <input
            name="title"
            defaultValue={item?.title}
            required
            minLength={2}
          />
        </label>
        <label>
          Serviço
          <select name="service_id" defaultValue={item?.service_id}>
            {data.services.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cliente
          <select name="customer_id" defaultValue={item?.customer_id}>
            {data.customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Responsável
          <input
            name="responsible"
            defaultValue={item?.responsible || "Equipe Ateliê Verde"}
            required
            minLength={2}
          />
        </label>
        <label>
          Data
          <input
            type="date"
            name="date"
            defaultValue={item?.date || today}
            required
          />
        </label>
        <label>
          Valor do serviço (R$)
          <input
            name="amount"
            type="number"
            min="0"
            step="0.01"
            defaultValue={(item?.amount_cents || 0) / 100}
          />
        </label>
        <label>
          Início
          <input
            type="time"
            name="start_time"
            defaultValue={item?.start_time || "08:00"}
            required
          />
        </label>
        <label>
          Término
          <input
            type="time"
            name="end_time"
            defaultValue={item?.end_time || "09:00"}
            required
          />
        </label>
        <label className="full">
          Endereço
          <input
            name="address"
            defaultValue={item?.address}
            required
            minLength={5}
          />
        </label>
        <label>
          Status
          <select name="status" defaultValue={item?.status || "Agendado"}>
            {["Agendado", "Em execução", "Concluído", "Cancelado"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="form-footer">
        <span>Conflitos de horário serão verificados.</span>
        <SaveButton busy={busy} />
      </div>
    </form>
  );
}
export function LedgerForm({
  direction = "Receita",
  item,
}: {
  direction?: string;
  item?: Ledger;
}) {
  const { data, reload, open, toast } = useGreen();
  const [status, setStatus] = useState(item?.status || "Pendente"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    try {
      await write("/ledger", {
        ...Object.fromEntries(f),
        direction,
        customer_id: f.get("customer_id") ? Number(f.get("customer_id")) : null,
        supplier_id: f.get("supplier_id") ? Number(f.get("supplier_id")) : null,
        amount_cents: Math.round(Number(f.get("amount")) * 100),
        paid_date: status === "Pago" ? f.get("paid_date") : null,
      });
      await reload();
      open("");
      toast("Lançamento financeiro salvo.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="form" onSubmit={submit}>
      <div className="form-grid">
        <label>
          {direction === "Receita"
            ? "Cliente / pagador"
            : "Fornecedor / beneficiário"}
          <input name="counterparty" required minLength={2} />
        </label>
        <label>
          {direction === "Receita"
            ? "Cliente vinculado (opcional)"
            : "Fornecedor vinculado (opcional)"}
          <select
            name={direction === "Receita" ? "customer_id" : "supplier_id"}
          >
            <option value="">Sem vínculo</option>
            {(direction === "Receita"
              ? data.customers
              : data.suppliers.filter((s) => s.active)
            ).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="full">
          Descrição
          <input name="description" required minLength={2} />
        </label>
        <label>
          Origem
          <select name="source">
            {["Loja", "Serviços", "Projetos", "Estoque", "Outros"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Valor (R$)
          <input type="number" name="amount" min="0.01" step="0.01" required />
        </label>
        <label>
          Vencimento
          <input name="due_date" type="date" required />
        </label>
        <label>
          Status
          <select
            name="status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option>Pendente</option>
            <option>Pago</option>
          </select>
        </label>
        {status === "Pago" && (
          <label>
            Data do pagamento
            <input
              name="paid_date"
              type="date"
              required
              defaultValue={new Date().toLocaleDateString("sv-SE")}
            />
          </label>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      <div className="form-footer">
        <span>{direction} · controle financeiro</span>
        <SaveButton busy={busy} />
      </div>
    </form>
  );
}
export function AdminQuoteForm() {
  const { data, reload, open, toast } = useGreen();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    try {
      const q = await write<{ id: number }>("/quotes", {
        ...Object.fromEntries(f),
        customer_id: Number(f.get("customer_id")),
        service_id: Number(f.get("service_id")),
        area: Number(f.get("area")),
      });
      await reload();
      open("");
      toast(`Orçamento #${q.id} criado.`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="form" onSubmit={submit}>
      <div className="form-grid">
        <label>
          Cliente
          <select name="customer_id" required>
            {data.customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Serviço
          <select name="service_id">
            {data.services.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Área (m²)
          <input name="area" type="number" min="0.1" step="0.1" required />
        </label>
        <label>
          Endereço
          <input name="address" required minLength={5} />
        </label>
        <label className="full">
          Descrição
          <textarea name="description" rows={4} />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="form-footer">
        <span>As fotos e a proposta serão adicionadas no detalhe.</span>
        <SaveButton busy={busy} />
      </div>
    </form>
  );
}
