import { useState } from "react";
import { Camera, Trash2 } from "lucide-react";
import { api, write } from "./api";
import { Avatar } from "./ReferenceUI";
import { SaveButton } from "./components";
import type { User } from "./types";

export function ProfileForm({
  user,
  onChange,
  onSaved,
}: {
  user: User;
  onChange: (u: User) => void;
  onSaved: (u: User) => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  async function photo(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (file.size > 5 * 1024 * 1024)
        throw new Error("A foto deve ter até 5 MB.");
      const form = new FormData();
      form.append("file", file);
      await api(`/images/users/${user.id}`, { method: "POST", body: form });
      onChange(await api<User>("/auth/me"));
      setMessage("Foto do perfil atualizada.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function removePhoto() {
    const id = user.avatar_url.match(/\/images\/(\d+)\/content/)?.[1];
    if (!id) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api(`/images/${id}`, { method: "DELETE" });
      onChange(await api<User>("/auth/me"));
      setMessage("Foto removida.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form
      className="form profile-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError("");
        try {
          onSaved(
            await write<User>(
              "/auth/profile",
              Object.fromEntries(new FormData(e.currentTarget)),
              "PUT",
            ),
          );
        } catch (err) {
          setError((err as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <div className="profile-photo-editor">
        <Avatar name={user.name} url={user.avatar_url} />
        <div>
          <h3>Sua foto de perfil</h3>
          <p>JPG, PNG ou WebP · até 5 MB</p>
          <label className="button secondary upload-control">
            <Camera size={17} />
            {user.avatar_url ? "Trocar foto" : "Enviar foto"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              aria-label="Enviar foto do perfil"
              disabled={busy}
              onChange={(e) => {
                photo(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </label>
          {user.avatar_url && (
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={removePhoto}
            >
              <Trash2 size={15} />
              Remover foto
            </button>
          )}
        </div>
      </div>
      <div className="form-grid">
        {[
          { key: "name", label: "Nome completo", required: true, max: 100 },
          {
            key: "email",
            label: "E-mail",
            type: "email",
            required: true,
            max: 254,
          },
          { key: "phone", label: "Telefone", max: 30 },
          { key: "city", label: "Cidade / UF", max: 100 },
        ].map((f) => (
          <label key={f.key}>
            {f.label}
            <input
              name={f.key}
              type={f.type || "text"}
              defaultValue={String(user[f.key as keyof User] || "")}
              required={f.required}
              maxLength={f.max}
            />
          </label>
        ))}
      </div>
      <label>
        Endereço
        <input name="address" defaultValue={user.address} maxLength={500} />
      </label>
      {message && (
        <p className="green-text" role="status">
          {message}
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <SaveButton busy={busy} label="Salvar perfil" />
    </form>
  );
}
