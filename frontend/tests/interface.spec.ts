import { test, expect } from "@playwright/test";

test("Operação integrada: produto, estoque, compra e cancelamento", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  await expect(page.locator(".admin-sidebar")).toBeVisible();
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name: "Estoque", exact: true })
    .click();
  await page.getByRole("button", { name: "Novo produto", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Nome do produto", { exact: true })
    .fill("Planta teste integrada");
  await dialog.getByLabel("SKU / código do produto").fill("TESTE-E2E-001");
  await dialog.getByLabel("Preço (R$)", { exact: true }).fill("19.90");
  await dialog.getByLabel("Estoque inicial").fill("3");
  await dialog.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await page.locator(".app-header input").fill("TESTE-E2E-001");
  const row = page.getByRole("row").filter({ hasText: "TESTE-E2E-001" });
  await expect(row).toBeVisible();
  await row
    .getByRole("button", { name: "Movimentar Planta teste integrada" })
    .click();
  await dialog
    .getByLabel("Quantidade (entrada positiva / saída negativa)")
    .fill("-4");
  await dialog.getByLabel("Motivo", { exact: true }).fill("Verificar bloqueio");
  await dialog.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(dialog).toContainText("Saldo insuficiente");
  await dialog
    .getByLabel("Quantidade (entrada positiva / saída negativa)")
    .fill("2");
  await dialog.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await page.getByRole("button", { name: "Abrir menu da conta" }).click();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(page.locator(".client-nav")).toBeVisible();
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Produtos", exact: true })
    .click();
  await page.locator(".app-header input").fill("Planta teste integrada");
  await page.getByRole("button", { name: "Adicionar", exact: true }).click();
  await page
    .getByRole("button", { name: "Carrinho com 1 itens", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Confirmar pedido", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Meu histórico", exact: true }),
  ).toBeVisible();
  const order = page
    .getByRole("row")
    .filter({ hasText: "Planta teste integrada" });
  await expect(order).toContainText("Confirmado");
  await order.getByRole("button", { name: "Cancelar pedido" }).click();
  await dialog.getByRole("button", { name: "Confirmar cancelamento" }).click();
  await expect(order).toContainText("Cancelado");
});
test("Administrador: referências a 100% e navegação funcional", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".kpi").first()).toContainText("Faturamento");
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: "../docs/screenshots/dashboard-100.png",
    fullPage: true,
  });
  for (const [label, file] of [
    ["Estoque", "estoque"],
    ["Clientes", "clientes"],
    ["Serviços", "servicos"],
    ["Orçamentos", "orcamentos"],
    ["Financeiro", "financeiro"],
  ]) {
    await page
      .locator(".admin-sidebar")
      .getByRole("button", { name: label, exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: label, exact: true }),
    ).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: `../docs/screenshots/${file}-100.png`,
      fullPage: true,
    });
  }
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name: "Projetos", exact: true })
    .click();
  await page
    .getByRole("button")
    .filter({
      has: page.getByRole("heading", {
        name: "Projeto Residencial – Jardim Frontal",
        exact: true,
      }),
    })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Projeto Residencial – Jardim Frontal",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Espécies selecionadas", exact: true }),
  ).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: "../docs/screenshots/projeto-100.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
test("Cliente: loja, filtros, produto, favoritos e carrinho", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(page.locator(".client-nav")).toBeVisible();
  await expect(page.locator(".shop-hero")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: "../docs/screenshots/loja-100.png",
    fullPage: true,
  });
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Produtos", exact: true })
    .click();
  await expect(page.locator(".catalog-card")).not.toHaveCount(0);
  await expect(page.locator(".catalog-card img")).toHaveCount(8);
  await expect.poll(() => page.locator(".catalog-card img").evaluateAll(images => images.every(img => (img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth > 0))).toBe(true);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: "../docs/screenshots/plantas-100.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Hibisco", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Hibisco", exact: true }),
  ).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: "../docs/screenshots/produto-100.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Adicionar ao carrinho", exact: true })
    .click();
  await page.getByRole("button", { name: /Carrinho com 1 itens/ }).click();
  await expect(page.getByRole("dialog")).toContainText("Hibisco");
  await page.getByRole("button", { name: "Continuar comprando" }).click();
  await page.getByRole("button", { name: "Cuidados", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Como cuidar" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("Responsividade no celular com zoom padrão", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(page.locator(".client-nav")).toBeVisible();
  await expect(page.locator(".shop-hero")).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: "../docs/screenshots/loja-mobile.png",
    fullPage: true,
  });
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Produtos", exact: true })
    .click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: "../docs/screenshots/plantas-mobile.png",
    fullPage: true,
  });
});
