import { useEffect, useState, type ReactNode } from "react";
import { Leaf, X, ImagePlus, Trash2, LoaderCircle } from "lucide-react";
import { api, imageBlob } from "./api";

export function PlantArt({ variant = 0 }: { variant?: number }) {
  return (
    <svg className="plant-art" viewBox="0 0 240 200" aria-hidden="true">
      <defs>
        <linearGradient id={`leaf${variant}`} x2="1" y2="1">
          <stop stopColor={variant % 2 ? "#558d65" : "#426e4e"} />
          <stop offset="1" stopColor="#183f2d" />
        </linearGradient>
      </defs>
      <ellipse cx="122" cy="184" rx="58" ry="7" fill="#172a1d" opacity=".08" />
      <path
        d="M120 150 Q104 108 120 44 M120 130 Q152 103 166 62 M118 123 Q81 100 67 68"
        fill="none"
        stroke="#457355"
        strokeWidth="4"
      />
      {variant % 3 === 0 ? (
        <>
          <path
            d="M121 86C85 81 85 26 123 21c29 18 34 50-2 65Z"
            fill={`url(#leaf${variant})`}
          />
          <path
            d="M117 119C73 129 51 97 59 56c36 3 64 28 58 63Z"
            fill="#537f58"
          />
          <path
            d="M130 116c-1-40 22-69 59-65 7 42-21 68-59 65Z"
            fill="#386148"
          />
          <path
            d="M112 130c-31 5-56-10-72-37 40-9 73 8 72 37Z"
            fill="#6c955f"
          />
          <path
            d="M135 142c7-36 33-48 65-37-10 32-30 45-65 37Z"
            fill="#6c955f"
          />
        </>
      ) : variant % 3 === 1 ? (
        <>
          <path
            d="M119 155c-25-56-26-112-7-133 22 27 25 81 7 133Z"
            fill={`url(#leaf${variant})`}
          />
          <path
            d="M110 153c-37-33-55-69-46-99 34 9 50 49 46 99Z"
            fill="#598358"
          />
          <path
            d="M129 151c-4-48 9-91 40-106 17 25 4 65-40 106Z"
            fill="#416c4d"
          />
          <path
            d="M110 145C80 148 51 122 42 98c31-4 59 17 68 47Z"
            fill="#83a570"
          />
          <path
            d="M137 151c17-30 40-43 65-39-2 25-30 42-65 39Z"
            fill="#83a570"
          />
        </>
      ) : (
        <>
          <path
            d="M120 152c-41-39-50-75-23-106 29 18 38 64 23 106Z"
            fill="#5f885e"
          />
          <path
            d="M126 141c-20-62-2-99 27-109 24 41 4 87-27 109Z"
            fill={`url(#leaf${variant})`}
          />
          <path
            d="M108 145c-46 3-68-21-70-47 45-8 70 12 70 47Z"
            fill="#87a679"
          />
          <path
            d="M132 150c5-42 33-66 66-51 1 37-26 57-66 51Z"
            fill="#6d925e"
          />
        </>
      )}
      <path
        d="M83 147h79l-10 37H94Z"
        fill={variant % 2 ? "#bf8063" : "#d4b08b"}
      />
      <ellipse cx="122" cy="147" rx="40" ry="7" fill="#b18d6c" />
      <path d="M96 154h49l-5 26h-37Z" fill="#fff" opacity=".12" />
    </svg>
  );
}

export function Photo({
  url,
  variant = 0,
  alt = "Foto cadastrada",
}: {
  url?: string;
  variant?: number;
  alt?: string;
}) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    let alive = true;
    let object = "";
    setSrc("");
    if (
      url?.startsWith("/plants/") ||
      url?.startsWith("/projects/") ||
      url?.startsWith("/catalog-media/")
    ) {
      setSrc(url);
      return;
    }
    if (url)
      imageBlob(url)
        .then((value) => {
          object = value;
          if (alive) setSrc(value);
          else URL.revokeObjectURL(value);
        })
        .catch(() => {});
    return () => {
      alive = false;
      if (object) URL.revokeObjectURL(object);
    };
  }, [url]);
  return src ? (
    <img className="photo" src={src} alt={alt} />
  ) : (
    <PlantArt variant={variant} />
  );
}

export function Badge({ children }: { children: ReactNode }) {
  return (
    <span
      className={`badge ${String(children) === "Execução" || String(children) === "Confirmado" || String(children) === "Aprovado" ? "green" : String(children) === "Orçamento" || String(children) === "Solicitado" ? "amber" : "neutral"}`}
    >
      {children}
    </span>
  );
}
export function Empty({
  children = "Nenhum registro encontrado.",
}: {
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <Leaf size={30} />
      <strong>{children}</strong>
      <span>Os registros aparecerão aqui quando forem cadastrados.</span>
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", esc);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const prior = document.activeElement as HTMLElement | null;
    const frame = requestAnimationFrame(() =>
      document
        .querySelector<HTMLElement>(
          ".modal input, .modal select, .modal button",
        )
        ?.focus(),
    );
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", esc);
      document.body.style.overflow = prev;
      prior?.focus();
    };
  }, [onClose]);
  return (
    <div
      className="overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className={`modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onKeyDown={(e) => {
          if (e.key !== "Tab") return;
          const items = [
            ...e.currentTarget.querySelectorAll<HTMLElement>(
              "button:not(:disabled), input:not(:disabled):not([type=hidden]), select:not(:disabled), textarea:not(:disabled), a[href], summary, [tabindex]:not([tabindex='-1'])",
            ),
          ].filter(
            (el) =>
              el.getClientRects().length > 0 &&
              el.getAttribute("aria-hidden") !== "true",
          );
          const first = items[0],
            last = items[items.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last?.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first?.focus();
          }
        }}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Fechar">
            <X />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

export function Gallery({
  entity,
  id,
  editable,
  onChange,
}: {
  entity: string;
  id: number;
  editable: boolean;
  onChange: () => Promise<void>;
}) {
  const [images, setImages] = useState<{ id: number; url: string }[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const load = () =>
    api<{ id: number; url: string }[]>(`/images/${entity}/${id}`)
      .then(setImages)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, [entity, id]);
  async function upload(file: File) {
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      await api(`/images/${entity}/${id}`, { method: "POST", body: form });
      await load();
      await onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove(imageId: number) {
    setBusy(true);
    try {
      await api(`/images/${imageId}`, { method: "DELETE" });
      await load();
      await onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="gallery-section">
      <div className="section-heading">
        <h3>Fotos do {entity === "quotes" ? "local" : "cadastro"}</h3>
        {editable && (
          <label className={`button secondary ${busy ? "disabled" : ""}`}>
            <ImagePlus size={16} />
            {busy ? "Enviando…" : "Adicionar foto"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              hidden
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) upload(f);
                e.target.value = "";
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
      <div className="gallery">
        {images.map((img, i) => (
          <div key={img.id}>
            <Photo url={img.url} variant={i} />
            {editable && (
              <button
                aria-label="Excluir foto"
                className="icon-button photo-remove"
                disabled={busy}
                onClick={() => remove(img.id)}
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}
        {!images.length && (
          <p className="muted">
            Nenhuma foto adicionada. JPG, PNG ou WebP · até 5 MB.
          </p>
        )}
      </div>
    </div>
  );
}
export function SaveButton({
  busy,
  label = "Salvar",
}: {
  busy: boolean;
  label?: string;
}) {
  return (
    <button className="button primary" type="submit" disabled={busy}>
      {busy && <LoaderCircle size={16} className="spin" />}
      {busy ? "Salvando…" : label}
    </button>
  );
}
