import { test, expect, type Page } from "@playwright/test";
import { resolve } from "node:path";

async function admin(page: Page) {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  await expect(page.locator(".admin-sidebar")).toBeVisible();
}
async function tab(page: Page, name: string) {
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name, exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name, level: 1, exact: true }),
  ).toBeVisible();
}

async function adminData(page: Page, path: string) {
  const token = await page.evaluate(() =>
    sessionStorage.getItem("greenscape-token"),
  );
  const response = await page.request.get(`/api/${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBe(true);
  return response.json();
}

test("Filtros combinados, busca sem acento e seleção coerente", async ({
  page,
}) => {
  await admin(page);
  await tab(page, "Estoque");
  const products = page.locator(".inventory-panel");
  await expect(
    products.getByRole("region", { name: "Filtros avançados" }),
  ).not.toBeVisible();
  await products.getByRole("button", { name: "Próxima página" }).click();
  await products.getByRole("button", { name: "Filtros", exact: true }).click();
  await products
    .getByLabel("Categoria", { exact: true })
    .selectOption("Plantas");
  await products.getByLabel("Tipo de planta").selectOption("Cactos");
  await expect(products.locator(".filter-count")).toHaveText("4 resultados");
  await expect(products.locator(".pagination")).toContainText(
    "Mostrando 1 a 4",
  );
  await products.getByLabel("Estoque / situação").selectOption("Normal");
  await expect(products.locator(".filter-count")).toHaveText("4 resultados");
  await products.getByLabel("Buscar produto, SKU ou espécie…").fill("dedo");
  await expect(products.locator(".filter-count")).toHaveText("1 resultado");
  await products.getByRole("button", { name: "Limpar filtros" }).click();
  await expect(products.getByLabel("Tipo de planta")).toHaveValue("");
  await expect(products.locator(".filter-count")).toHaveText("61 resultados");

  await tab(page, "Clientes");
  const customers = page.locator(".customers-panel");
  const allCustomers = await adminData(page, "customers");
  const allProjects = await adminData(page, "projects");
  await customers
    .getByLabel("Buscar nome, e-mail ou telefone…")
    .fill("sao paulo");
  await expect(customers.locator("tbody tr")).toHaveCount(2);
  await customers.locator("tbody tr").filter({ hasText: "Rafael" }).click();
  await expect(page.locator(".profile-header")).toContainText("Rafael");
  await customers.getByRole("button", { name: "Limpar filtros" }).click();
  await customers.getByRole("button", { name: "Filtros", exact: true }).click();
  await customers
    .getByLabel("Projetos", { exact: true })
    .selectOption("Com projetos");
  await customers
    .getByLabel("Cidade", { exact: true })
    .selectOption("São Paulo - SP");
  const matchingCustomers = allCustomers.filter(
    (customer: { id: number; city: string }) =>
      customer.city === "São Paulo - SP" &&
      allProjects.some(
        (project: { customer_id: number }) =>
          project.customer_id === customer.id,
      ),
  );
  expect(matchingCustomers.length).toBeGreaterThan(0);
  await expect(customers.locator(".filter-count")).toHaveText(
    `${matchingCustomers.length} ${matchingCustomers.length === 1 ? "resultado" : "resultados"}`,
  );
  await expect(customers.locator("tbody tr")).toHaveCount(
    matchingCustomers.length,
  );
  await customers
    .getByLabel("Buscar nome, e-mail ou telefone…")
    .fill("ninguém cadastrado");
  await expect(customers).toContainText("Nenhum cliente encontrado");
  await expect(page.locator(".profile-header")).toHaveCount(0);

  await tab(page, "Serviços");
  const services = page.locator(".services-panel");
  await services.getByRole("button", { name: "Filtros", exact: true }).click();
  await services.getByLabel("Status do serviço").selectOption("Inativo");
  await expect(services.locator(".filter-count")).toHaveText("0 resultados");
  await expect(services).toContainText("Nenhum serviço encontrado");
  await services.getByRole("button", { name: "Limpar filtros" }).click();
  await expect(services.locator(".filter-count")).toHaveText("8 resultados");

  await tab(page, "Orçamentos");
  const quotes = page.locator(".quotes-panel");
  await quotes.getByRole("button", { name: "Filtros", exact: true }).click();
  await quotes.getByLabel("Status do orçamento").selectOption("Aprovado");
  await expect(quotes.locator(".filter-count")).toHaveText("1 resultado");
  await quotes.getByLabel("Solicitado a partir de").fill("2099-01-01");
  await expect(quotes.locator(".filter-count")).toHaveText("0 resultados");
  await expect(page.locator(".quote-profile")).toHaveCount(0);
  await quotes.getByRole("button", { name: "Limpar filtros" }).click();
  await quotes
    .getByLabel("Buscar código, cliente ou serviço…")
    .fill("ORC-2026-001");
  await expect(quotes.locator(".filter-count")).toHaveText("1 resultado");
  await expect(page.locator(".quote-profile")).toContainText("ORC-001");

  await tab(page, "Projetos");
  await page.getByRole("button", { name: "Filtros", exact: true }).click();
  await page.getByLabel("Etapa", { exact: true }).selectOption("Execução");
  await page
    .getByLabel("Buscar projeto, endereço ou cliente…")
    .fill("Projeto Residencial – Jardim Frontal");
  await expect(page.locator(".filter-count")).toHaveText("1 resultado");
  await expect(page.locator(".project-card")).toHaveCount(1);
});

test("Projetos com referências distintas e prioridade para fotos enviadas", async ({
  page,
}) => {
  await admin(page);
  await tab(page, "Projetos");
  const projects = await adminData(page, "projects");
  const images = page.locator(".project-cover img");
  const references = projects.filter(
    (project: { reference_image_url?: string }) => project.reference_image_url,
  );
  expect(references.length).toBeGreaterThan(0);
  await expect(images).toHaveCount(references.length);
  expect(
    new Set(
      await images.evaluateAll((items) =>
        items.map((el) => (el as HTMLImageElement).src),
      ),
    ).size,
  ).toBe(5);
  const frontal = page
    .locator(".project-card")
    .filter({ hasText: "Jardim Frontal" });
  await expect(frontal).toContainText("Imagem ilustrativa");
  await expect(frontal.locator("img")).toHaveAttribute(
    "src",
    "/projects/jardim-frontal.png",
  );
  await frontal.click();
  await page.getByRole("button", { name: "Fotos", exact: true }).click();
  await expect(page.locator(".project-reference")).toContainText(
    "não representa uma fotografia da obra executada",
  );
  await page
    .locator(".gallery-section input[type=file]")
    .setInputFiles(resolve("public/plants/plinia-cauliflora-1.jpg"));
  await expect(page.locator(".gallery-section .photo")).toBeVisible();
  const token = await page.evaluate(() =>
    sessionStorage.getItem("greenscape-token"),
  );
  const auth = { Authorization: `Bearer ${token}` };
  const photos = await (
    await page.request.get("/api/images/projects/1", { headers: auth })
  ).json();
  try {
    await tab(page, "Projetos");
    await expect(frontal.locator(".project-cover")).toHaveAttribute(
      "data-source",
      "uploaded",
    );
    await expect(frontal).toContainText("Foto do projeto");
    await page.reload();
    await tab(page, "Projetos");
    await expect(frontal.locator(".project-cover")).toHaveAttribute(
      "data-source",
      "uploaded",
    );
  } finally {
    for (const photo of photos)
      await page.request.delete(`/api/images/${photo.id}`, { headers: auth });
  }
});

test("Cards, paginação e decorações cabem em todas as abas administrativas", async ({
  page,
}) => {
  await admin(page);
  for (const width of [1672, 1366, 1024]) {
    await page.setViewportSize({ width, height: width === 1672 ? 941 : 768 });
    for (const name of [
      "Dashboard",
      "Fornecedores",
      "Estoque",
      "Clientes",
      "Serviços",
      "Orçamentos",
      "Projetos",
      "Financeiro",
      "Relatórios",
      "Configurações",
    ]) {
      await tab(page, name);
      expect(
        await page.locator(".page-canvas").evaluate((canvas) => {
          const bounds = canvas.getBoundingClientRect();
          return [
            ...canvas.querySelectorAll<HTMLElement>(
              ".kpi, .panel, .project-card",
            ),
          ].every((card) => {
            const r = card.getBoundingClientRect();
            return (
              r.width > 0 &&
              r.left >= bounds.left - 1 &&
              r.right <= bounds.right + 1 &&
              (card.classList.contains("project-card") ||
                r.bottom <= bounds.bottom + 1)
            );
          });
        }),
        `${name} em ${width}px`,
      ).toBe(true);
      expect(
        await page.locator(".kpi").evaluateAll((cards) =>
          cards.every((card) => {
            const decoration = card
              .querySelector(".kpi-plant")
              ?.getBoundingClientRect();
            return (
              !decoration || (decoration.width <= 48 && decoration.height <= 68)
            );
          }),
        ),
      ).toBe(true);
      expect(
        await page
          .locator(".table-scroll")
          .evaluateAll((items) =>
            items.every((el) => el.scrollWidth <= el.clientWidth + 1),
          ),
        `${name}: tabelas sem rolagem horizontal em ${width}px`,
      ).toBe(true);
      if (["Dashboard", "Financeiro"].includes(name)) {
        await expect(
          page.locator(".split.charts .panel-content").first(),
        ).toBeVisible();
        const chartOverflow = await page
          .locator(".split.charts .panel-content")
          .evaluateAll((items) =>
            items
              .map((el) => ({
                label: el.closest(".panel")?.querySelector("h2")?.textContent,
                width: el.clientWidth,
                scrollWidth: el.scrollWidth,
                height: el.clientHeight,
                scrollHeight: el.scrollHeight,
              }))
              .filter(
                (item) =>
                  item.scrollHeight > item.height + 1 ||
                  item.scrollWidth > item.width + 1,
              ),
          );
        expect(
          chartOverflow,
          `${name} ${width}px: gráficos dentro dos cards`,
        ).toEqual([]);
        expect(
          await page
            .locator(".split.charts .panel-content")
            .evaluateAll((items) =>
              items.every(
                (el) =>
                  el.scrollHeight <= el.clientHeight + 1 &&
                  el.scrollWidth <= el.clientWidth + 1,
              ),
            ),
        ).toBe(true);
        const overflowReport = await page
          .locator(".donut, .donut-legend")
          .evaluateAll((items) =>
            items
              .map((el) => {
                const body = el
                    .closest(".panel-content")!
                    .getBoundingClientRect(),
                  box = el.getBoundingClientRect();
                return {
                  class: el.className,
                  left: box.left,
                  right: box.right,
                  top: box.top,
                  bottom: box.bottom,
                  body: {
                    left: body.left,
                    right: body.right,
                    top: body.top,
                    bottom: body.bottom,
                  },
                };
              })
              .filter(
                (x) =>
                  x.top < x.body.top - 1 ||
                  x.bottom > x.body.bottom + 1 ||
                  x.left < x.body.left - 1 ||
                  x.right > x.body.right + 1,
              ),
          );
        expect(overflowReport, `${name} em ${width}px`).toEqual([]);
        expect(
          await page.locator(".donut, .donut-legend").evaluateAll((items) =>
            items.every((el) => {
              const body = el
                .closest(".panel-content")!
                .getBoundingClientRect();
              const box = el.getBoundingClientRect();
              return (
                box.top >= body.top - 1 &&
                box.bottom <= body.bottom + 1 &&
                box.left >= body.left - 1 &&
                box.right <= body.right + 1
              );
            }),
          ),
        ).toBe(true);
        expect(
          await page.locator(".cash-chart").evaluate((el) => {
            const box = el.getBoundingClientRect();
            const view = (el as SVGSVGElement).viewBox.baseVal;
            return (
              Math.abs(box.width - view.width) < 2 &&
              Math.abs(box.height - view.height) < 2
            );
          }),
        ).toBe(true);
      }
      expect(
        await page.locator(".decorative-plant").evaluateAll((items) =>
          items.every((el) => {
            const css = getComputedStyle(el);
            return (
              css.objectFit === "contain" &&
              css.clipPath === "none" &&
              css.opacity === "0.65"
            );
          }),
        ),
      ).toBe(true);
      if (name === "Financeiro") {
        expect(
          await page.locator(".split.equal > .panel").evaluateAll((items) =>
            items.every((el) => {
              // The viewport shell deliberately resizes cards. Require three
              // usable rows, instead of an obsolete fixed card height.
              const scroller = el.querySelector(".table-scroll");
              const header = el.querySelector("thead");
              const row = el.querySelector("tbody tr");
              const count = el.querySelectorAll("tbody tr").length;
              if (!scroller || !header || !row) return count === 0;
              return (
                scroller.clientHeight - header.getBoundingClientRect().height >=
                row.getBoundingClientRect().height * Math.min(3, count) - 2
              );
            }),
          ),
        ).toBe(true);
      }
      expect(
        await page
          .locator(".table-scroll td")
          .evaluateAll((items) =>
            items.every((el) => getComputedStyle(el).whiteSpace === "nowrap"),
          ),
      ).toBe(true);
      expect(
        await page.locator(".pagination").evaluateAll((items) =>
          items.every((el) => {
            const r = el.getBoundingClientRect(),
              card = el.closest(".panel")?.getBoundingClientRect();
            return !card || (r.top >= card.top && r.bottom <= card.bottom);
          }),
        ),
      ).toBe(true);
      if (width === 1366)
        await page.screenshot({
          path: `../docs/screenshots/admin-${name
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")}-1366.png`,
        });
    }
    await tab(page, "Estoque");
    const panel = page.locator(".inventory-panel");
    await panel.getByRole("button", { name: "Filtros", exact: true }).click();
    const heading = await panel.locator(".panel-heading").boundingBox();
    await panel.locator(".table-scroll").evaluate((el) => {
      el.scrollTop = el.scrollHeight;
      el.scrollLeft = el.scrollWidth;
    });
    expect(await panel.locator(".panel-heading").boundingBox()).toEqual(
      heading,
    );
    const footer = await panel.locator(".pagination").boundingBox();
    expect(
      footer && footer.y + footer.height <= (width === 1672 ? 941 : 768),
    ).toBeTruthy();
  }
});
