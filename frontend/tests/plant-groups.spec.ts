import { test, expect } from "@playwright/test";

test("Tipos de plantas completos e coerentes no estoque e loja", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name: "Estoque", exact: true })
    .click();
  const panel = page.locator(".inventory-panel");
  await panel.getByRole("button", { name: "Filtros", exact: true }).click();
  const filter = panel.getByLabel("Tipo de planta");
  await expect(
    filter.locator("option").filter({ hasText: /^Cactos$/ }),
  ).toHaveCount(1);
  const options = await filter.locator("option").allTextContents();
  for (const group of [
    "Cactos",
    "Frutíferas",
    "Flores",
    "Folhagens",
    "Suculentas",
    "Aromáticas e temperos",
    "Palmeiras",
    "Samambaias",
    "Trepadeiras",
    "Cercas vivas",
    "Ornamentais",
  ])
    expect(options).toContain(group);
  await filter.selectOption("Suculentas");
  await expect(panel.locator(".filter-count")).toHaveText("3 resultados");
  await expect(panel.locator("tbody")).toContainText("Echeveria");
  await filter.selectOption("Palmeiras");
  await expect(panel.locator(".filter-count")).toHaveText("2 resultados");
  await filter.selectOption("Samambaias");
  await expect(panel.locator(".filter-count")).toHaveText("1 resultado");
  await expect(panel.locator("tbody")).toContainText("Samambaia-boston");
  await page.getByRole("button", { name: "Abrir menu da conta" }).click();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Produtos", exact: true })
    .click();
  await page
    .getByLabel("Tipos de plantas")
    .selectOption("Aromáticas e temperos");
  await expect(page.locator(".catalog-card")).toHaveCount(4);
  await expect(page.locator(".catalog-grid")).toContainText("Lavanda");
  await expect(page.locator(".catalog-grid")).toContainText("Manjericão");
  await page.getByLabel("Tipos de plantas").selectOption("Flores");
  await expect(page.locator(".catalog-grid")).toContainText("Hibisco");
});
