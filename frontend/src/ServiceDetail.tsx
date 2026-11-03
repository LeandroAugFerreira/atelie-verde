import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  Monitor,
  MapPin,
  FileText,
} from "lucide-react";
import { useGreen } from "./context";
import { Sprite } from "./ReferenceUI";
import { Empty } from "./components";
import { money } from "./types";

export function ServiceDetailPage() {
  const { data, selectedId, go, open } = useGreen();
  const service = data.services.find((s) => s.id === selectedId && s.active);
  if (!service) return <Empty>Serviço não encontrado.</Empty>;
  const details = service.details;
  return (
    <div className="service-detail-page">
      <button className="text-button" onClick={() => go("services")}>
        <ArrowLeft size={16} />
        Voltar aos serviços
      </button>
      <div className="service-detail-hero">
        <div>
          <span className="service-mode">
            {service.delivery_mode === "Virtual" ? (
              <Monitor size={15} />
            ) : (
              <MapPin size={15} />
            )}
            Atendimento {service.delivery_mode?.toLowerCase() || "presencial"}
          </span>
          <h1>{service.name}</h1>
          <p>{service.description}</p>
          <strong>
            A partir de {money(service.price_cents)} / {service.unit}
          </strong>
          <span className="form-hint">
            Escopo, prazo e valor final definidos na proposta.
          </span>
          <button
            className="button primary"
            onClick={() =>
              service.category === "Projeto"
                ? open("landscape-studio", { service })
                : open("quote-form", service)
            }
          >
            {service.delivery_mode === "Virtual"
              ? "Preparar projeto e solicitar orçamento"
              : "Solicitar orçamento"}
            <ArrowRight size={18} />
          </button>
        </div>
        <Sprite name={service.demo_asset || "landscape"} />
      </div>
      <div className="service-detail-sections">
        {[
          { title: "O que este serviço realiza", items: details?.includes },
          { title: "O que você recebe", items: details?.deliverables },
          { title: "Como preparar a solicitação", items: details?.preparation },
          { title: "Documentos e registros", items: details?.documents },
        ].map((section) => (
          <section className="panel" key={section.title}>
            <h2>{section.title}</h2>
            <ul>
              {section.items?.map((item) => (
                <li key={item}>
                  <CheckCircle size={16} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <section className="panel service-process">
        <h2>Etapas do atendimento</h2>
        <ol>
          {details?.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        {service.category === "Projeto" && (
          <p className="form-hint">
            <FileText size={14} />O planejamento inclui planta 2D, espécies e
            memorial; fotos, croquis e documentos podem ser anexados à
            solicitação. A entrega técnica é revisada pelo paisagista.
          </p>
        )}
      </section>
      <div className="service-detail-bottom">
        {details?.sources?.length > 0 && (
          <details className="service-references">
            <summary>Referências do planejamento</summary>
            <ul>
              {details.sources.map((source) => (
                <li key={source.url}>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.title}
                  </a>
                </li>
              ))}
            </ul>
          </details>
        )}
        <button
          className="button primary"
          onClick={() =>
            service.category === "Projeto"
              ? open("landscape-studio", { service })
              : open("quote-form", service)
          }
        >
          Solicitar orçamento
          <ArrowRight size={17} />
        </button>
      </div>
    </div>
  );
}
