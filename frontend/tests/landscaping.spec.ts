import { test, expect, type Page } from "@playwright/test";

async function client(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(page.locator(".client-nav")).toBeVisible();
}
async function services(page: Page) {
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Serviços", exact: true })
    .click();
  await expect(page.locator(".client-service-card")).toHaveCount(8);
}

test("Serviços explicam escopo e orçamento já seleciona o atendimento", async ({
  page,
}) => {
  await client(page);
  await services(page);
  const card = page
    .locator(".client-service-card")
    .filter({ has: page.getByRole("heading", { name: "Poda", exact: true }) });
  const cards = await page
    .locator(".client-service-card")
    .evaluateAll((items) =>
      items.every((card) => {
        const bounds = card.getBoundingClientRect();
        return [...card.querySelectorAll("h2,p,strong,button")].every((el) => {
          const r = el.getBoundingClientRect();
          return r.top >= bounds.top && r.bottom <= bounds.bottom + 1;
        });
      }),
    );
  expect(cards).toBe(true);
  await card.getByRole("button", { name: "Conhecer serviço" }).click();
  await expect(
    page.getByRole("heading", { name: "O que este serviço realiza" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Documentos e registros" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Solicitar orçamento", exact: true })
    .first()
    .click();
  await expect(
    page
      .getByRole("dialog")
      .getByRole("combobox", { name: "Serviço", exact: true })
      .locator("option:checked"),
  ).toHaveText("Poda");
});

test("Paisagista virtual: importação, prévia, anexos e projeto aprovado", async ({
  page,
}) => {
  await client(page);
  await services(page);
  await page
    .locator(".client-service-card")
    .filter({
      has: page.getByRole("heading", {
        name: "Paisagista virtual",
        exact: true,
      }),
    })
    .getByRole("button", { name: "Conhecer serviço" })
    .click();
  await page
    .getByRole("button", { name: "Preparar projeto e solicitar orçamento" })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Largura (m)", { exact: true }).fill("12");
  await dialog.getByLabel("Comprimento (m)", { exact: true }).fill("8");
  await dialog
    .getByLabel("Endereço do projeto")
    .fill("Rua do Planejamento, 123");
  await dialog
    .getByLabel("Objetivos e estilo")
    .fill("Jardim de flores com baixa manutenção");
  await dialog.getByLabel("Importar dados e plantas").setInputFiles({
    name: "plantas.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "especie;quantidade;x_m;y_m;diametro_m;aplicacao\nHibisco;6;2;3;1;Canteiro frontal\nLavanda;8;6;3;1;Bordadura\n",
    ),
  });
  await expect(dialog.locator(".landscape-svg circle")).toHaveCount(2);
  await expect(dialog.locator(".landscape-legend")).toContainText("Hibisco");
  await dialog.getByRole("button", { name: "Arquivos", exact: true }).click();
  await dialog.getByLabel("Fotos e documentos do planejamento").setInputFiles({
    name: "medidas.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF"),
  });
  await expect(dialog).toContainText("medidas.pdf");
  await dialog
    .getByRole("button", { name: "Solicitar orçamento", exact: true })
    .click();
  await expect(dialog).not.toBeVisible();
  const headers = {
    Authorization:
      "Bearer " +
      (await page.evaluate(() => sessionStorage.getItem("greenscape-token"))),
  };
  const quotes = await (
    await page.request.get("/api/quotes", { headers })
  ).json();
  const quote = quotes.find(
    (q: { address: string }) => q.address === "Rua do Planejamento, 123",
  );
  expect(quote.area).toBe(96);
  expect(quote.brief.plantings.length).toBe(2);
  const docs = await (
    await page.request.get(`/api/quotes/${quote.id}/documents`, { headers })
  ).json();
  expect(docs.length).toBe(1);
  const auth = await (
    await page.request.post("/api/auth/login", {
      data: { email: "admin@atelieverde.local", password: "AtelieVerde@2026" },
    })
  ).json();
  const adminHeaders = { Authorization: "Bearer " + auth.access_token };
  expect(
    (
      await page.request.patch(`/api/quotes/${quote.id}/price`, {
        headers: adminHeaders,
        data: { amount_cents: 180000 },
      })
    ).ok(),
  ).toBe(true);
  const project = await (
    await page.request.post(`/api/quotes/${quote.id}/approve`, { headers })
  ).json();
  expect(project.delivery_mode).toBe("Virtual");
  await page.reload();
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Projetos", exact: true })
    .click();
  await page.locator(".project-card").filter({ hasText: project.name }).click();
  await page
    .locator(".project-tabs")
    .getByRole("button", { name: "Planta 2D", exact: true })
    .click();
  await expect(page.locator(".landscape-svg circle")).toHaveCount(2);
  await expect(page.locator(".landscape-memo")).toContainText("96 m²");
  await page.screenshot({
    path: "../docs/screenshots/cliente-projeto-virtual-100.png",
  });
  await page
    .locator(".project-tabs")
    .getByRole("button", { name: "Documentos", exact: true })
    .click();
  await expect(page.locator(".page-canvas")).toContainText("medidas.pdf");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Baixar", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("medidas.pdf");
});

test("Hero, frase e conteúdo dos cards ficam inteiros a 100%", async ({
  page,
}) => {
  await client(page);
  for (const size of [
    { width: 1852, height: 964 },
    { width: 1366, height: 768 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(size);
    await page
      .locator(".client-nav")
      .getByRole("button", { name: "Loja", exact: true })
      .click();
    expect(
      await page.locator(".shop-hero").evaluate((hero) => {
        const b = hero.getBoundingClientRect();
        return [
          ...hero.querySelectorAll(
            ".hero-copy h1,.hero-copy p,.hero-copy button,.hero-quote",
          ),
        ]
          .filter((el) => el.getClientRects().length)
          .every((el) => {
            const r = el.getBoundingClientRect();
            return (
              r.top >= b.top - 1 &&
              r.bottom <= b.bottom + 1 &&
              r.left >= b.left - 1 &&
              r.right <= b.right + 1
            );
          });
      }),
    ).toBe(true);
    await services(page);
    expect(
      await page.locator(".client-service-card").evaluateAll((items) =>
        items.every((card) => {
          const b = card.getBoundingClientRect();
          return [...card.querySelectorAll("h2,p,button")].every(
            (el) => el.getBoundingClientRect().bottom <= b.bottom + 1,
          );
        }),
      ),
    ).toBe(true);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollHeight <= innerHeight + 1 &&
          document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
  }
});

test("Importação inválida mantém o planejador utilizável", async ({ page }) => {
  await client(page);
  await services(page);
  await page
    .locator(".client-service-card")
    .filter({
      has: page.getByRole("heading", {
        name: "Paisagista virtual",
        exact: true,
      }),
    })
    .getByRole("button", { name: "Conhecer serviço" })
    .click();
  await page
    .getByRole("button", { name: "Preparar projeto e solicitar orçamento" })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Importar dados e plantas")
    .setInputFiles({
      name: "invalido.json",
      mimeType: "application/json",
      buffer: Buffer.from(
        JSON.stringify({ width: 10, length: 8, zones: null, plantings: [] }),
      ),
    });
  await expect(dialog.getByRole("alert")).toContainText(
    "Importe até 100 áreas",
  );
  await expect(
    dialog.getByRole("img", { name: "Planta 2D do projeto paisagístico" }),
  ).toBeVisible();
  await dialog
    .getByLabel("Importar dados e plantas")
    .setInputFiles({
      name: "invalido.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("especie;quantidade\nNão cadastrada;2"),
    });
  await expect(dialog.getByRole("alert")).toContainText(
    "espécie não encontrada",
  );
});
