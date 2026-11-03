import { ChevronRight, Home } from "lucide-react";
import { useGreen, type Page } from "./context";
import { categories } from "./Forms";

const labels: Record<Page, string> = {
  dashboard: "Dashboard",
  products: "Produtos",
  inventory: "Estoque",
  customers: "Clientes",
  suppliers: "Fornecedores",
  services: "Serviços",
  "service-detail": "Detalhes do serviço",
  quotes: "Orçamentos",
  projects: "Projetos",
  finance: "Financeiro",
  reports: "Relatórios",
  settings: "Configurações",
  home: "Loja",
  catalog: "Produtos",
  product: "Detalhes do produto",
  project: "Detalhes do projeto",
  history: "Meu histórico",
  species: "Biblioteca de espécies",
  learn: "Aprender",
};
type Crumb = { label: string; page: Page; id?: number };

export function NavigationBreadcrumb() {
  const { user, page, selectedId, data, go } = useGreen();
  const root: Page = user.role === "admin" ? "dashboard" : "home";
  const path: Crumb[] = [{ label: labels[root], page: root }];
  if (page !== root) {
    if (page === "product") {
      const product = data.products.find((p) => p.id === selectedId);
      path.push({ label: "Produtos", page: "catalog" });
      if (product)
        path.push({
          label: product.category,
          page: "catalog",
          id: categories.indexOf(product.category) + 1,
        });
      path.push({
        label: product?.name || labels[page],
        page,
        id: selectedId || undefined,
      });
    } else if (page === "catalog" && selectedId && categories[selectedId - 1]) {
      path.push({ label: "Produtos", page: "catalog" });
      path.push({
        label: categories[selectedId - 1],
        page: "catalog",
        id: selectedId,
      });
    } else if (page === "project") {
      path.push({ label: "Projetos", page: "projects" });
      path.push({
        label:
          data.projects.find((p) => p.id === selectedId)?.name || labels[page],
        page,
        id: selectedId || undefined,
      });
    } else if (page === "service-detail") {
      path.push({ label: "Serviços", page: "services" });
      path.push({
        label:
          data.services.find((s) => s.id === selectedId)?.name || labels[page],
        page,
        id: selectedId || undefined,
      });
    } else if (page === "learn" && selectedId) {
      path.push({ label: "Aprender", page: "learn" });
      path.push({
        label:
          data.articles.find((a) => a.id === selectedId)?.title ||
          "Guia de cultivo",
        page,
        id: selectedId,
      });
    } else {
      if (page === "species")
        path.push({
          label: user.role === "admin" ? "Estoque" : "Aprender",
          page: user.role === "admin" ? "inventory" : "learn",
        });
      if (page === "products" && user.role === "admin")
        path.push({ label: "Estoque", page: "inventory" });
      path.push({ label: labels[page], page });
    }
  }
  return (
    <nav className="navigation-breadcrumb" aria-label="Caminho de navegação">
      <ol>
        {path.map((item, index) => (
          <li key={`${item.page}-${item.id || 0}-${index}`}>
            {index > 0 && <ChevronRight size={13} aria-hidden="true" />}
            {index === path.length - 1 ? (
              <span aria-current="page">
                {index === 0 && <Home size={14} aria-hidden="true" />}
                {item.label}
              </span>
            ) : (
              <button type="button" onClick={() => go(item.page, item.id)}>
                {index === 0 && <Home size={14} aria-hidden="true" />}
                {item.label}
              </button>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
