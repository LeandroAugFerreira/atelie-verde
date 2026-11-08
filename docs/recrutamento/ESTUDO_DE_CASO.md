# Ateliê Verde — estudo de caso técnico verificável

## Problema

Um futuro negócio de jardinagem precisa apresentar plantas, produtos e serviços ao cliente, registrar solicitações de compra e orçamento e coordenar estoque, contas, fornecedores e projetos. O Ateliê Verde transforma esse cenário em um sistema demonstrativo com portal e administração.

**Público pretendido:** cliente da loja/serviços e administrador operacional. Não foram observados nem entrevistados compradores reais para medir ganhos.

## Solução

Portal React/TypeScript para navegar produtos e serviços e realizar ações autorizadas. Backend FastAPI/Pydantic com SQLAlchemy e migrations Alembic para controlar regras, acesso, transações e persistência. SQLite local e PostgreSQL configurável. Assistente Rafinha com modo de catálogo e adaptadores pessoais opcionais que não são necessários para comprar ou pedir orçamento.

Os dois percursos principais são:

### 1. Compra → estoque → financeiro → cancelamento

- Produto de teste: Lavanda, SKU PL-001, estoque 5, preço de R$ 24,90.
- Cliente pede 2 unidades. A API aplica preço de cadastro, não o valor enviado pelo cliente.
- Transação cria pedido, movimentação de saída de 2 unidades e conta a receber pendente de R$ 49,80. Estoque passa de 5 para 3.
- Repetir o mesmo identificador de requisição não gera segunda baixa.
- Outro cliente não pode cancelar o pedido, e cliente comum não pode consultar razão financeiro/admin.
- Cancelamento do pedido não pago devolve 2 unidades e cancela conta a receber, retornando estoque a 5. Cancelamento repetido gera conflito.
- Um pedido marcado pago é bloqueado para cancelamento automático, exigindo processo de reembolso.

**Fontes:** [checkout](../../backend/app/checkout.py), [cancelamento](../../backend/app/main.py), [teste integrado](../../backend/tests/test_recruiting_case.py).

### 2. Orçamento → preço do administrador → aprovação → projeto

- Cliente de teste solicita serviço (Poda) para área hipotética de 85 m².
- A cotação nasce sem preço aprovado; o administrador atribui valor de teste R$ 1.800,00 e marca "Enviado".
- Somente o cliente titular aprova um orçamento enviado.
- A aprovação gera um projeto e um evento de aprovação uma única vez.
- Outro cliente não visualiza o projeto do titular; nova aprovação ou nova precificação do orçamento encerrado retorna conflito.

**Fontes:** [rotas](../../backend/app/main.py) e [teste integrado](../../backend/tests/test_recruiting_case.py).

## Decisões técnicas observáveis

| Decisão | Justificativa de engenharia |
| --- | --- |
| Preço calculado no backend | Evitar confiar em valores manipuláveis enviados pela interface |
| Chave idempotente | Evitar dupla venda em repetição de POST |
| Transação e bloqueio de linha | Manter pedido, estoque, conta e auditoria coerentes |
| Identificação do cliente titular | Restringir consulta/cancelamento/aprovação por usuário |
| Aprovação vinculada a status | Evitar criar projetos duplicados ou aprovar solicitação sem preço |
| Testes SQLite e PostgreSQL no CI | Detectar diferenças de concorrência, restrições e SQL |
| Tour web estático sem API | Permitir avaliação imediata por recrutadores sem contas ou exposição de dados |

## Arquitetura

Ver [ARQUITETURA.md](ARQUITETURA.md). O projeto mantém portal e administração na mesma aplicação React e compartilha regras no backend; interfaces de projeto e assistente são maiores que este caso e exigem análise própria.

## Evidências e honestidade

O repositório já tinha testes de backend e Playwright, inclusive validação SQLite/PostgreSQL. Esta etapa adiciona três testes de integração de percursos críticos, sem trocar dados reais nem inventar vendas. Os valores do case são os das fixtures em [conftest.py](../../backend/tests/conftest.py), não números do futuro Ateliê Verde.

**Sem pagamento real:** a conta a receber é um lançamento interno. O tour estático do portfólio não cria pedido; o backend real só é executado em teste/local.

## Limitações

A demonstração não comprova operação comercial, estoque real, emissão fiscal, nota, compliance LGPD, integração bancária, receita, ROI ou mercado validado. A segurança de provedores externos do Rafinha e a implantação pública precisam de avaliação própria. O instalador Windows não foi revalidado neste ciclo.

## Materiais

[Tour no navegador](https://leandroaugferreira.github.io/atelie-verde-demo.html) · [Evidências e logs](EVIDENCIAS.md) · [Roteiro de 3 minutos](ROTEIRO_DEMO.md) · [Perguntas técnicas](ENTREVISTA_TECNICA.md).
