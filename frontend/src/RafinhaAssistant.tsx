import { useEffect, useRef, useState } from "react";
import {
  MessageCircle,
  X,
  Send,
  History,
  Plus,
  Settings,
  Trash2,
  Square,
  Volume2,
  Sparkles,
  Camera,
  Minus,
} from "lucide-react";
import { api, write, assistantPhoto } from "./api";
import {
  expressionAsset,
  initialReaction,
  PHASE_LABELS,
  SOURCE_LABELS,
  type RafinhaExpression,
} from "./rafinhaExpressions";
import { useGreen } from "./context";
import { AI_MODE_LABELS } from "./rafinhaModes";
import { RafinhaMessageText } from "./RafinhaMessageText";
import { RafinhaCharacter } from "./RafinhaCharacter";
import {
  SearchImageGallery,
  publicWebUrl,
  type SearchImage,
} from "./SearchImageGallery";

type Context = {
  kind: "species" | "product" | "article" | "project" | "quote";
  id: number;
  label?: string;
};
type Action = { kind: string; id: number; label: string };
type Message = {
  expression?: RafinhaExpression;
  meta?: {
    source_type: string;
    expressions?: {
      initial: RafinhaExpression;
      processing: RafinhaExpression;
      final: RafinhaExpression;
    };
    research?: { needed: boolean; status: string; cache?: string };
    fallback?: boolean;
  };
  id: number;
  role: "user" | "assistant";
  text: string;
  status: string;
  mode: string;
  request_id: string;
  context: Context | Record<string, never>;
  sources: { title: string; url: string }[];
  images?: SearchImage[];
  actions: Action[];
};
type Conversation = {
  id: number;
  title: string;
  updated_at: string;
  pending_request: string;
  messages?: Message[];
  attachments?: { id: number; url: string }[];
};
type Preferences = {
  enabled: boolean;
  motion: boolean;
  typewriter: boolean;
  voice: boolean;
};
type Configuration = {
  enabled: boolean;
  greeting: string;
  suggestions: string[];
};
type Status = Configuration & {
  mode: string;
  label: string;
  local_available: boolean;
};
const defaults: Preferences = {
  enabled: true,
  motion: true,
  typewriter: true,
  voice: false,
};
const eventName = "atelie-ask-rafinha";

export function askRafinha(context?: Context) {
  window.dispatchEvent(new CustomEvent(eventName, { detail: context }));
}
export function AskRafinha({
  context,
  label = "Perguntar ao Rafinha",
}: {
  context?: Context;
  label?: string;
}) {
  const { user } = useGreen();
  if (user.role !== "customer") return null;
  return (
    <button
      type="button"
      className="text-button ask-rafinha"
      onClick={() => askRafinha(context)}
    >
      <MessageCircle size={16} />
      {label}
    </button>
  );
}

function speech(text: string) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "pt-BR";
  // Use only an installed local voice: no cloud narration and no voice cloning.
  const localVoice = window.speechSynthesis
    .getVoices()
    .find((v) => v.localService && v.lang.startsWith("pt"));
  if (!localVoice) return;
  utterance.voice = localVoice;
  window.speechSynthesis.speak(utterance);
}

function PrivatePhoto({ url }: { url: string }) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    let alive = true;
    let value = "";
    assistantPhoto(url)
      .then((blob) => {
        value = blob;
        if (alive) setSrc(blob);
        else URL.revokeObjectURL(blob);
      })
      .catch(() => {});
    return () => {
      alive = false;
      if (value) URL.revokeObjectURL(value);
    };
  }, [url]);
  return src ? (
    <img src={src} alt="Foto da planta enviada nesta conversa" />
  ) : (
    <span>Carregando foto…</span>
  );
}

export function RafinhaAssistant({ blocked }: { blocked: boolean }) {
  const { user, go, open: openModal, data } = useGreen();
  const [status, setStatus] = useState<Status | null>(null);
  const [prefs, setPrefs] = useState(defaults);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [visible, setVisible] = useState(false),
    [hidden, setHidden] = useState(false);
  const [settings, setSettings] = useState(false),
    [showHistory, setShowHistory] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversation, setConversation] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]),
    [context, setContext] = useState<Context | undefined>();
  const lastReply = messages
    .filter((m) => m.role === "assistant" && m.status === "completed")
    .at(-1);
  const effectiveMode = lastReply?.mode || status?.mode;
  const effectiveLabel = lastReply
    ? AI_MODE_LABELS[lastReply.mode] || "Resposta guiada"
    : status?.label;
  const [draft, setDraft] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const [typing, setTyping] = useState<{
    id: number;
    count: number;
    parts: string[];
  } | null>(null);
  const [streaming, setStreaming] = useState("");
  const streamed = useRef(false);
  const [pose, setPose] = useState("welcome");
  const [phase, setPhase] = useState("context"),
    [photoBusy, setPhotoBusy] = useState(false);
  const [photos, setPhotos] = useState<{ id: number; url: string }[]>([]);
  const [reduced, setReduced] = useState(false),
    [localVoice, setLocalVoice] = useState(false);
  const log = useRef<HTMLDivElement>(null),
    input = useRef<HTMLTextAreaElement>(null);
  const controller = useRef<AbortController | null>(null);
  const pending = useRef<{ conversation: number; request: string } | null>(
    null,
  );
  const sequence = useRef(0),
    sending = useRef(false),
    timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const storageKey = `atelie-rafinha-conversation-${user.id}`;
  const processTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finalPoseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reactionStarted = useRef(0);
  function finishTyping() {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    setTyping(null);
  }
  async function stop(refresh = true) {
    if (processTimer.current) clearTimeout(processTimer.current);
    if (finalPoseTimer.current) clearTimeout(finalPoseTimer.current);
    sequence.current++;
    controller.current?.abort();
    finishTyping();
    setStreaming("");
    streamed.current = false;
    const request = pending.current;
    pending.current = null;
    sending.current = false;
    setBusy(false);
    if (request) {
      try {
        await write(
          `/assistant/conversations/${request.conversation}/messages/${request.request}/cancel`,
          {},
        );
        const result = await api<Conversation>(
          `/assistant/conversations/${request.conversation}`,
        );
        if (refresh && conversation === request.conversation)
          setMessages(result.messages || []);
      } catch (e) {
        setError((e as Error).message);
      }
    }
  }
  function collapse() {
    const closingId = conversation || pending.current?.conversation;
    setVisible(false);
    void stop(false);
    setConversation(null);
    setMessages([]);
    setPhotos([]);
    setPhotoBusy(false);
    setDraft("");
    setContext(undefined);
    setPose("welcome");
    setShowHistory(false);
    setSettings(false);
    setError("");
    sessionStorage.removeItem(storageKey);
    if (closingId)
      api(`/assistant/conversations/${closingId}`, { method: "DELETE" }).catch(
        (e) => {
          if ((e as { status?: number }).status !== 404)
            console.warn("Não foi possível encerrar a conversa do Rafinha.");
        },
      );
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }
  function minimize() {
    setVisible(false);
    setShowHistory(false);
    setSettings(false);
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }
  async function load(id: number) {
    await stop();
    setPhotoBusy(false);
    setError("");
    const version = ++sequence.current;
    try {
      const result = await api<Conversation>(`/assistant/conversations/${id}`);
      if (sequence.current !== version) return;
      setConversation(id);
      setMessages(result.messages || []);
      setPhotos(result.attachments || []);
      setPose(
        result.messages?.filter((m) => m.role === "assistant").at(-1)
          ?.expression || "welcome",
      );
      sessionStorage.setItem(storageKey, String(id));
      const ctx = [...(result.messages || [])]
        .reverse()
        .find((m) => m.context?.kind)?.context as Context | undefined;
      setContext(ctx);
      setShowHistory(false);
    } catch (e) {
      if (sequence.current === version) setError((e as Error).message);
    }
  }
  async function history() {
    try {
      setConversations(await api<Conversation[]>("/assistant/conversations"));
      setShowHistory(true);
      setSettings(false);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function newConversation() {
    await stop();
    setConversation(null);
    setMessages([]);
    setPhotos([]);
    setPhotoBusy(false);
    setContext(undefined);
    setDraft("");
    setError("");
    setShowHistory(false);
    setPose("neutral");
    setSettings(false);
    sessionStorage.removeItem(storageKey);
    input.current?.focus();
  }
  async function deleteConversation(id: number) {
    await stop();
    try {
      await api(`/assistant/conversations/${id}`, { method: "DELETE" });
      if (conversation === id) await newConversation();
      await history();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function savePrefs(next: Preferences) {
    if (savingPrefs) return;
    const previous = prefs;
    setPrefs(next);
    setSavingPrefs(true);
    try {
      const result = await write<Preferences>(
        "/assistant/preferences",
        next,
        "PUT",
      );
      setPrefs(result);
      if (!result.typewriter) finishTyping();
    } catch (e) {
      setPrefs(previous);
      setError((e as Error).message);
    } finally {
      setSavingPrefs(false);
    }
  }
  function animate(message: Message) {
    if (!prefs.typewriter || reduced) return;
    const parts =
      typeof Intl.Segmenter === "function"
        ? Array.from(
            new Intl.Segmenter("pt-BR", { granularity: "grapheme" }).segment(
              message.text,
            ),
            (s) => s.segment,
          )
        : Array.from(message.text);
    let count = 0;
    setTyping({ id: message.id, count, parts });
    timer.current = setInterval(() => {
      count = Math.min(
        parts.length,
        count + Math.max(3, Math.ceil(parts.length / 30)),
      );
      setTyping({ id: message.id, count, parts });
      if (count >= parts.length) finishTyping();
    }, 30);
  }
  async function send(text = draft, existingId?: number) {
    if (!text.trim() || sending.current || typing || !status?.enabled) return;
    if (photoBusy && !existingId) return;
    sending.current = true;
    if (finalPoseTimer.current) clearTimeout(finalPoseTimer.current);
    reactionStarted.current = performance.now();
    const initialExpression = initialReaction(text);
    setPose(initialExpression);
    setStreaming("");
    streamed.current = false;
    setPhase("context");
    processTimer.current = setTimeout(() => {
      if (
        sending.current &&
        !streamed.current &&
        !["concerned", "sad", "angry", "surprised", "shy", "sleepy"].includes(
          initialExpression,
        )
      )
        setPose("thinking");
    }, 800);
    setBusy(true);
    setError("");
    setShowHistory(false);
    setSettings(false);
    setDraft("");
    const version = ++sequence.current;
    const abort = new AbortController();
    controller.current = abort;
    const request = crypto.randomUUID();
    try {
      let id = existingId ?? conversation;
      if (!id) {
        const created = await api<Conversation>("/assistant/conversations", {
          method: "POST",
          signal: abort.signal,
        });
        if (version !== sequence.current) return;
        id = created.id;
        setConversation(id);
        sessionStorage.setItem(storageKey, String(id));
      }
      pending.current = { conversation: id, request };
      setMessages((previous) => [
        ...previous,
        {
          id: -Date.now(),
          role: "user",
          text: text.trim(),
          status: "completed",
          mode: "catalog",
          request_id: request,
          context: context || {},
          sources: [],
          actions: [],
        },
      ]);
      const answer = await api<Message>(
        `/assistant/conversations/${id}/messages`,
        {
          method: "POST",
          signal: abort.signal,
          body: JSON.stringify({
            text,
            request_id: request,
            context: context ? { kind: context.kind, id: context.id } : null,
          }),
        },
      );
      if (version !== sequence.current) return;
      if (processTimer.current) clearTimeout(processTimer.current);
      pending.current = null;
      setMessages((previous) => [
        ...previous.filter(
          (m) => !(m.role === "assistant" && m.request_id === request),
        ),
        answer,
      ]);
      setStreaming("");
      const finalExpression = answer.expression || "greeting";
      const hold = Math.max(
        0,
        750 - (performance.now() - reactionStarted.current),
      );
      if (hold && prefs.motion && !reduced)
        finalPoseTimer.current = setTimeout(
          () => setPose(finalExpression),
          hold,
        );
      else setPose(finalExpression);
      // Text already arrived progressively from ChatGPT; do not replay typing.
      if (!streamed.current) animate(answer);
    } catch (e) {
      if (version === sequence.current && (e as Error).name !== "AbortError") {
        setError((e as Error).message);
        setPose("concerned");
        setStreaming("");
        setDraft(text);
        if (pending.current) {
          const id = pending.current.conversation;
          try {
            const result = await api<Conversation>(
              `/assistant/conversations/${id}`,
            );
            if (version === sequence.current)
              setMessages(result.messages || []);
          } catch {
            /* Keep the question for retry. */
          }
        }
      }
    } finally {
      if (version === sequence.current) {
        sending.current = false;
        setBusy(false);
        pending.current = null;
      }
    }
  }
  async function uploadPhoto(file?: File) {
    if (!file || busy || photoBusy || !status?.enabled) return;
    setPhotoBusy(true);
    setError("");
    const version = sequence.current;
    try {
      if (file.size > 5 * 1024 * 1024)
        throw new Error("A foto deve ter até 5 MB.");
      let id = conversation;
      if (!id) {
        const created = await api<Conversation>("/assistant/conversations", {
          method: "POST",
        });
        id = created.id;
        if (sequence.current !== version) {
          await api(`/assistant/conversations/${id}`, {
            method: "DELETE",
          }).catch(() => {});
          return;
        }
        setConversation(id);
      }
      const body = new FormData();
      body.set("file", file);
      const uploaded = await api<{ id: number; url: string }>(
        `/assistant/conversations/${id}/attachments`,
        { method: "POST", body },
      );
      if (sequence.current !== version) return;
      setPhotos((current) => [...current, uploaded]);
      setPhotoBusy(false);
      await send(
        "Analise a imagem da minha planta: descreva o que você vê e ajude com a identificação provável e os cuidados.",
        id,
      );
    } catch (e) {
      if (sequence.current === version) setError((e as Error).message);
    } finally {
      if (sequence.current === version) setPhotoBusy(false);
    }
  }
  function execute(action: Action) {
    collapse();
    if (
      action.kind === "open_product" &&
      data.products.some((p) => p.id === action.id && p.active)
    )
      go("product", action.id);
    if (action.kind === "open_species") {
      const s = data.species.find((s) => s.id === action.id);
      if (s) openModal("species-detail", s);
    }
    if (
      action.kind === "open_article" &&
      data.articles.some((a) => a.id === action.id)
    )
      go("learn", action.id);
    if (
      action.kind === "open_service" &&
      data.services.some((s) => s.id === action.id && s.active)
    )
      go("service-detail", action.id);
    if (action.kind === "request_quote") {
      const service = data.services.find((s) => s.id === action.id && s.active);
      if (service) {
        if (service.delivery_mode === "Virtual")
          openModal("landscape-studio", { service });
        else openModal("quote-form", { id: service.id });
      }
    }
  }
  useEffect(() => {
    let alive = true;
    Promise.all([
      api<Status>("/assistant/status"),
      api<Preferences>("/assistant/preferences"),
    ])
      .then(([state, preference]) => {
        if (alive) {
          setStatus(state);
          setPrefs(preference);
        }
      })
      .catch((e) => {
        if (alive) setError((e as Error).message);
      });
    sessionStorage.removeItem(storageKey);
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const motion = () => setReduced(media.matches);
    motion();
    media.addEventListener("change", motion);
    const voices = () =>
      setLocalVoice(
        "speechSynthesis" in window &&
          window.speechSynthesis
            .getVoices()
            .some((v) => v.localService && v.lang.startsWith("pt")),
      );
    voices();
    if ("speechSynthesis" in window)
      window.speechSynthesis.addEventListener("voiceschanged", voices);
    return () => {
      alive = false;
      sequence.current++;
      controller.current?.abort();
      if (timer.current) clearInterval(timer.current);
      if (processTimer.current) clearTimeout(processTimer.current);
      if (finalPoseTimer.current) clearTimeout(finalPoseTimer.current);
      const p = pending.current;
      if (p)
        write(
          `/assistant/conversations/${p.conversation}/messages/${p.request}/cancel`,
          {},
        ).catch(() => {});
      media.removeEventListener("change", motion);
      if ("speechSynthesis" in window) {
        window.speechSynthesis.removeEventListener("voiceschanged", voices);
        window.speechSynthesis.cancel();
      }
    };
  }, [user.id]);
  useEffect(() => {
    const ask = (event: Event) => {
      const ctx = (event as CustomEvent<Context>).detail;
      setContext(ctx);
      setHidden(false);
      setVisible(true);
      setSettings(!prefs.enabled);
      setShowHistory(false);
      setError("");
    };
    window.addEventListener(eventName, ask);
    return () => window.removeEventListener(eventName, ask);
  }, [prefs.enabled]);
  useEffect(() => {
    if (blocked) {
      collapse();
    }
  }, [blocked]);
  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight });
  }, [messages, busy, typing?.count, streaming]);
  useEffect(() => {
    if (visible) input.current?.focus();
  }, [visible]);
  useEffect(() => {
    if (reduced) finishTyping();
  }, [reduced]);
  useEffect(() => {
    if (!busy) return;
    let alive = true;
    let polling = false;
    const abort = new AbortController();
    const poll = setInterval(async () => {
      const p = pending.current;
      if (!p || polling) return;
      const version = sequence.current;
      polling = true;
      try {
        const result = await api<{
          request_id: string;
          phase: string;
          text?: string;
          expression?: RafinhaExpression;
        }>(`/assistant/conversations/${p.conversation}/progress`, {
          signal: abort.signal,
        });
        if (
          alive &&
          version === sequence.current &&
          pending.current?.request === p.request &&
          result.request_id === p.request
        ) {
          setPhase(result.phase);
          setStreaming(result.text || "");
          if (result.text) {
            streamed.current = true;
            if (processTimer.current) clearTimeout(processTimer.current);
            setPose(result.expression || "explaining");
          }
        }
      } catch {
        /* The main request reports the error. */
      } finally {
        polling = false;
      }
    }, 350);
    return () => {
      alive = false;
      abort.abort();
      clearInterval(poll);
    };
  }, [busy]);
  const currentReply = !busy
    ? messages.filter((m) => m.role === "assistant").at(-1)
    : undefined;
  const renderAnswer = (m: Message) => {
    const images = m.images || [];
    const separator = images.length ? m.text.indexOf("\n\n") : -1;
    const introduction = separator >= 0 ? m.text.slice(0, separator) : m.text;
    const details = separator >= 0 ? m.text.slice(separator + 2) : "";
    return (
      <>
        <RafinhaMessageText text={introduction} sources={m.sources} />
        <SearchImageGallery images={images} />
        {details && <RafinhaMessageText text={details} sources={m.sources} />}
      </>
    );
  };
  const renderMessage = (m: Message) => (
    <div key={m.id} className={`rafinha-message ${m.role}`}>
      <small>
        {m.role === "user" ? "Você" : "Rafinha"}
        {m.role === "assistant"
          ? ` · ${SOURCE_LABELS[m.meta?.source_type || "catalog"] || "Catálogo"}`
          : ""}
        {m.role === "assistant" && m.meta?.source_type !== "web" && (
          <span> · {AI_MODE_LABELS[m.mode] || "Resposta guiada"}</span>
        )}
      </small>
      {m.role === "assistant" &&
      m.status === "completed" &&
      typing?.id !== m.id ? (
        renderAnswer(m)
      ) : (
        <p aria-hidden={typing?.id === m.id}>
          {typing?.id === m.id
            ? typing.parts.slice(0, typing.count).join("")
            : m.status === "pending"
              ? "Preparando a orientação…"
              : m.text}
        </p>
      )}
      {m.role === "assistant" &&
        m.status === "completed" &&
        typing?.id !== m.id && (
          <>
            <div className="rafinha-actions">
              {m.actions.map((a) => (
                <button
                  type="button"
                  key={`${a.kind}-${a.id}`}
                  onClick={() => execute(a)}
                >
                  {a.label}
                </button>
              ))}
            </div>
            {m.sources.length > 0 && (
              <details>
                <summary>Fontes consultadas ({m.sources.length})</summary>
                {m.sources
                  .filter((s) => publicWebUrl(s.url))
                  .map((s) => (
                    <a
                      key={s.url}
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {s.title}
                    </a>
                  ))}
              </details>
            )}
            {prefs.voice && localVoice && (
              <button
                type="button"
                className="text-button"
                onClick={() => speech(m.text)}
              >
                <Volume2 size={14} />
                Ouvir resposta
              </button>
            )}
          </>
        )}
    </div>
  );
  if (blocked || hidden || (status && !status.enabled)) return null;
  if (!prefs.enabled && !visible) return null;
  const last = messages
    .filter((m) => m.role === "assistant" && m.status === "completed")
    .at(-1);
  return (
    <aside
      className={`rafinha ${visible ? "is-open" : ""} ${prefs.motion && !reduced ? "has-motion" : ""}`}
      aria-label="Assistente Rafinha"
    >
      {!visible ? (
        <div className="rafinha-launcher">
          <button
            type="button"
            className="rafinha-open"
            disabled={!status}
            aria-busy={!status}
            onClick={() => setVisible(true)}
            aria-label="Fale com o Rafinha"
          >
            <img src={expressionAsset("welcome")} alt="" />
            <span>
              Fale com o<br />
              <strong>Rafinha</strong>
            </span>
          </button>
          <button
            type="button"
            className="rafinha-hide"
            aria-label="Ocultar Rafinha nesta sessão"
            onClick={() => setHidden(true)}
          >
            <X size={12} />
          </button>
        </div>
      ) : (
        <section
          className="rafinha-panel"
          role="dialog"
          aria-label="Conversa com Rafinha"
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              collapse();
            }
          }}
        >
          <header>
            <div>
              <strong>
                Rafinha <span>🌿</span>
              </strong>
              <small>{effectiveLabel || "Conectando ao catálogo…"}</small>
            </div>
            <div className="rafinha-tools">
              <button
                type="button"
                aria-label="Minimizar Rafinha"
                title="Minimizar e manter a conversa"
                onClick={minimize}
              >
                <Minus size={17} />
              </button>
              <button
                type="button"
                aria-label="Nova conversa"
                onClick={newConversation}
              >
                <Plus size={17} />
              </button>
              <button
                type="button"
                aria-label="Histórico de conversas"
                onClick={history}
              >
                <History size={17} />
              </button>
              <button
                type="button"
                aria-label="Preferências do Rafinha"
                disabled={!status}
                onClick={() => {
                  setSettings(!settings);
                  setShowHistory(false);
                }}
              >
                <Settings size={17} />
              </button>
              <button
                type="button"
                aria-label="Fechar conversa do Rafinha"
                title="Fechar e encerrar esta conversa"
                onClick={() => {
                  collapse();
                }}
              >
                <X size={17} />
              </button>
            </div>
          </header>
          {context && (
            <div className="rafinha-context">
              <span>
                Sobre:{" "}
                {context.label ||
                  {
                    species: data.species.find((s) => s.id === context.id)
                      ?.name,
                    product: data.products.find((p) => p.id === context.id)
                      ?.name,
                    article: data.articles.find((a) => a.id === context.id)
                      ?.title,
                    project: data.projects.find((p) => p.id === context.id)
                      ?.name,
                    quote: `Orçamento ${context.id}`,
                  }[context.kind]}
              </span>
              <button
                type="button"
                aria-label="Remover contexto da conversa"
                onClick={() => setContext(undefined)}
              >
                <X size={14} />
              </button>
            </div>
          )}
          {settings ? (
            <div className="rafinha-settings">
              <h3>Do seu jeito</h3>
              {(
                [
                  ["enabled", "Habilitar assistente"],
                  ["motion", "Movimentos do personagem"],
                  ["typewriter", "Texto aparecendo aos poucos"],
                  ["voice", "Exibir opção de ouvir resposta"],
                ] as const
              ).map(([key, label]) => (
                <label key={key}>
                  <input
                    type="checkbox"
                    checked={prefs[key]}
                    disabled={savingPrefs}
                    onChange={(e) =>
                      savePrefs({ ...prefs, [key]: e.target.checked })
                    }
                  />
                  {label}
                </label>
              ))}
              <p>
                A voz usa uma opção local em português, quando disponível.
                Nenhum som é reproduzido automaticamente.
              </p>
              <button
                className="text-button"
                type="button"
                onClick={() => {
                  setHidden(true);
                  collapse();
                }}
              >
                Ocultar durante esta sessão
              </button>
            </div>
          ) : showHistory ? (
            <div className="rafinha-history">
              <h3>Suas conversas</h3>
              {!conversations.length && <p>Nenhuma conversa salva ainda.</p>}
              {conversations.map((c) => (
                <div key={c.id}>
                  <button type="button" onClick={() => load(c.id)}>
                    {c.title}
                  </button>
                  <button
                    type="button"
                    aria-label={`Excluir conversa ${c.id}`}
                    onClick={() => deleteConversation(c.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div
              className="rafinha-messages"
              ref={log}
              tabIndex={0}
              aria-label="Mensagens da conversa"
            >
              {photos.length > 0 && (
                <div className="rafinha-photo-list">
                  {photos.map((p) => (
                    <PrivatePhoto key={p.id} url={p.url} />
                  ))}
                  <small>
                    Fotos privadas desta conversa. A análise visual utiliza a
                    conexão ChatGPT quando ela está disponível.
                  </small>
                </div>
              )}
              {messages
                .filter((m) => m.id !== currentReply?.id)
                .map(renderMessage)}

              {!messages.length && (
                <div className="rafinha-suggestions">
                  {status?.suggestions.map((s) => (
                    <button
                      type="button"
                      disabled={busy}
                      key={s}
                      onClick={() => send(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {!settings && !showHistory && (
            <div
              className="rafinha-composition"
              aria-label="Rafinha e sua resposta"
            >
              <RafinhaCharacter
                expression={pose}
                motion={prefs.motion && !reduced}
              />
              <div
                className="rafinha-speech-bubble"
                data-mouth-x="0.5"
                data-mouth-y="0.525"
              >
                {busy && streaming ? (
                  <div
                    className="rafinha-message assistant rafinha-streaming"
                    aria-label="Resposta do Rafinha sendo escrita"
                  >
                    <small>Rafinha</small>
                    <RafinhaMessageText text={streaming} sources={[]} />
                  </div>
                ) : busy ? (
                  <p className="rafinha-thinking" role="status">
                    {PHASE_LABELS[phase] || "Deixa eu pensar…"}
                  </p>
                ) : currentReply ? (
                  renderMessage(currentReply)
                ) : (
                  <div className="rafinha-welcome">
                    <p>
                      {status?.greeting ||
                        "Olá! Vamos cuidar do seu espaço verde?"}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
          <span className="sr-only" aria-live="polite" aria-atomic="true">
            {!typing && !busy ? last?.text : ""}
          </span>
          {error && (
            <div className="rafinha-error" role="alert">
              <span>{error}</span>
              <button type="button" onClick={() => send(draft)}>
                Tentar novamente
              </button>
            </div>
          )}
          {typing && (
            <button
              type="button"
              className="rafinha-complete"
              onClick={() => finishTyping()}
            >
              Mostrar resposta completa
            </button>
          )}
          {!settings && !showHistory && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              <label className="sr-only" htmlFor="rafinha-message">
                Sua mensagem para o Rafinha
              </label>
              <textarea
                id="rafinha-message"
                ref={input}
                disabled={photoBusy || !status?.enabled}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder={
                  status?.enabled
                    ? "Escreva sua mensagem para o Rafinha…"
                    : "Preparando o Rafinha…"
                }
                maxLength={2000}
                rows={2}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
              />
              <label className="rafinha-attach" title="Anexar foto privada">
                <Camera size={18} />
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  aria-label="Anexar foto da planta"
                  disabled={busy || photoBusy || !status?.enabled}
                  onChange={(e) => {
                    uploadPhoto(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
              </label>
              {busy ? (
                <button
                  type="button"
                  aria-label="Interromper resposta"
                  onClick={() => stop()}
                >
                  <Square size={17} />
                </button>
              ) : (
                <button
                  type="submit"
                  aria-label="Enviar mensagem ao Rafinha"
                  disabled={
                    !draft.trim() || !!typing || photoBusy || !status?.enabled
                  }
                >
                  <Send size={18} />
                </button>
              )}
            </form>
          )}
        </section>
      )}
    </aside>
  );
}

export function RafinhaSettings() {
  const [config, setConfig] = useState<Configuration | null>(null),
    [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false),
    [note, setNote] = useState("");
  useEffect(() => {
    Promise.all([
      api<Configuration>("/assistant/configuration"),
      api<Status>("/assistant/status"),
    ])
      .then(([c, s]) => {
        setConfig(c);
        setStatus(s);
      })
      .catch((e) => setNote((e as Error).message));
  }, []);
  if (!config)
    return (
      <p role="status">{note || "Carregando configurações do Rafinha…"}</p>
    );
  return (
    <section className="rafinha-admin">
      <h3>
        <Sparkles size={18} />
        Rafinha · assistente do cliente
      </h3>
      <p>
        {status?.label}. O endereço e o modelo de IA local são configurados no
        ambiente do servidor.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            setConfig(
              await write<Configuration>(
                "/assistant/configuration",
                config,
                "PUT",
              ),
            );
            setNote("Configurações do Rafinha salvas.");
          } catch (e) {
            setNote((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={config.enabled}
            onChange={(e) =>
              setConfig({ ...config, enabled: e.target.checked })
            }
          />
          Habilitar Rafinha no portal
        </label>
        <label>
          Mensagem inicial
          <textarea
            rows={3}
            maxLength={500}
            minLength={10}
            required
            value={config.greeting}
            onChange={(e) => setConfig({ ...config, greeting: e.target.value })}
          />
        </label>
        <label>
          Perguntas sugeridas (uma por linha)
          <textarea
            rows={4}
            value={config.suggestions.join("\n")}
            onChange={(e) =>
              setConfig({ ...config, suggestions: e.target.value.split("\n") })
            }
          />
        </label>
        <div className="row-actions">
          <button
            type="submit"
            className="button primary small"
            disabled={busy}
          >
            Salvar Rafinha
          </button>
          <button
            type="button"
            className="button secondary small"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                const r = await write<{ text: string; mode: string }>(
                  "/assistant/test",
                  {
                    text: "Como cuidar da Lavanda?",
                    request_id: crypto.randomUUID(),
                  },
                );
                setNote(
                  `${AI_MODE_LABELS[r.mode] || "Resposta guiada"}: ${r.text}`,
                );
              } catch (e) {
                setNote((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            Testar atendimento
          </button>
        </div>
      </form>
      {note && (
        <p className="rafinha-admin-note" role="status">
          {note}
        </p>
      )}
    </section>
  );
}
