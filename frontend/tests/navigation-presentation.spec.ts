import { test, expect, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
const output = resolve("..", ".local", "qa-navigation-photos");
mkdirSync(output, { recursive: true });
const trail = (page: Page) =>
  page.getByRole("navigation", { name: "Caminho de navegação", exact: true });

async function customer(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(page.locator(".category-grid")).toBeVisible();
}

test("Caminho liga produto, categoria, catálogo e loja", async ({ page }) => {
  await customer(page);
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Produtos", exact: true })
    .click();
  await expect(page.locator(".catalog-heading h1")).toHaveText("Produtos");
  await page
    .locator(".catalog-sidebar")
    .getByRole("button", { name: /Plantas/ })
    .click();
  await expect(trail(page).locator('[aria-current="page"]')).toHaveText(
    "Plantas",
  );
  await page
    .locator(".catalog-card .product-name")
    .filter({ hasText: /^Hibisco$/ })
    .click();
  await expect(trail(page)).toContainText("LojaProdutosPlantasHibisco");
  await trail(page)
    .getByRole("button", { name: "Plantas", exact: true })
    .click();
  await expect(page.locator(".catalog-heading h1")).toHaveText("Plantas");
  await trail(page)
    .getByRole("button", { name: "Produtos", exact: true })
    .click();
  await expect(page.locator(".catalog-heading h1")).toHaveText("Produtos");
  await trail(page).getByRole("button", { name: "Loja", exact: true }).click();
  await expect(page.locator(".category-grid")).toBeVisible();
});

test("Projetos simulados e caminhos das demais áreas funcionam", async ({
  page,
}) => {
  await customer(page);
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Projetos", exact: true })
    .click();
  const demos = page
    .locator(".project-card")
    .filter({ hasText: "demonstração" });
  await expect(demos).toHaveCount(6);
  await demos.filter({ hasText: "Varanda de folhagens" }).click();
  await expect(trail(page)).toContainText("Varanda de folhagens");
  await page.getByRole("button", { name: "Planta 2D", exact: true }).click();
  await expect(
    page.locator(".project-plan-panel svg.landscape-svg"),
  ).toBeVisible();
  await trail(page)
    .getByRole("button", { name: "Projetos", exact: true })
    .click();
  await expect(demos).toHaveCount(6);
  await page.screenshot({ path: resolve(output, "projects.png") });
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Serviços", exact: true })
    .click();
  await page
    .locator(".client-service-card")
    .first()
    .getByRole("button", { name: /Conhecer serviço/ })
    .click();
  await trail(page)
    .getByRole("button", { name: "Serviços", exact: true })
    .click();
  await expect(page.locator(".client-service-grid")).toBeVisible();
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Aprender", exact: true })
    .click();
  await page.locator(".guide-card").nth(1).click();
  await expect(
    trail(page).getByRole("button", { name: "Aprender", exact: true }),
  ).toBeVisible();
  await trail(page)
    .getByRole("button", { name: "Aprender", exact: true })
    .click();
  await page.getByRole("button", { name: /Biblioteca de espécies/ }).click();
  await trail(page)
    .getByRole("button", { name: "Aprender", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Aprender a cultivar", exact: true }),
  ).toBeVisible();
});

test("Todas as áreas administrativas têm retorno pelo caminho", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  for (const name of [
    "Estoque",
    "Fornecedores",
    "Clientes",
    "Serviços",
    "Orçamentos",
    "Projetos",
    "Financeiro",
    "Relatórios",
    "Configurações",
  ]) {
    await page
      .locator(".admin-sidebar")
      .getByRole("button", { name, exact: true })
      .click();
    await expect(trail(page).locator('[aria-current="page"]')).toHaveText(name);
    await trail(page)
      .getByRole("button", { name: "Dashboard", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Dashboard", exact: true }),
    ).toBeVisible();
  }
});

for (const viewport of [
  { width: 1280, height: 720 },
  { width: 1366, height: 768 },
  { width: 1920, height: 1080 },
]) {
  test(`Galeria grande e fotos uniformes em ${viewport.width}x${viewport.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await customer(page);
    await page
      .locator(".client-nav")
      .getByRole("button", { name: "Produtos", exact: true })
      .click();
    await page
      .locator(".catalog-sidebar")
      .getByRole("button", { name: /Plantas/ })
      .click();
    await expect
      .poll(() => page.locator(".catalog-photo").count())
      .toBeGreaterThan(0);
    const frames = await page.locator(".catalog-photo").evaluateAll((els) =>
      els.map((el) => {
        const b = el.getBoundingClientRect();
        return [b.width, b.height];
      }),
    );
    expect(frames.length).toBeGreaterThan(0);
    expect(frames.every(([w, h]) => Math.abs(w - h) < 2)).toBe(true);
    await page
      .locator(".catalog-card .product-name")
      .filter({ hasText: /^Hibisco$/ })
      .click();
    const hero = page.locator(".product-large-photo");
    const rect = await hero.boundingBox();
    expect(rect!.height).toBeGreaterThan(viewport.height * 0.5);
    const image = hero.locator("img");
    await image.evaluate((img) => (img as HTMLImageElement).decode());
    expect(await image.evaluate((el) => getComputedStyle(el).objectFit)).toBe(
      "contain",
    );
    await expect(page.locator(".information-table tr")).toHaveCount(8);
    expect(
      await page
        .locator(".information-table")
        .evaluate((el) => el.getBoundingClientRect().bottom <= innerHeight),
    ).toBe(true);
    await page.screenshot({
      path: resolve(output, `large-photo-${viewport.width}.png`),
    });
  });
}
