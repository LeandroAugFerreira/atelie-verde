import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type Connection = {
  connected: boolean;
  kind: string;
  enabled: boolean;
  state: string;
  email: string;
  model: string;
  models: { id: string; name: string }[];
  daily_limit: number;
  response_timeout: number;
  web_enabled: boolean;
  web_mode: string;
  attempts_today: number;
  login_state: string;
  login_message: string;
  message: string;
};
type Options = {
  daily_limit?: number;
  model?: string;
  response_timeout?: number;
  web_enabled?: boolean;
  web_mode?: string;
};

export function RafinhaConnection({ changed }: { changed?: () => void }) {
  const [connection, setConnection] = useState<Connection | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [saved, setSaved] = useState(""),
    [url, setUrl] = useState("");
  const [limit, setLimit] = useState("20"),
    [model, setModel] = useState("");
  const pending = useRef<Options>({}),
    saving = useRef(false),
    alive = useRef(true);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connected = connection?.connected && connection.kind === "chatgpt";
  const waiting = ["waiting", "exchanging"].includes(
    connection?.login_state || "",
  );

  function receive(value: Connection) {
    if (!alive.current) return;
    setConnection(value);
    if (!saving.current && !Object.keys(pending.current).length) {
      setLimit(String(value.daily_limit));
      setModel(value.model);
    }
    changed?.();
  }
  async function refresh() {
    receive(await api<Connection>("/assistant/connection"));
  }
  async function save() {
    if (timer.current) clearTimeout(timer.current);
    if (saving.current || !Object.keys(pending.current).length) return;
    const patch = pending.current;
    pending.current = {};
    saving.current = true;
    let success = false;
    try {
      const value = await api<Connection>("/assistant/connection", {
        method: "PUT",
        body: JSON.stringify(patch),
      });
      receive(value);
      success = true;
      if (alive.current)
        setSaved(
          Object.keys(pending.current).length
            ? "Salvando…"
            : "Alterações salvas",
        );
    } catch (e) {
      pending.current = { ...patch, ...pending.current };
      if (alive.current) {
        setError((e as Error).message);
        setSaved("Não foi possível salvar");
      }
    } finally {
      saving.current = false;
    }
    if (success && Object.keys(pending.current).length) void save();
  }
  function schedule(patch: Options) {
    pending.current = { ...pending.current, ...patch };
    setSaved("Salvando…");
    setError("");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => void save(), 650);
  }
  async function act(work: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await work();
      await refresh();
    } catch (e) {
      if (alive.current) setError((e as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  useEffect(() => {
    alive.current = true;
    refresh().catch((e) => {
      if (alive.current) setError(e.message);
    });
    return () => {
      alive.current = false;
      if (timer.current) clearTimeout(timer.current);
      if (Object.keys(pending.current).length) void save();
    };
  }, []);
  useEffect(() => {
    if (!waiting) return;
    const poll = setInterval(() => refresh().catch(() => {}), 1500);
    return () => clearInterval(poll);
  }, [waiting]);

  return (
    <section className="rafinha-connection" aria-label="IA do Rafinha">
      <h3>ChatGPT do Rafinha</h3>
      <p>
        {connected && connection.enabled && connection.state === "ready"
          ? "ChatGPT conectado · pronto para conversar"
          : "Conecte sua própria conta ChatGPT para conversar com o Rafinha."}
      </p>
      {connected && (
        <p>Conta conectada{connection.email ? `: ${connection.email}` : ""}.</p>
      )}
      {!connected || connection.state === "reconnect" ? (
        <button
          type="button"
          className="button secondary"
          disabled={busy || waiting}
          onClick={() =>
            act(async () => {
              const popup = window.open("about:blank", "_blank");
              try {
                const result = await api<{ authorization_url: string }>(
                  "/assistant/connection/chatgpt/start",
                  {
                    method: "POST",
                    body: JSON.stringify({ open_browser: false }),
                  },
                );
                setUrl(result.authorization_url);
                if (popup) popup.location.href = result.authorization_url;
              } catch (e) {
                popup?.close();
                throw e;
              }
            })
          }
        >
          Continuar com ChatGPT
        </button>
      ) : (
        <button
          type="button"
          className="button secondary"
          disabled={busy}
          onClick={() =>
            act(() =>
              api("/assistant/connection", {
                method: "PUT",
                body: JSON.stringify({ enabled: !connection.enabled }),
              }),
            )
          }
        >
          {connection.enabled ? "Pausar ChatGPT" : "Ativar ChatGPT"}
        </button>
      )}
      {waiting && (
        <p role="status">
          Finalize a autorização no navegador. Esta tela será atualizada
          automaticamente.{" "}
          {url && (
            <a href={url} target="_blank" rel="noreferrer">
              Abrir login oficial
            </a>
          )}
        </p>
      )}
      {connection?.login_message && !waiting && (
        <p role="status">{connection.login_message}</p>
      )}
      {!connected && (
        <p className="muted">
          Disponível para contas ChatGPT elegíveis. Sem conexão, o catálogo
          continua disponível.
        </p>
      )}
      {connected && (
        <>
          <a
            href="https://chatgpt.com/settings/usage"
            target="_blank"
            rel="noreferrer"
          >
            Gerenciar uso do meu plano ChatGPT
          </a>
          <details className="rafinha-ai-option">
            <summary>Preferências da conexão</summary>
            <label>
              Modelo
              <select
                value={model}
                disabled={busy}
                onChange={(e) => {
                  setModel(e.target.value);
                  schedule({ model: e.target.value });
                }}
              >
                {connection.models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Máximo de consultas por dia
              <input
                type="number"
                min="1"
                max="100"
                value={limit}
                disabled={busy}
                onChange={(e) => {
                  const value = e.target.value;
                  setLimit(value);
                  const count = Number(value);
                  if (Number.isInteger(count) && count >= 1 && count <= 100)
                    schedule({ daily_limit: count });
                }}
                onBlur={() => void save()}
              />
            </label>
            <label>
              Tempo para responder
              <select
                value={connection.response_timeout || 30}
                disabled={busy}
                onChange={(e) =>
                  schedule({ response_timeout: Number(e.target.value) })
                }
              >
                <option value={30}>Até 30 segundos</option>
                <option value={10}>Até 10 segundos</option>
              </select>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={connection.web_enabled}
                disabled={busy}
                onChange={(e) => schedule({ web_enabled: e.target.checked })}
              />
              Pesquisar na internet quando necessário
            </label>
            <label>
              Quando pesquisar
              <select
                value={connection.web_mode || "automatic"}
                disabled={busy || !connection.web_enabled}
                onChange={(e) => schedule({ web_mode: e.target.value })}
              >
                <option value="automatic">
                  Automaticamente quando fizer sentido
                </option>
                <option value="on_request">Somente quando eu pedir</option>
              </select>
            </label>
            <p role="status">{saved}</p>
            <p>
              Consultas usadas hoje: {connection.attempts_today} de{" "}
              {connection.daily_limit}.
            </p>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() =>
                act(() => api("/assistant/connection", { method: "DELETE" }))
              }
            >
              Desconectar minha conta
            </button>
          </details>
        </>
      )}
      {connection?.message && <p role="status">{connection.message}</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
