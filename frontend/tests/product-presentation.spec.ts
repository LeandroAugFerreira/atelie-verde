import { test, expect, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const output = resolve("..", ".local", "qa-catalog-individual");
mkdirSync(output, { recursive: true });

async function customer(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(page.locator(".category-grid")).toBeVisible();
}

async function product(page: Page, name: string, category = "Plantas") {
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Produtos", exact: true })
    .click();
  await page
    .locator(".catalog-sidebar")
    .getByRole("button", { name: new RegExp(category) })
    .click();
  await page.locator(".app-header input").fill(name);
  await page
    .locator(".catalog-card .product-name")
    .filter({ hasText: new RegExp(`^${name}$`) })
    .click();
  await expect(page.locator(".product-page h1")).toHaveText(name);
}

test("Regador e ferramentas exibem seu próprio item completo", async ({
  page,
}) => {
  await customer(page);
  for (const [name, category, file] of [
    ["Regador verde 2 L", "Acessórios", "ac-016-v1.png"],
    ["Tesoura de poda", "Ferramentas", "fe-015-v1.png"],
    ["Cultivador manual de três pontas", "Ferramentas", "av-demo-112-v1.png"],
  ]) {
    await product(page, name, category);
    const photo = page.locator(".product-large-photo > .photo");
    await expect(photo).toHaveAttribute(
      "src",
      `/catalog-media/products/${file}`,
    );
    await photo.evaluate((img) => (img as HTMLImageElement).decode());
    expect(await photo.evaluate((el) => getComputedStyle(el).objectFit)).toBe(
      "contain",
    );
    await expect(page.locator(".product-image-note")).toContainText(
      "Imagem ilustrativa",
    );
    const thumbnails = page.locator(".product-thumbnails > button > img");
    await expect(thumbnails).toHaveCount(1);
    expect(
      await thumbnails.evaluate((el) => {
        const style = getComputedStyle(el),
          parent = el.parentElement!;
        return (
          style.objectFit === "contain" &&
          el.clientWidth <= parent.clientWidth &&
          el.clientHeight <= parent.clientHeight
        );
      }),
    ).toBe(true);
    if (file.startsWith("ac-016"))
      await page.screenshot({ path: resolve(output, "regador.png") });
    await page.locator(".app-header input").fill("");
  }
});

test("Produto sem foto cadastrada não recebe uma foto genérica da categoria", async ({
  page,
}) => {
  await page.route("**/api/products", async (route) => {
    const response = await route.fetch(),
      products = await response.json();
    products.find(
      (p: { name: string }) => p.name === "Regador verde 2 L",
    ).image_url = "";
    await route.fulfill({ json: products });
  });
  await customer(page);
  await product(page, "Regador verde 2 L", "Acessórios");
  await expect(
    page.locator(".product-large-photo .item-photo-placeholder"),
  ).toContainText("Imagem ainda não cadastrada");
  await expect(page.locator(".product-large-photo img.sprite")).toHaveCount(0);
});

for (const viewport of [
  { width: 1366, height: 768 },
  { width: 1280, height: 720 },
  { width: 1920, height: 1080 },
]) {
  test(`Produto e descrição cabem no desktop ${viewport.width}x${viewport.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await customer(page);
    await product(page, "Hibisco");
    await page
      .locator(".product-large-photo > img")
      .evaluate((img) => (img as HTMLImageElement).decode());
    for (const tab of ["Informações da planta", "Descrição", "Cuidados"]) {
      await page.getByRole("button", { name: tab, exact: true }).click();
      const overflow = await page
        .locator(
          ".product-top, .plant-information > .panel, .product-detail-content > .panel",
        )
        .evaluateAll((els) =>
          els
            .filter((el) => el.scrollHeight > el.clientHeight + 2)
            .map((el) => ({
              class: el.className,
              client: el.clientHeight,
              scroll: el.scrollHeight,
            })),
        );
      expect(overflow, tab).toEqual([]);
      expect(
        await page
          .locator(".product-page")
          .evaluate((el) => el.scrollHeight <= el.clientHeight + 2),
      ).toBe(true);
      if (tab === "Informações da planta")
        await expect(page.locator(".information-table tr")).toHaveCount(8);
    }
    await page
      .getByRole("button", { name: "Informações da planta", exact: true })
      .click();
    await page.screenshot({
      path: resolve(output, `plant-${viewport.width}.png`),
    });
    await page
      .getByRole("button", { name: "Créditos das fotografias", exact: true })
      .click();
    const credits = page.getByRole("dialog", {
      name: "Créditos das fotografias",
      exact: true,
    });
    await expect(credits).toBeVisible();
    await expect(credits.locator(".photo-credits")).toHaveAttribute("open", "");
    await credits.getByRole("button", { name: "Fechar", exact: true }).click();
  });
}

test("Espécies com textos e portes diferentes mantêm todos os campos visíveis", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await customer(page);
  for (const name of [
    "Zamioculca",
    "Areca-bambu",
    "Flor-de-maio",
    "Costela-de-adão",
  ]) {
    await product(page, name);
    for (const tab of ["Informações da planta", "Descrição", "Cuidados"]) {
      await page.getByRole("button", { name: tab, exact: true }).click();
      const overflowing = await page
        .locator(
          ".product-top, .plant-information>.panel, .product-detail-content>.panel",
        )
        .evaluateAll((els) =>
          els
            .filter((el) => el.scrollHeight > el.clientHeight + 2)
            .map((el) => el.className),
        );
      expect(overflowing, name + ": " + tab).toEqual([]);
    }
  }
});

test("Fundo anexado, containers claros e mensagem vazia de projetos centralizada", async ({
  page,
}) => {
  await page.route("**/api/projects", (route) => route.fulfill({ json: [] }));
  await customer(page);
  expect(
    await page
      .locator(".client-app")
      .evaluate((el) => getComputedStyle(el).backgroundImage),
  ).toContain("botanical-watercolor-v1.jpeg");
  for (const [name, key] of [
    ["Projetos", "projects"],
    ["Serviços", "services"],
    ["Aprender", "learn"],
  ]) {
    await page
      .locator(".client-nav")
      .getByRole("button", { name, exact: true })
      .click();
    await expect(page.locator(`.page-${key}`)).toBeVisible();
    expect(
      await page
        .locator(`.page-${key}`)
        .evaluate((el) => getComputedStyle(el).backgroundColor),
    ).toBe("rgba(255, 253, 248, 0.82)");
    if (key === "projects") {
      const empty = page.locator(".project-grid > .empty");
      await expect(empty).toContainText(
        "Nenhum projeto encontrado. Ajuste ou limpe os filtros.",
      );
      await expect(page.locator(".page-projects .empty")).toHaveCount(1);
      const field = await page.locator(".project-grid").boundingBox(),
        message = await empty.boundingBox();
      expect(
        Math.abs(field!.x + field!.width / 2 - message!.x - message!.width / 2),
      ).toBeLessThan(2);
      await page.screenshot({ path: resolve(output, "projects-empty.png") });
    }
    if (key === "learn")
      await page.screenshot({ path: resolve(output, "learn.png") });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page
      .locator(".client-app")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
});
