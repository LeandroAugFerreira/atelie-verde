import { test, expect, type Page } from "@playwright/test";
import { resolve } from "node:path";

async function client(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Fale com o Rafinha", exact: true }),
  ).toBeVisible();
  const token = await page.evaluate(() =>
    sessionStorage.getItem("greenscape-token"),
  );
  const headers = { Authorization: `Bearer ${token}` };
  await page.request.put("/api/assistant/preferences", {
    headers,
    data: { enabled: true, motion: false, typewriter: false, voice: false },
  });
  await page.reload();
  return headers;
}
async function open(page: Page) {
  await page
    .getByRole("button", { name: "Fale com o Rafinha", exact: true })
    .click();
  await expect(
    page.getByRole("dialog", { name: "Conversa com Rafinha" }),
  ).toBeVisible();
}
async function send(page: Page, text: string) {
  const previous = await page.locator(".rafinha-message.assistant").count();
  await page
    .getByLabel("Sua mensagem para o Rafinha", { exact: true })
    .fill(text);
  await page
    .getByLabel("Sua mensagem para o Rafinha", { exact: true })
    .press("Enter");
  await expect(page.locator(".rafinha-message.assistant")).toHaveCount(
    previous + 1,
  );
  await expect(
    page.getByRole("button", { name: "Interromper resposta", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.locator(".rafinha-message.assistant").last(),
  ).not.toContainText("Preparando");
  await expect(page.locator(".rafinha-message.assistant").last()).toBeVisible();
}

test("Minimizar preserva conversa e rascunho; fechar encerra e limpa", async ({
  page,
}) => {
  const headers = await client(page);
  await open(page);
  await send(page, "Tenho uma Lavanda");
  const messages = await page.locator(".rafinha-message").allTextContents();
  await page
    .getByLabel("Sua mensagem para o Rafinha", { exact: true })
    .fill("Ela está em vaso");
  const conversations = await page.request.get("/api/assistant/conversations", {
    headers,
  });
  const cid = (await conversations.json())[0].id;
  await page
    .getByRole("button", { name: "Minimizar Rafinha", exact: true })
    .click();
  await expect(
    page.getByRole("dialog", { name: "Conversa com Rafinha" }),
  ).toHaveCount(0);
  expect(
    (
      await page.request.get(`/api/assistant/conversations/${cid}`, { headers })
    ).status(),
  ).toBe(200);
  await open(page);
  expect(await page.locator(".rafinha-message").allTextContents()).toEqual(
    messages,
  );
  await expect(
    page.getByLabel("Sua mensagem para o Rafinha", { exact: true }),
  ).toHaveValue("Ela está em vaso");
  await page
    .getByRole("button", { name: "Fechar conversa do Rafinha", exact: true })
    .click();
  await expect
    .poll(async () =>
      (
        await page.request.get(`/api/assistant/conversations/${cid}`, {
          headers,
        })
      ).status(),
    )
    .toBe(404);
  await open(page);
  await expect(page.locator(".rafinha-message")).toHaveCount(0);
  await expect(
    page.getByLabel("Sua mensagem para o Rafinha", { exact: true }),
  ).toHaveValue("");
});

test("Resposta chega durante a espera, preserva preocupação e não repete a digitação", async ({
  page,
}) => {
  const headers = await client(page);
  await page.request.put("/api/assistant/preferences", {
    headers,
    data: { enabled: true, motion: true, typewriter: true, voice: false },
  });
  await page.reload();
  let requestId = "";
  let release!: () => void;
  const finish = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(
    "**/api/assistant/conversations/*/messages",
    async (route) => {
      requestId = route.request().postDataJSON().request_id;
      await finish;
      await route.continue();
    },
  );
  await page.route(
    "**/api/assistant/conversations/*/progress",
    async (route) => {
      await route.fulfill({
        json: {
          request_id: requestId,
          phase: "writing",
          expression: "concerned",
          text: "Vamos olhar a roseira com atenção. Confira a umidade da terra antes de regar.",
        },
      });
    },
  );
  await open(page);
  await page
    .getByLabel("Sua mensagem para o Rafinha", { exact: true })
    .fill("Minha roseira está murchando, esqueci de regar");
  await page
    .getByRole("button", { name: "Enviar mensagem ao Rafinha", exact: true })
    .click();
  try {
    await expect(
      page.getByLabel("Resposta do Rafinha sendo escrita"),
    ).toContainText("roseira com atenção");
    await expect(page.locator(".rafinha-character-frame")).toHaveAttribute(
      "data-expression",
      "serious",
    );
    await expect(
      page.getByRole("button", { name: "Interromper resposta", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Minimizar Rafinha", exact: true })
      .click();
    await open(page);
    await expect(
      page.getByLabel("Resposta do Rafinha sendo escrita"),
    ).toContainText("roseira com atenção");
  } finally {
    release();
  }
  await expect(
    page.getByRole("button", { name: "Interromper resposta", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByLabel("Resposta do Rafinha sendo escrita"),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", {
      name: "Mostrar resposta completa",
      exact: true,
    }),
  ).toHaveCount(0);
  await expect(page.locator(".rafinha-message.assistant")).toHaveCount(1);
  await expect(page.locator(".rafinha-character-frame")).toHaveAttribute(
    "data-expression",
    "serious",
  );
});

test("Conversa, preços atuais, histórico privado e retomada entre abas", async ({
  page,
}) => {
  const headers = await client(page);
  await open(page);
  await expect(page.locator(".rafinha-welcome")).toBeVisible();
  await expect(page.locator(".rafinha-panel header")).toContainText(
    "Orientações do catálogo",
  );
  await send(page, "Como cuidar da Lavanda?");
  await expect(page.locator(".rafinha-welcome")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Preferências do Rafinha", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "Lavanda",
  );
  await expect(
    page.locator(".rafinha-actions").last().getByRole("button").first(),
  ).toBeVisible();
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Aprender", exact: true })
    .click();
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "Lavanda",
  );
  await send(page, "Qual o preço e estoque da Lavanda?");
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "R$",
  );
  const id = await page.evaluate(() =>
    Number(sessionStorage.getItem("atelie-rafinha-conversation-2")),
  );
  expect(id).toBeGreaterThan(0);
  await page
    .getByRole("button", { name: "Histórico de conversas", exact: true })
    .click();
  await page
    .getByRole("button", { name: `Excluir conversa ${id}`, exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: `Excluir conversa ${id}`, exact: true }),
  ).toHaveCount(0);
  const detail = await page.request.get(`/api/assistant/conversations/${id}`, {
    headers,
  });
  expect(detail.status()).toBe(404);
  await page
    .getByRole("button", { name: "Fechar conversa do Rafinha", exact: true })
    .click();
  await open(page);
  await expect(page.locator(".rafinha-message")).toHaveCount(0);
});

test("Contexto de produto, guia e serviço usa as telas existentes", async ({
  page,
}) => {
  await client(page);
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Produtos", exact: true })
    .click();
  await page
    .locator(".catalog-card")
    .filter({ hasText: "Hibisco" })
    .getByRole("button", { name: "Hibisco", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Perguntar ao Rafinha sobre esta planta",
      exact: true,
    })
    .click();
  await expect(page.locator(".rafinha-context")).toContainText("Hibisco");
  await send(page, "Como regar esta planta?");
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "Hibisco",
  );
  await page
    .getByRole("button", { name: "Fechar conversa do Rafinha", exact: true })
    .click();
  await page
    .locator(".client-nav")
    .getByRole("button", { name: "Aprender", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Tirar uma dúvida sobre este guia",
      exact: true,
    })
    .click();
  await expect(page.locator(".rafinha-context")).toBeVisible();
  await page
    .getByRole("button", { name: "Nova conversa", exact: true })
    .click();
  await send(page, "Quero contratar paisagista virtual e solicitar orçamento");
  await page
    .locator(".rafinha-actions")
    .last()
    .getByRole("button", { name: "Solicitar orçamento", exact: true })
    .click();
  await expect(page.locator(".landscape-studio")).toBeVisible();
  await expect(page.locator(".rafinha")).toHaveCount(0);
});

test("Texto progressivo, preferência acessível e layout a 100%", async ({
  page,
}) => {
  const headers = await client(page);
  await page.request.put("/api/assistant/preferences", {
    headers,
    data: { enabled: true, motion: true, typewriter: true, voice: false },
  });
  await page.reload();
  await open(page);
  await page
    .getByLabel("Sua mensagem para o Rafinha", { exact: true })
    .fill("Como cuidar da Lavanda?");
  await page
    .getByRole("button", { name: "Enviar mensagem ao Rafinha", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Mostrar resposta completa", exact: true })
    .click();
  for (const size of [
    { width: 1852, height: 964 },
    { width: 1366, height: 768 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(size);
    expect(
      await page
        .locator(".rafinha-panel, .rafinha-character")
        .evaluateAll((items) =>
          items.every((el) => {
            const b = el.getBoundingClientRect();
            return (
              b.left >= 0 &&
              b.right <= innerWidth + 1 &&
              b.top >= 0 &&
              b.bottom <= innerHeight + 1
            );
          }),
        ),
    ).toBe(true);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth <= innerWidth &&
          document.documentElement.scrollHeight <= innerHeight,
      ),
    ).toBe(true);
    const image = page.locator(".rafinha-character");
    await image.evaluate(async (img) => {
      await (img as HTMLImageElement).decode();
    });
    if (size.width !== 1366)
      await page.screenshot({
        path: resolve(`../docs/screenshots/rafinha-${size.width}.png`),
      });
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await send(page, "E como regar?");
  await expect(
    page.getByRole("button", {
      name: "Mostrar resposta completa",
      exact: true,
    }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Preferências do Rafinha", exact: true })
    .click();
  await page.getByLabel("Habilitar assistente", { exact: true }).uncheck();
  await page
    .getByRole("button", { name: "Fechar conversa do Rafinha", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Fale com o Rafinha", exact: true }),
  ).toHaveCount(0);
});

test("Administração configura apresentação e testa sem modificar vendas", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Administrador", exact: true })
    .click();
  await page
    .locator(".admin-sidebar")
    .getByRole("button", { name: "Configurações", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Testar atendimento", exact: true })
    .click();
  await expect(page.locator(".rafinha-admin-note")).toContainText("Lavanda");
  await page
    .getByRole("button", { name: "Salvar Rafinha", exact: true })
    .click();
  await expect(page.locator(".rafinha-admin-note")).toContainText(
    "Configurações do Rafinha salvas",
  );
});

test("Preocupação acompanha a resposta e fechar elimina a conversa ativa", async ({
  page,
}) => {
  const headers = await client(page);
  await open(page);
  await page
    .getByLabel("Sua mensagem para o Rafinha", { exact: true })
    .fill("Não molhei o Hibisco e as folhas estão murchas");
  await page
    .getByRole("button", { name: "Enviar mensagem ao Rafinha", exact: true })
    .click();
  await expect(page.locator(".rafinha-character")).toHaveAttribute(
    "src",
    "/rafinha/official/rafinha_serious.webp",
  );
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "com atenção",
    { timeout: 12000 },
  );
  await expect(page.locator(".rafinha-character")).toHaveAttribute(
    "src",
    "/rafinha/official/rafinha_serious.webp",
  );
  const id = await page.evaluate(() =>
    Number(sessionStorage.getItem("atelie-rafinha-conversation-2")),
  );
  await page
    .getByRole("button", { name: "Fechar conversa do Rafinha", exact: true })
    .click();
  await open(page);
  await expect(page.locator(".rafinha-message")).toHaveCount(0);
  await expect(
    page.getByLabel("Sua mensagem para o Rafinha", { exact: true }),
  ).toHaveValue("");
  await expect
    .poll(async () =>
      (
        await page.request.get(`/api/assistant/conversations/${id}`, {
          headers,
        })
      ).status(),
    )
    .toBe(404);
});

test("Logo único no login e marca legível no cabeçalho do cliente", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".login-visual .standalone-logo")).toBeVisible();
  await expect(page.locator(".login-form .standalone-logo")).not.toBeVisible();
  await expect(page.locator(".login-form .logo > span")).toHaveCount(0);
  await expect(page.locator(".login-form .company-logo")).toHaveAttribute(
    "src",
    "/rafinha/atelie-verde-logo-transparent.png",
  );
  await page.getByRole("button", { name: "Cliente", exact: true }).click();
  await expect(page.locator(".logo-link .logo > span")).toHaveCount(0);
  await expect(page.locator(".logo-link .company-logo")).toBeVisible();
});

test("Identificação aceita desconhecimento e mantém respostas curtas", async ({
  page,
}) => {
  await client(page);
  await open(page);
  await send(page, "Como cuidar da minha planta?");
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "nome da planta",
  );
  await send(page, "Não faço ideia.");
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "foto",
  );
  await expect(
    page.locator(".rafinha-message.assistant").last(),
  ).not.toContainText("nome da planta");
  await send(page, "Não tenho foto.");
  await send(page, "Mais ou menos.");
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "recortadas",
  );
  await send(page, "Tem recortes.");
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "flores",
  );
  await send(page, "Não.");
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "dentro ou fora",
  );
  await send(page, "Dentro.");
  await expect(
    page.locator(".rafinha-message.assistant").last(),
  ).not.toContainText("dentro ou fora");
});

test("Cliente conversa sem configuração de provedores e não acessa administração de IA", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (/\/api\/assistant\/(connection|admin-ai)/.test(request.url()))
      requests.push(request.url());
  });
  const headers = await client(page);
  await open(page);
  await expect(page.locator(".rafinha-welcome")).not.toContainText(
    "conexão pessoal",
  );
  await page
    .getByRole("button", { name: "Preferências do Rafinha", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Do seu jeito" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "IA do Rafinha", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Inteligência Artificial", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Continuar com ChatGPT", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByLabel("Chave pessoal da API", { exact: true }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Chave Tavily", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Chave OpenAI", { exact: true })).toHaveCount(0);
  await expect(
    page.getByLabel("Permitir pesquisa paga", { exact: true }),
  ).toHaveCount(0);
  expect(requests).toEqual([]);
  for (const [path, method, data] of [
    ["/api/assistant/admin-ai", "get", undefined],
    ["/api/assistant/admin-ai/local/health", "get", undefined],
    ["/api/assistant/admin-ai/settings", "put", { mode: "free_only" }],
    [
      "/api/assistant/admin-ai/providers/tavily/key",
      "post",
      { key: "tvly-placeholder-not-a-real-key" },
    ],
    [
      "/api/assistant/admin-ai/providers/openai/key",
      "post",
      { key: "sk-placeholder-not-a-real-key" },
    ],
    ["/api/assistant/admin-ai/providers/tavily/test", "post", undefined],
    ["/api/assistant/admin-ai/providers/openai", "delete", undefined],
  ] as const) {
    const response = await page.request.fetch(path, {
      method: method.toUpperCase(),
      headers,
      data,
    });
    expect(response.status()).toBe(403);
  }
  await page
    .getByRole("button", { name: "Preferências do Rafinha", exact: true })
    .click();
  await send(page, "Quem é você?");
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "assistente virtual do Ateliê Verde",
  );
});

test("Preferências do cliente são de apresentação e persistem após recarregar", async ({
  page,
}) => {
  const headers = await client(page);
  await open(page);
  const preferences = page.getByRole("button", {
    name: "Preferências do Rafinha",
    exact: true,
  });
  await preferences.click();
  await page.getByLabel("Movimentos do personagem", { exact: true }).check();
  await expect
    .poll(
      async () =>
        (
          await (
            await page.request.get("/api/assistant/preferences", { headers })
          ).json()
        ).motion,
    )
    .toBe(true);
  await page.getByLabel("Texto aparecendo aos poucos", { exact: true }).check();
  await expect
    .poll(
      async () =>
        (
          await (
            await page.request.get("/api/assistant/preferences", { headers })
          ).json()
        ).typewriter,
    )
    .toBe(true);
  await page.reload();
  await open(page);
  await preferences.click();
  await expect(
    page.getByLabel("Movimentos do personagem", { exact: true }),
  ).toBeChecked();
  await expect(
    page.getByLabel("Texto aparecendo aos poucos", { exact: true }),
  ).toBeChecked();
  await expect(
    page.getByLabel("Habilitar assistente", { exact: true }),
  ).toBeChecked();
  await expect(
    page.getByLabel("Exibir opção de ouvir resposta", { exact: true }),
  ).not.toBeChecked();
  await page
    .getByLabel("Texto aparecendo aos poucos", { exact: true })
    .uncheck();
  await expect
    .poll(
      async () =>
        (
          await (
            await page.request.get("/api/assistant/preferences", { headers })
          ).json()
        ).typewriter,
    )
    .toBe(false);
  await preferences.click();
  await send(page, "Tenho uma planta, uma roseira");
  await expect(page.locator(".rafinha-message.assistant").last()).toContainText(
    "poda",
  );
  await expect(
    page.locator(".rafinha-message.assistant").last(),
  ).not.toContainText("nome da planta");
});

test("Pesquisa mostra citações, fontes e galeria com origem no desktop e mobile", async ({
  page,
}) => {
  await client(page);
  await page.route("https://images.example.test/plant.jpg", (route) =>
    route.fulfill({
      path: resolve("public/plants/plinia-cauliflora-1.jpg"),
      contentType: "image/jpeg",
    }),
  );
  await page.route("https://images.example.test/plant-thumbnail.jpg", (route) =>
    route.fulfill({ status: 404, body: "Thumbnail unavailable" }),
  );
  await page.route(
    /\/api\/assistant\/conversations\/\d+\/messages$/,
    async (route) => {
      const response = await route.fetch();
      const last = await response.json();
      Object.assign(last, {
        mode: "chatgpt",
        text: "Uma possibilidade é *Crassula ovata 'Gollum'*, pelas folhas tubulares. É uma hipótese. [1]",
        meta: { source_type: "web", searched_web: true },
        sources: [
          {
            title: "NC State Extension",
            url: "https://plants.ces.ncsu.edu/plants/crassula-ovata/",
          },
        ],
        images: [
          {
            image_url: "https://images.example.test/plant.jpg",
            thumbnail_url: "https://images.example.test/plant-thumbnail.jpg",
            source_url: "https://plants.ces.ncsu.edu/plants/crassula-ovata/",
            domain: "plants.ces.ncsu.edu",
            caption: "Folhas da candidata",
          },
        ],
      });
      await route.fulfill({ json: last });
    },
  );
  await open(page);
  await send(page, "Que suculenta parece a orelha do Shrek?");
  const answer = page.locator(".rafinha-message.assistant").last();
  await expect(answer).toContainText("Pesquisa web");
  await expect(
    answer.getByRole("link", { name: "Fonte: NC State Extension" }),
  ).toHaveAttribute(
    "href",
    "https://plants.ces.ncsu.edu/plants/crassula-ovata/",
  );
  await expect(
    answer.getByRole("region", { name: "Imagens de referência da pesquisa" }),
  ).toBeVisible();
  await expect(answer.getByAltText("Folhas da candidata")).toBeVisible();
  await answer.getByText("Fontes consultadas (1)", { exact: true }).click();
  await expect(
    answer.getByRole("link", { name: "NC State Extension", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(answer.getByAltText("Folhas da candidata")).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
});

test("Grupo incerto e excesso de água recebem orientação e expressão de preocupação", async ({
  page,
}) => {
  await client(page);
  await open(page);
  await send(
    page,
    "eu só sei que é uma suculenta, parece com a orelha do Sherek",
  );
  await send(page, "eu não deixei ela no sol e reguei muito");
  const answer = page.locator(".rafinha-message.assistant").last();
  await expect(answer).toContainText("umidade");
  await expect(answer.locator("ol li")).toHaveCount(3);
  await expect(answer).not.toContainText("dentro ou fora");
  await expect(answer).not.toContainText("nome da planta");
  await expect(page.locator(".rafinha-character")).toHaveAttribute(
    "src",
    "/rafinha/official/rafinha_serious.webp",
  );
});

test("Fechar durante o envio da foto não reabre nem recria a conversa", async ({
  page,
}) => {
  const headers = await client(page);
  await open(page);
  await send(page, "Tenho uma Lavanda");
  let release!: () => void;
  const current = (
    await (
      await page.request.get("/api/assistant/conversations", { headers })
    ).json()
  )[0].id;
  let arrived!: () => void;
  const received = new Promise<void>((resolve) => {
    arrived = resolve;
  });
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(
    "**/api/assistant/conversations/*/attachments",
    async (route) => {
      arrived();
      await held;
      await route.continue();
    },
  );
  await page
    .getByLabel("Anexar foto da planta", { exact: true })
    .setInputFiles(resolve("public/plants/plinia-cauliflora-1.jpg"));
  await received;
  await page
    .getByRole("button", { name: "Fechar conversa do Rafinha", exact: true })
    .click();
  await expect
    .poll(async () =>
      (
        await page.request.get(`/api/assistant/conversations/${current}`, {
          headers,
        })
      ).status(),
    )
    .toBe(404);
  const completed = page.waitForResponse(
    (response) =>
      /\/attachments$/.test(response.url()) &&
      response.request().method() === "POST",
  );
  release();
  await completed;
  await open(page);
  await expect(page.locator(".rafinha-photo-list")).toHaveCount(0);
  await expect(page.locator(".rafinha-message")).toHaveCount(0);
  await expect(page.locator(".rafinha-error")).toHaveCount(0);
  await expect(
    page.getByLabel("Anexar foto da planta", { exact: true }),
  ).toBeEnabled();
});

test("Foto de referência privada e reação de perda", async ({ page }) => {
  await client(page);
  await open(page);
  await expect(
    page.getByLabel("Anexar foto da planta", { exact: true }),
  ).toBeEnabled();
  await page
    .getByLabel("Anexar foto da planta", { exact: true })
    .setInputFiles(resolve("public/plants/plinia-cauliflora-1.jpg"));
  await expect(
    page.getByAltText("Foto da planta enviada nesta conversa"),
  ).toBeVisible();
  await expect(page.locator(".rafinha-photo-list")).toContainText(
    "A análise visual utiliza a conexão ChatGPT",
  );
  await expect(page.locator(".rafinha-message.assistant").last()).toBeVisible();
  await send(page, "Minha planta morreu.");
  await expect(page.locator(".rafinha-character")).toHaveAttribute(
    "src",
    "/rafinha/official/rafinha_sad.webp",
  );
  await page
    .getByRole("button", { name: "Fechar conversa do Rafinha", exact: true })
    .click();
  await open(page);
  await expect(page.locator(".rafinha-photo-list")).toHaveCount(0);
});

test("As 12 expressões oficiais mantêm a composição e a ponta na boca", async ({
  page,
}) => {
  await client(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await open(page);
  const names = [
    "happy",
    "sad",
    "serious",
    "angry",
    "thinking",
    "sleepy",
    "greeting",
    "surprised",
    "shy",
    "skeptical",
    "delighted",
    "celebrating",
  ];
  let expression = names[0];
  await page.route(
    "**/api/assistant/conversations/*/messages",
    async (route) => {
      const response = await route.fetch();
      await route.fulfill({ json: { ...(await response.json()), expression } });
    },
  );
  const before = await page.locator(".rafinha-character-frame").boundingBox();
  for (const name of names) {
    expression = name;
    await send(page, "Olá");
    const image = page.locator(".rafinha-character");
    await expect(image).toHaveAttribute(
      "src",
      `/rafinha/official/rafinha_${name}.webp`,
    );
    await image.evaluate(async (img) => {
      await (img as HTMLImageElement).decode();
    });
    const current = await page
      .locator(".rafinha-character-frame")
      .boundingBox();
    expect(current).toEqual(before);
  }
  for (const viewport of [
    { width: 1366, height: 768 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    const geometry = await page
      .locator(".rafinha-composition")
      .evaluate((element) => {
        const character = element
          .querySelector(".rafinha-character-frame")!
          .getBoundingClientRect();
        const bubble = element.querySelector(".rafinha-speech-bubble")!;
        const rect = bubble.getBoundingClientRect();
        const tip = getComputedStyle(bubble, "::before");
        const input = document
          .querySelector(".rafinha-panel > form")!
          .getBoundingClientRect();
        return {
          mouthX: character.x + character.width * 0.5,
          mouthY: character.y + character.height * 0.525,
          tipX: rect.x + parseFloat(tip.left) + 1,
          tipY:
            rect.bottom -
            parseFloat(tip.bottom) -
            parseFloat(tip.height) / 2 -
            1,
          characterBottom: character.bottom,
          inputTop: input.top,
          bubbleLeft: rect.left,
          characterLeft: character.left,
          inside:
            character.left >= 0 &&
            rect.right <= innerWidth &&
            input.bottom <= innerHeight,
        };
      });
    expect(Math.abs(geometry.mouthX - geometry.tipX)).toBeLessThan(2);
    expect(Math.abs(geometry.mouthY - geometry.tipY)).toBeLessThan(2);
    expect(geometry.characterBottom).toBeLessThanOrEqual(geometry.inputTop);
    expect(geometry.bubbleLeft).toBeGreaterThan(geometry.characterLeft);
    expect(geometry.inside).toBe(true);
  }
});

test("Expressão permanece sem outra mensagem, inclusive ao minimizar e escrever rascunho", async ({
  page,
}) => {
  await client(page);
  await page.clock.install();
  await open(page);
  let expression = "angry";
  await page.route(
    "**/api/assistant/conversations/*/messages",
    async (route) => {
      const response = await route.fetch();
      await route.fulfill({ json: { ...(await response.json()), expression } });
    },
  );
  await send(page, "Vou colocar detergente na minha planta");
  await expect(page.locator(".rafinha-character-frame")).toHaveAttribute(
    "data-expression",
    "angry",
  );
  await page.clock.fastForward(60000);
  await expect(page.locator(".rafinha-character-frame")).toHaveAttribute(
    "data-expression",
    "angry",
  );
  await page
    .getByLabel("Sua mensagem para o Rafinha", { exact: true })
    .fill("Não vou usar isso");
  await page
    .getByRole("button", { name: "Minimizar Rafinha", exact: true })
    .click();
  await page.clock.fastForward(60000);
  await open(page);
  await expect(page.locator(".rafinha-character-frame")).toHaveAttribute(
    "data-expression",
    "angry",
  );
  expression = "happy";
  await send(page, "Obrigado, ela se recuperou e deu certo!");
  await expect(page.locator(".rafinha-character-frame")).toHaveAttribute(
    "data-expression",
    "happy",
  );
});
