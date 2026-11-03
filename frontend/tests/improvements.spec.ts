import { test, expect, type Page } from "@playwright/test";

async function login(page: Page) {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  await expect(page.locator(".admin-sidebar")).toBeVisible();
  await expect(page.locator(".loading-line")).not.toBeVisible();
}
test("Consumo real no projeto baixa estoque e mantém o custo registrado", async ({
  page,
}) => {
  await login(page);
  const headers = {
    Authorization:
      "Bearer " +
      (await page.evaluate(() => sessionStorage.getItem("greenscape-token"))),
  };
  const response = await page.request.post("/api/products", {
    headers,
    data: {
      name: "Produto para consumo E2E",
      category: "Plantas",
      price_cents: 5000,
      cost_cents: 2500,
      stock: 4,
    },
  });
  expect(response.status()).toBe(201);
  const product = await response.json();
  const projects = await (
    await page.request.get("/api/projects", { headers })
  ).json();
  const project = projects.find(
    (p: { status: string }) => p.status === "Execução",
  );
  await page.reload();
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name: "Projetos", exact: true })
    .click();
  await page.locator(".project-card").filter({ hasText: project.name }).click();
  await page
    .locator(".project-tabs")
    .getByRole("button", { name: "Consumo", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Registrar consumo", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByRole("combobox", { name: "Produto", exact: true })
    .selectOption(String(product.id));
  await dialog
    .getByLabel("Quantidade (entrada positiva / saída negativa)")
    .fill("-2");
  await dialog
    .getByLabel("Motivo", { exact: true })
    .fill("Plantio realizado na obra");
  await expect(dialog.getByLabel("Custo unitário do consumo (R$)")).toHaveValue(
    "25",
  );
  await dialog.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  const usage = page.locator(".project-usage-panel");
  await expect(usage.locator("tbody tr")).toContainText([
    "Produto para consumo E2E",
  ]);
  await expect(usage.locator(".usage-summary")).toContainText("R$ 50,00");
  const products = await (
    await page.request.get("/api/admin/products", { headers })
  ).json();
  expect(products.find((p: { id: number }) => p.id === product.id).stock).toBe(
    2,
  );
  await page.screenshot({
    path: "../docs/screenshots/projeto-consumo-100.png",
  });
});

test("Sessão expirada limpa o painel e pede novo login", async ({ page }) => {
  await login(page);
  await page.route("**/api/analytics?**", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Sessão inválida ou expirada." }),
    }),
  );
  await page.getByLabel("Início do período").fill("2026-09-01");
  await expect(
    page.getByRole("heading", { name: "Bem-vindo ao Ateliê Verde" }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Sua sessão expirou");
  expect(
    await page.evaluate(() => sessionStorage.getItem("greenscape-token")),
  ).toBeNull();
  await expect(page.locator(".admin-sidebar")).not.toBeVisible();
});

test("Paginação acompanha páginas avançadas e filtros", async ({ page }) => {
  await login(page);
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name: "Estoque", exact: true })
    .click();
  const panel = page.locator(".inventory-panel");
  await panel.getByRole("button", { name: "Última página" }).click();
  await expect(
    panel.locator(".pagination button[aria-current='page']"),
  ).toHaveText("13");
  await expect(panel.locator("tbody tr").first()).toBeVisible();
  await panel.getByLabel("Buscar produto, SKU ou espécie…").fill("cacto-dedo");
  await expect(
    panel.locator(".pagination button[aria-current='page']"),
  ).toHaveText("1");
  await expect(panel.locator("tbody tr")).toHaveCount(1);
});

test("Categorias mostram quantidades, percentuais e abrem o filtro do estoque", async ({
  page,
}) => {
  await login(page);
  const chart = page.getByLabel("Vendas por categoria em unidades");
  await expect(chart.locator("li")).toHaveCount(6);
  await chart.getByRole("button", { name: /^Plantas:/ }).click();
  await expect(
    page.getByRole("heading", { name: "Estoque", level: 1, exact: true }),
  ).toBeVisible();
  await page
    .locator(".inventory-panel")
    .getByRole("button", { name: /Filtros/ })
    .click();
  await expect(page.getByLabel("Categoria", { exact: true })).toHaveValue(
    "Plantas",
  );
});

test("Filtro de categorias usa ano e intervalo personalizado coerentes", async ({
  page,
}) => {
  await login(page);
  const picker = page.getByLabel("Período do gráfico");
  await picker.selectOption("year");
  await expect(picker).toHaveValue("year");
  const chart = page.getByLabel("Vendas por categoria em unidades");
  for (const category of [
    "Plantas",
    "Vasos",
    "Substratos",
    "Fertilizantes",
    "Ferramentas",
    "Acessórios",
  ]) {
    await expect(
      chart.getByRole("button", { name: new RegExp(`^${category}: [1-9]`) }),
    ).toBeVisible();
  }
  await picker.selectOption("custom");
  await page.getByLabel("Início do filtro do gráfico").fill("2020-01-01");
  await page.getByLabel("Fim do filtro do gráfico").fill("2020-12-31");
  await page.getByRole("button", { name: "Aplicar", exact: true }).click();
  await expect(chart).toContainText("Nenhuma venda registrada");
  await expect(picker).toHaveValue("custom");
  await expect(
    page.getByRole("button", { name: "Editar período personalizado" }),
  ).toBeVisible();
});

test("Relatórios conferem a coerência da empresa demonstrativa", async ({
  page,
}) => {
  await login(page);
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name: "Relatórios", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Consistência dos dados", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Registros consistentes");
  await expect(dialog).toContainText("Produtos");
  await dialog.getByRole("button", { name: "Conferir novamente" }).click();
  await expect(dialog).toContainText("Registros consistentes");
});
