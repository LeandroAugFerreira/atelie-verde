import { test, expect, type Page } from "@playwright/test";

async function tab(page: Page, name: string) {
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name, exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name, level: 1, exact: true }),
  ).toBeVisible();
}
test("Fornecedor, preço com impostos, compra e cliente comercial persistem", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  await expect(page.locator(".admin-sidebar")).toBeVisible();
  const names = await page
    .locator(".admin-sidebar nav > button")
    .allTextContents();
  expect(names).not.toContain("Produtos");
  expect(names.indexOf("Fornecedores") + 1).toBe(names.indexOf("Clientes"));
  await tab(page, "Fornecedores");
  await page
    .getByRole("button", { name: "Novo fornecedor", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Razão social / nome do fornecedor")
    .fill("Viveiro E2E Comercial");
  await dialog.getByLabel("CNPJ", { exact: true }).fill("11.222.333/0001-81");
  await dialog.getByLabel("Cidade", { exact: true }).fill("Campinas");
  await dialog.getByLabel("UF", { exact: true }).fill("SP");
  await dialog.getByLabel("Prazo de entrega (dias)").fill("4");
  await dialog.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await page.locator(".app-header input").fill("Viveiro E2E");
  await expect(page.locator(".supplier-list tbody tr")).toHaveCount(1);
  await expect(page.locator(".supplier-profile-heading")).toContainText("FOR-");
  await page.reload();
  await tab(page, "Fornecedores");
  await page.locator(".app-header input").fill("Viveiro E2E");
  await expect(page.locator(".supplier-list tbody tr")).toHaveCount(1);
  await page.locator(".supplier-list tbody tr").click();
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.screenshot({ path: "../docs/screenshots/fornecedores-1366.png" });
  await tab(page, "Estoque");
  await page.getByRole("button", { name: "Novo produto", exact: true }).click();
  await dialog
    .getByLabel("Nome do produto", { exact: true })
    .fill("Muda E2E tributada");
  await dialog
    .getByRole("combobox", { name: "Fornecedor", exact: true })
    .selectOption({ label: "FOR-007 · Viveiro E2E Comercial" });
  await dialog.getByLabel("Marca / produtor").fill("Ateliê");
  await dialog.getByLabel("Variação / embalagem").fill("Muda de 20 cm");
  await dialog.getByLabel("Formação do preço").selectOption("Custo + margem");
  await dialog.getByLabel("Custo unitário (R$)", { exact: true }).fill("100");
  await dialog.getByLabel("Margem sobre o custo (%)").fill("50");
  await dialog
    .getByLabel("Regime de precificação")
    .selectOption("Simples Nacional");
  await dialog.getByLabel("Simples — alíquota efetiva (%)").fill("6");
  await expect(dialog.getByLabel("Composição do preço")).toContainText(
    "R$ 159,57",
  );
  await expect(dialog.getByLabel("Preço (R$)", { exact: true })).toHaveValue(
    "159.57",
  );
  await dialog.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await page.locator(".app-header input").fill("Muda E2E tributada");
  const row = page
    .locator(".inventory-panel tbody tr")
    .filter({ hasText: "Muda E2E tributada" });
  await expect(row).toContainText("PRD-");
  await expect(row).toContainText("R$ 159,57");
  await row.getByRole("button", { name: "Editar Muda E2E tributada" }).click();
  await expect(
    dialog.getByLabel("Custo unitário (R$)", { exact: true }),
  ).toHaveValue("100");
  await expect(dialog.getByLabel("Simples — alíquota efetiva (%)")).toHaveValue(
    "6",
  );
  await dialog.getByRole("button", { name: "Fechar" }).click();
  await row
    .getByRole("button", { name: "Movimentar Muda E2E tributada" })
    .click();
  await dialog
    .getByLabel("Quantidade (entrada positiva / saída negativa)")
    .fill("3");
  await dialog
    .getByLabel("Motivo", { exact: true })
    .fill("Compra E2E comercial");
  await dialog.getByLabel("Documento / referência").fill("NF-E2E-01");
  await dialog.getByLabel("Custo unitário da entrada (R$)").fill("100");
  await dialog.getByLabel("Gerar conta a pagar desta entrada").check();
  await dialog.getByLabel("Vencimento", { exact: true }).fill("2026-11-30");
  await dialog.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  const headers = {
    Authorization:
      "Bearer " +
      (await page.evaluate(() => sessionStorage.getItem("greenscape-token"))),
  };
  const products = await (
    await page.request.get("/api/admin/products", { headers })
  ).json();
  const product = products.find(
    (p: { name: string }) => p.name === "Muda E2E tributada",
  );
  expect(product.stock).toBe(3);
  expect(product.price_cents).toBe(15957);
  const moves = await (
    await page.request.get(`/api/stock-history?product_id=${product.id}`, {
      headers,
    })
  ).json();
  expect(moves.total).toBe(1);
  expect(moves.items[0].balance_before).toBe(0);
  expect(moves.items[0].balance_after).toBe(3);
  const ledger = await (
    await page.request.get("/api/ledger", { headers })
  ).json();
  const payable = ledger.find(
    (l: { stock_move_id: number }) => l.stock_move_id === moves.items[0].id,
  );
  expect(payable.amount_cents).toBe(30000);
  expect(payable.supplier_id).toBe(product.supplier_id);
  await tab(page, "Clientes");
  await page.getByRole("button", { name: "Novo cliente", exact: true }).click();
  await dialog
    .getByLabel("Nome completo / razão social")
    .fill("Cliente Comercial E2E");
  await dialog
    .getByLabel("E-mail", { exact: true })
    .fill("cliente-comercial-e2e@example.com");
  await dialog.getByLabel("CPF / CNPJ").fill("529.982.247-25");
  await dialog.getByLabel("Cidade", { exact: true }).fill("Campinas");
  await dialog.getByLabel("UF", { exact: true }).fill("SP");
  await dialog.getByRole("button", { name: "Salvar", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await page.locator(".app-header input").fill("Cliente Comercial E2E");
  await expect(page.locator(".profile-header")).toContainText(
    "Cliente Comercial E2E",
  );
  await page.getByText("Dados comerciais", { exact: true }).click();
  await expect(page.locator(".customer-commercial")).toContainText(
    "Cadastro comercial sem acesso",
  );
  await tab(page, "Relatórios");
  await page.getByRole("button", { name: "Histórico de alterações" }).click();
  await dialog.getByLabel("Cadastro / operação").selectOption("Fornecedor");
  await expect(dialog).toContainText("Criar");
  expect(errors).toEqual([]);
});
