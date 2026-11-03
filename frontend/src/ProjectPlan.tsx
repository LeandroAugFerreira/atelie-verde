import { FileText, Pencil, Ruler } from "lucide-react";
import { useGreen } from "./context";
import { Panel } from "./ReferenceUI";
import { Empty } from "./components";
import { LandscapePlan, exportMemorial } from "./LandscapePlan";
import type { Project, Quote } from "./types";
import { AskRafinha } from "./RafinhaAssistant";

export function LandscapeOverview({ record }: { record: Project | Quote }) {
  const { data } = useGreen();
  const brief = record.brief;
  if (!brief?.width)
    return <Empty>A planta visual será definida com o paisagista.</Empty>;
  return (
    <div className="landscape-overview">
      <LandscapePlan brief={brief} species={data.species} />
      <div className="landscape-memo">
        <h3>Memorial do planejamento</h3>
        <AskRafinha
          context={{
            kind: "name" in record ? "project" : "quote",
            id: record.id,
            label: "name" in record ? record.name : "Levantamento do orçamento",
          }}
          label="Entender meu planejamento com o Rafinha"
        />
        <dl>
          {[
            [
              "Dimensões",
              `${brief.width} × ${brief.length} m · ${brief.width * brief.length} m²`,
            ],
            ["Luminosidade", brief.light],
            ["Solo", brief.soil],
            ["Drenagem", brief.drainage],
            ["Manutenção", brief.maintenance],
            ["Objetivos", brief.objective || "A definir"],
          ].map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        {brief.notes && <p>{brief.notes}</p>}
        <button
          className="button secondary"
          onClick={() => exportMemorial(brief, data.species, record.address)}
        >
          <FileText size={16} />
          Baixar memorial do projeto
        </button>
      </div>
    </div>
  );
}
export function ProjectPlan({ project }: { project: Project }) {
  const { user, open } = useGreen();
  return (
    <Panel
      title="Planta 2D e memorial"
      Icon={Ruler}
      className="project-plan-panel"
      actions={
        <div className="row-actions">
          <button
            className="button secondary small"
            onClick={() => open("landscape-view", project)}
          >
            Ampliar planta
          </button>
          {user.role === "admin" && project.status !== "Finalizado" && (
            <button
              className="button primary"
              onClick={() => open("landscape-studio", { project })}
            >
              <Pencil size={16} />
              Editar planta
            </button>
          )}
        </div>
      }
    >
      <LandscapeOverview record={project} />
    </Panel>
  );
}
