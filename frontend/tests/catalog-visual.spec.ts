import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const artifacts = resolve("..", ".local", "qa-photos-20261010");
mkdirSync(artifacts, { recursive: true });

test("Fotos nítidas e fundo botânico no portal, serviços e administrador", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(page.locator(".category-grid img.sprite")).toHaveCount(6);
  await expect
    .poll(() =>
      page
        .locator(".category-grid img.sprite")
        .evaluateAll((imgs) =>
          imgs.every((img) => (img as HTMLImageElement).naturalWidth >= 1024),
        ),
    )
    .toBe(true);
  expect(
    await page
      .locator(".client-app")
      .evaluate((el) => getComputedStyle(el).backgroundImage),
  ).toContain("botanical-watercolor-v1.jpeg");
  await page
    .locator(".category-grid img.sprite, .home-services img.sprite")
    .evaluateAll((imgs) =>
      Promise.all(imgs.map((img) => (img as HTMLImageElement).decode())),
    );
  await page.screenshot({ path: resolve(artifacts, "home.png") });
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Serviços", exact: true })
    .click();
  await expect
    .poll(() => page.locator(".client-service-card > img.sprite").count())
    .toBeGreaterThanOrEqual(6);
  await expect
    .poll(() =>
      page
        .locator(".client-service-card > img.sprite")
        .evaluateAll((imgs) =>
          imgs.every((img) => (img as HTMLImageElement).naturalWidth >= 1536),
        ),
    )
    .toBe(true);
  await page
    .locator(".client-service-card > img.sprite")
    .evaluateAll((imgs) =>
      Promise.all(imgs.map((img) => (img as HTMLImageElement).decode())),
    );
  await page.screenshot({ path: resolve(artifacts, "services.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: resolve(artifacts, "services-mobile.png") });
  expect(
    await page
      .locator(".client-app")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  await page.setViewportSize({ width: 1672, height: 941 });
  await page.getByRole("button", { name: "Abrir menu da conta" }).click();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();
  await expect
    .poll(() => page.locator(".admin-content .kpi").count())
    .toBeGreaterThanOrEqual(4);
  expect(
    await page
      .locator(".admin-content")
      .evaluate((el) => getComputedStyle(el).backgroundImage),
  ).toContain("botanical-watercolor-v1.jpeg");
  await page.screenshot({ path: resolve(artifacts, "admin.png") });
});

for (const kind of ["igual", "distinta"] as const) {
  test(`Descrição ${kind} não perde conteúdo e evita repetição`, async ({
    page,
  }) => {
    await page.route("**/api/products", async (route) => {
      const response = await route.fetch();
      const products = await response.json();
      const product = products.find(
        (p: { name: string }) => p.name === "Hibisco",
      );
      if (kind === "igual")
        product.description =
          "  " +
          product.description.toLocaleUpperCase("pt-BR").replaceAll(" ", "  ") +
          "  ";
      else product.description = "Informações específicas deste produto.";
      await route.fulfill({ json: products });
    });
    await page.goto("/");
    await page.getByRole("button", { name: "Cliente", exact: true }).click();
    await page
      .locator(".client-nav")
      .getByRole("button", { name: "Produtos", exact: true })
      .click();
    await page
      .locator(".catalog-card .product-name")
      .filter({ hasText: /^Hibisco$/ })
      .click();
    await page.getByRole("button", { name: "Descrição", exact: true }).click();
    const description = page.locator(".product-detail-content > section.panel");
    await expect(description.locator("p")).toHaveCount(
      kind === "igual" ? 1 : 2,
    );
    if (kind === "distinta")
      await expect(description).toContainText(
        "Informações específicas deste produto.",
      );
    await expect
      .poll(() =>
        page
          .locator(".product-large-photo img")
          .evaluate((img) => (img as HTMLImageElement).naturalWidth),
      )
      .toBeGreaterThanOrEqual(1200);
    if (kind === "igual")
      await page.screenshot({
        path: resolve(artifacts, "plant-description.png"),
      });
  });
}
