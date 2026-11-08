# Ateliê Verde — evidências técnicas para recrutamento

**Data:** 08/11/2026. **Execução efetiva dos testes novos:** [GitHub Actions #42531033867](https://github.com/LeandroAugFerreira/atelie-verde/actions/runs/42531033867). **Commit testado:** bd9a768c327256787c11eaf3c20a8e4cd2b1ddf8.

## Resultados efetivamente executados nesta revisão

| Verificação | Resultado | Evidência |
| --- | --- | --- |
| Ruff (backend/app, backend/tests e migrations) | **Aprovado** | Job api do Actions |
| API pytest SQLite | **538 testes aprovados; 1 warning** | Job api do Actions |
| API pytest PostgreSQL 17 | **538 testes aprovados; 1 warning** | Job api com banco efêmero do runner |
| Alembic upgrade + check SQLite | **Aprovado** | Job api do Actions |
| Alembic upgrade + check PostgreSQL | **Aprovado** | Job api do Actions |
| Frontend React/TypeScript | **Build aprovado** | Job frontend |
| Playwright Chromium | **60 testes aprovados** | Job browser |
| Capturas de tela | **Artifact de QA gerado** | Artifact atelieverde-screenshots da execução |

Esses números são do código e das fixtures desta revisão, não métricas de clientes. O run anterior da main em [#41738540946](https://github.com/LeandroAugFerreira/atelie-verde/actions/runs/41738540946) já havia aprovado testes, antes dos **três testes de integração adicionais** desta etapa.

## Três testes novos e seu escopo exato

Arquivo: [backend/tests/test_recruiting_case.py](../../backend/tests/test_recruiting_case.py).

### Teste 1 — Compra idempotente, estoque, financeiro e cancelamento

Executado com usuários e produtos fictícios do conftest. Verifica compra de 2 lavandas (R$ 24,90/un) → total R$ 49,80, estoque 5 → 3, lançamento financeiro Pendente, uma movimentação de saída, reenvio do mesmo request_key sem duplicação, proibição de acesso/cancelamento por outra conta e cancelamento autorizado → estoque 5, conta Cancelada e exatamente uma reposição. O segundo cancelamento retorna conflito.

### Teste 2 — Orçamento, aprovação e projeto

Cliente solicita serviço de teste com área hipotética 85 m²; não pode aprovar antes de o administrador enviar preço. O cliente não pode precificar. Admin define R$ 1.800,00. Outra conta não pode aprovar. Titular aprova, gerando um único projeto e ProjectEvent. Repetir aprovação/precificação de orçamento encerrado retorna conflito.

### Teste 3 — Pedido pago exige reembolso

Admin marca a conta vinculada como Paga; cancelar o pedido passa a retornar 409. Teste verifica que pedido permanece Confirmado e o estoque não é reposto indevidamente.

**Não foi executado:** gateway bancário, reembolso real, pagamentos reais, cliente externo ou operação de loja. Os testes operam somente tabelas e transações de teste.

## Evidências do frontend

Os 60 testes Playwright da suíte existente exercitam interface e fluxos de catálogo/gestão, layouts, fotos, Rafinha e controles comerciais, conforme [frontend/tests](../../frontend/tests). O CI usa servidor local e base fictícia por execução. **Esta etapa não acrescentou um novo teste Playwright**, mas confirmou a execução da suíte existente sobre a branch com os três novos testes Python.

As capturas automatizadas foram gravadas como artifact no GitHub Actions. Não são prints de operação comercial real.

## Simulação web e sua diferença da execução real

A página [Ateliê Verde — demonstração interativa](https://leandroaugferreira.github.io/atelie-verde-demo.html) reproduz didaticamente valores e transições dos testes, **sem requisição à API, banco, pagamentos, cadastro de visitantes nem serviços externos**. O cálculo exibido deriva das regras/fixtures verificadas; clicar na simulação não executa backend.

A prova técnica está nos testes Python e nos logs do Actions, não no JavaScript estático do tour.

## Cuidados e limitações

- Testes usam credenciais sintéticas; não reaproveitam dados do usuário nem sistemas de produção.
- O workflow usa PostgreSQL de CI com senha de runner documentada e banco de teste descartável; ela não corresponde a credencial de operação.
- A integração de IA pessoal do Rafinha não foi testada com contas externas nesta revisão; o provedor de catálogo é suficiente para a demonstração.
- A existência de testes e migrações não é pentest, certificação fiscal/LGPD ou autorização de deploy.
- A existência de Ledger é um registro financeiro interno, não uma cobrança ou transferência bancária.
- A aplicação completa não foi implantada na internet; esta entrega publicou somente um tour estático.
- O instalador Windows não foi reconstruído nem revalidado nesta fase.
- Responsividade completa, proteção contra XSS e revisão de provedores de IA continuam prioridades.

## Como reproduzir no próprio repositório

Executar em clone/ambiente descartável com dependências instaladas; os testes usam backend/tests/conftest.py para banco e dados sintéticos. Não levar arquivo .env ou credenciais reais para o runner.

~~~bash
python -m pytest backend/tests/test_recruiting_case.py -q
python -m pytest -q
npm --prefix frontend run build
(cd frontend && npx playwright test)
~~~

Para SQLite/PostgreSQL e migrações, usar o workflow [ci.yml](../../.github/workflows/ci.yml) como fonte exata; não apontar TEST_DATABASE_URL a um banco existente.

[Auditoria](AUDITORIA.md) · [Estudo de caso](ESTUDO_DE_CASO.md) · [Arquitetura](ARQUITETURA.md) · [Roteiro](ROTEIRO_DEMO.md).
