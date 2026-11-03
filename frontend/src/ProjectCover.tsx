import { useEffect, useState } from "react";
import { Image as ImageIcon } from "lucide-react";
import { api } from "./api";
import { Photo } from "./components";
import type { Project } from "./types";

export function ProjectCover({ project }: { project: Project }) {
  const [uploaded, setUploaded] = useState("");
  useEffect(() => {
    let alive = true;
    setUploaded("");
    api<{ id: number; url: string }[]>(`/images/projects/${project.id}`)
      .then((images) => {
        const latest = [...images].sort((a, b) => b.id - a.id)[0];
        if (alive) setUploaded(latest?.url || "");
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [project.id]);
  const url = uploaded || project.reference_image_url;
  return (
    <div
      className="project-cover"
      data-source={uploaded ? "uploaded" : url ? "reference" : "empty"}
    >
      {url ? (
        <Photo
          url={url}
          alt={`${uploaded ? "Foto" : "Referência visual"} — ${project.name}`}
        />
      ) : (
        <div className="project-cover-empty">
          <ImageIcon size={32} />
          <span>Adicione uma foto ao projeto</span>
        </div>
      )}
      {url && (
        <span className="cover-label">
          {uploaded ? "Foto do projeto" : "Imagem ilustrativa"}
        </span>
      )}
    </div>
  );
}
