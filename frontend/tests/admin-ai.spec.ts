import { test, expect, type Page } from "@playwright/test";

const profile = (connected = true) => ({
  connected,
  kind: connected ? "chatgpt" : "local",
  enabled: connected,
  state: connected ? "ready" : "local",
  email: connected ? "person@example.test" : "",
  model: connected ? "gpt-5.6-sol" : "",
  models: [{ id: "gpt-5.6-sol", name: "ChatGPT" }],
  daily_limit: 47,
  response_timeout: 30,
  web_enabled: true,
  web_mode: "automatic",
  attempts_today: 2,
  login_state: "idle",
  login_message: "",
  message: "",
});

async function mockAccount(page: Page, connected = true) {
  const state = profile(connected),
    writes: Record<string, unknown>[] = [];
  let failNext = false;
  await page.route("**/api/assistant/connection", async (route) => {
    const request = route.request();
    if (request.method() === "PUT") {
      const patch = request.postDataJSON();
      writes.push(patch);
      if (failNext) {
        failNext = false;
        await route.fulfill({
          status: 500,
          json: { detail: "Falha de teste ao salvar" },
        });
        return;
      }
      Object.assign(state, patch);
    } else if (request.method() === "DELETE")
      Object.assign(state, profile(false));
    await route.fulfill({ json: state });
  });
  return {
    state,
    writes,
    fail: () => {
      failNext = true;
    },
  };
}

async function settings(page: Page) {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name: "Configurações", exact: true })
    .click();
  const region = page.getByRole("region", {
    name: "Inteligência Artificial",
    exact: true,
  });
  await expect(region).toBeVisible();
  return region;
}

test("Conexão restaurada usa apenas ChatGPT sem exigir chaves", async ({
  page,
}) => {
  await mockAccount(page);
  const region = await settings(page);
  await expect(region).toContainText(
    "ChatGPT conectado · pronto para conversar",
  );
  await expect(
    region.getByRole("button", { name: "Pausar ChatGPT" }),
  ).toBeVisible();
  await expect(region.getByRole("textbox", { name: /chave/i })).toHaveCount(0);
  await expect(region).not.toContainText("Ollama");
  await expect(region).not.toContainText("Tavily");
});

test("Limite de consultas continua salvo depois de recarregar", async ({
  page,
}) => {
  const mock = await mockAccount(page);
  let region = await settings(page);
  await region.getByText("Preferências da conexão", { exact: true }).click();
  await region.getByLabel("Máximo de consultas por dia").fill("51");
  await region.getByLabel("Máximo de consultas por dia").blur();
  await expect(
    region.getByRole("status").filter({ hasText: "Alterações salvas" }),
  ).toBeVisible();
  expect(mock.state.daily_limit).toBe(51);
  expect(mock.state.model).toBe("gpt-5.6-sol");
  expect(mock.state.enabled).toBe(true);
  await page.reload();
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name: "Configurações", exact: true })
    .click();
  region = page.getByRole("region", {
    name: "Inteligência Artificial",
    exact: true,
  });
  await region.getByText("Preferências da conexão", { exact: true }).click();
  await expect(region.getByLabel("Máximo de consultas por dia")).toHaveValue(
    "51",
  );
});

test("Falha ao salvar não confirma nem perde a edição; permite nova tentativa", async ({
  page,
}) => {
  const mock = await mockAccount(page);
  const region = await settings(page);
  await region.getByText("Preferências da conexão", { exact: true }).click();
  mock.fail();
  const limit = region.getByLabel("Máximo de consultas por dia");
  await limit.fill("63");
  await limit.blur();
  await expect(region.getByRole("alert")).toContainText("Falha de teste");
  await expect(limit).toHaveValue("63");
  expect(mock.state.daily_limit).toBe(47);
  await limit.focus();
  await limit.blur();
  await expect(
    region.getByRole("status").filter({ hasText: "Alterações salvas" }),
  ).toBeVisible();
  expect(mock.state.daily_limit).toBe(63);
});

test("Instalação nova oferece login próprio e cliente não configura a conta", async ({
  page,
}) => {
  await mockAccount(page, false);
  const region = await settings(page);
  await expect(
    region.getByRole("button", { name: "Continuar com ChatGPT" }),
  ).toBeVisible();
  await expect(region).toContainText("nenhuma credencial do desenvolvedor");
  await page.goto("/");
  // Return to login through the saved session menu rather than opening OAuth.
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.reload();
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await page.getByRole("button", { name: "Fale com o Rafinha" }).click();
  await page.getByRole("button", { name: "Preferências do Rafinha" }).click();
  await expect(
    page.getByRole("button", { name: "Continuar com ChatGPT" }),
  ).toHaveCount(0);
});
