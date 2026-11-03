import { test, expect, type Page } from "@playwright/test";
import { resolve } from "node:path";

async function noDocumentScroll(page: Page) {
  expect(
    await page.evaluate(() => {
      const root = document.scrollingElement!;
      return (
        root.scrollHeight <= window.innerHeight &&
        root.scrollWidth <= window.innerWidth
      );
    }),
  ).toBe(true);
}

test("Perfil próprio: upload, persistência e remoção", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(page.locator(".app-header .avatar-initials")).toBeVisible();
  await page.getByRole("button", { name: "Abrir menu da conta" }).click();
  await page
    .getByRole("button", { name: "Editar Perfil", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Enviar foto do perfil")
    .setInputFiles(resolve("public/plants/plinia-cauliflora-1.jpg"));
  await expect(dialog.getByRole("status")).toHaveText(
    "Foto do perfil atualizada.",
  );
  await dialog.getByLabel("Cidade / UF").fill("Campinas - SP");
  await dialog.getByRole("button", { name: "Salvar perfil" }).click();
  await expect(dialog).not.toBeVisible();
  await page.reload();
  await expect(page.locator(".app-header .avatar-photo img")).toBeVisible();
  await page.getByRole("button", { name: "Abrir menu da conta" }).click();
  await page
    .getByRole("button", { name: "Editar Perfil", exact: true })
    .click();
  await expect(dialog.getByLabel("Cidade / UF")).toHaveValue("Campinas - SP");
  await dialog.getByRole("button", { name: "Remover foto" }).click();
  await expect(dialog.getByRole("status")).toHaveText("Foto removida.");
  await dialog.getByRole("button", { name: "Salvar perfil" }).click();
  await noDocumentScroll(page);
});

test("Aprendizado: cactos, frutíferas e progresso persistente", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Aprender", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Aprender a cultivar" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Cactos", exact: true }).click();
  await expect(page.locator(".guide-reader")).toContainText("flor-de-maio");
  await page.getByRole("button", { name: "Marcar como concluído" }).click();
  await expect(page.locator(".learning-progress")).toContainText("1 de 10");
  await page.reload();
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Aprender", exact: true })
    .click();
  await page.getByRole("button", { name: "Concluídos", exact: true }).click();
  await expect(page.locator(".guide-list .guide-card")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Concluído · marcar como não lido" })
    .click();
  await page.getByRole("button", { name: "Frutíferas", exact: true }).click();
  await expect(page.locator(".guide-reader")).toContainText("jabuticabeira");
  await page.screenshot({ path: "../docs/screenshots/aprender-100.png" });
  await noDocumentScroll(page);
});

test("Cactos e frutíferas disponíveis para compra com fotos reais", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Produtos", exact: true })
    .click();
  for (const name of ["Cacto-dedo-de-dama", "Jabuticabeira"]) {
    await page.locator(".app-header input").fill(name);
    const card = page.locator(".catalog-card").filter({ hasText: name });
    await expect(card).toHaveCount(1);
    const img = card.locator("img");
    await expect
      .poll(() =>
        img.evaluate((e: HTMLImageElement) => e.complete && e.naturalWidth > 0),
      )
      .toBe(true);
    await card.getByRole("button", { name: "Adicionar", exact: true }).click();
    await noDocumentScroll(page);
  }
  await page
    .getByRole("button", { name: "Carrinho com 2 itens", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("Jabuticabeira");
  await expect(page.getByRole("dialog")).toContainText("Cacto-dedo-de-dama");
});

test("Todas as abas cabem na janela com conteúdo acessível nos cards", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  for (const size of [
    { width: 1672, height: 941 },
    { width: 1366, height: 768 },
  ]) {
    await page.setViewportSize(size);
    for (const label of [
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
      await page
        .locator(".admin-sidebar")
        .getByRole("button", { name: label, exact: true })
        .click();
      await noDocumentScroll(page);
      expect(
        await page.locator(".page-canvas").evaluate((el) => {
          const r = el.getBoundingClientRect();
          return r.bottom <= innerHeight + 1 && r.top >= 0;
        }),
      ).toBe(true);
    }
  }
  await page.getByRole("button", { name: "Abrir menu da conta" }).click();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  for (const size of [
    { width: 1366, height: 768 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(size);
    for (const label of [
      "Loja",
      "Produtos",
      "Serviços",
      "Projetos",
      "Aprender",
    ]) {
      const tab = page
        .locator(".client-nav")
        .getByRole("button", { name: label, exact: true });
      await tab.click();
      await noDocumentScroll(page);
    }
    await page
      .locator(".client-nav")
      .getByRole("button", { name: "Produtos", exact: true })
      .click();
    const card = page.locator(".catalog-card").first();
    await card
      .getByRole("button", { name: "Adicionar", exact: true })
      .scrollIntoViewIfNeeded();
    const button = await card
      .getByRole("button", { name: "Adicionar", exact: true })
      .boundingBox();
    expect(button && button.y + button.height <= size.height).toBeTruthy();
    expect(
      await card.evaluate((el) => el.scrollHeight <= el.clientHeight + 1),
    ).toBe(true);
  }
});
