# Ateliê Verde — roteiro de demonstração técnica (3 minutos)

**Contexto:** caso hipotético de empreendedorismo, com cliente e produtos fictícios. A página pública é uma simulação, não a aplicação full stack executada online.

## 00:00–00:25 — Problema e solução

Abrir [Ateliê Verde](https://leandroaugferreira.github.io/atelie-verde.html).

Fala: “O Ateliê Verde combina portal de compras e gestão operacional. O foco técnico foi manter catálogo, pedidos, estoque e financeiro consistentes e controlar o que cada usuário pode fazer.”

## 00:25–01:10 — Compra

Abrir [tour web](https://leandroaugferreira.github.io/atelie-verde-demo.html), aba Compra e estoque. Registrar duas lavandas do estoque fictício de cinco unidades.

Fala: “No código real, o preço vem do servidor. Ao registrar duas unidades, o estoque passa de cinco para três, com pedido de R$ 49,80 e conta a receber pendente.”

## 01:10–01:35 — Idempotência e cancelamento

Clicar “Reenviar mesma solicitação”. Explicar que o mesmo identificador não gera nova venda. Depois cancelar e mostrar estoque de volta a cinco e conta cancelada.

Fala: “O backend mantém pedido, movimentação e conta em transação. Cancelamento duplicado é recusado; pagamento confirmado exige processo de reembolso.”

## 01:35–02:15 — Orçamento e projeto

Mudar para aba Orçamento e projeto. Solicitar serviço fictício, clicar Admin envia proposta (R$ 1.800,00) e Cliente aprova.

Fala: “A regra separa responsabilidades: o cliente solicita, o administrador precifica e o titular aprova uma proposta enviada. A aprovação gera projeto e evento, sem permitir duplicidade.”

## 02:15–02:45 — Código e testes

Abrir [checkout.py](../../backend/app/checkout.py), [main.py](../../backend/app/main.py), [teste integrado](../../backend/tests/test_recruiting_case.py) e [CI](https://github.com/LeandroAugFerreira/atelie-verde/actions).

Fala: “Essa página é um tour estático. Os testes do backend usam FastAPI/SQLAlchemy reais com bancos de teste; o CI ainda executa PostgreSQL, build React e Playwright.”

## 02:45–03:00 — Limitações transparentes

Fala: “Não existe gateway de pagamento ou vendas reais demonstradas. Para produção, revisaria sessão, dependências, migrations, privacidade, provedores de IA e infraestrutura.”

## Contingências

- Se o site estiver indisponível, use o README e o código de testes.
- Não chame o tour web de “checkout live”; ele não chama a API.
- Não mostre credenciais pessoais, integrações Rafinha externas ou bases reais.
- Não afirme operação comercial real, renda, clientes ou ganhos financeiros.

[Estudo de caso](ESTUDO_DE_CASO.md) · [15 perguntas](ENTREVISTA_TECNICA.md).
