# Ateliê Verde — auditoria técnica para recrutamento

**Base:** código original da main em 08/11/2026, commit 190140e9817f556331632e08044d7827fb8e99c6. **Objetivo:** identificar evidências demonstráveis para Desenvolvedor Full Stack/Python, sem alegar operação comercial real.

## Parecer

O Ateliê Verde é uma aplicação full stack demonstrativa de jardinagem e paisagismo, com portal do cliente, catálogo, pedidos, estoque, serviços, orçamentos, projetos e gestão financeira, além do assistente Rafinha. O maior valor para entrevistas é a consistência transacional do fluxo comercial e a autorização por perfil, não o volume de telas ou a existência de um chatbot.

**Natureza do case:** o negócio ainda é projeto de empreendedorismo; testes e cadastros de demonstração não são evidência de vendas, atendimentos, ganhos, clientes externos ou produção.

## Código efetivamente inspecionado

- API: [main.py](../../backend/app/main.py), [operations.py](../../backend/app/operations.py), [business_routes.py](../../backend/app/business_routes.py).
- Regras: [checkout.py](../../backend/app/checkout.py), [business.py](../../backend/app/business.py), [transactions.py](../../backend/app/transactions.py), [landscaping.py](../../backend/app/landscaping.py).
- Persistência: [models.py](../../backend/app/models.py), [database.py](../../backend/app/database.py), [migrations](../../backend/migrations/versions).
- Segurança: [security.py](../../backend/app/security.py) e dependências admin/current_user nas rotas.
- Frontend: [App.tsx](../../frontend/src/App.tsx), [api.ts](../../frontend/src/api.ts), páginas comerciais, paisagismo e assistente.
- Verificações: [test_flows.py](../../backend/tests/test_flows.py), [test_commercial.py](../../backend/tests/test_commercial.py), [commercial.spec.ts](../../frontend/tests/commercial.spec.ts), [ci.yml](../../.github/workflows/ci.yml), novo [test_recruiting_case.py](../../backend/tests/test_recruiting_case.py).
- Assistente: vários módulos backend/app/assistant_*.py e documentação [RAFINHA-BYOK-HIBRIDO.md](../RAFINHA-BYOK-HIBRIDO.md); a inspeção não constitui auditoria completa de provedores externos.

A auditoria focou caminhos-chave. Não foram revisados exaustivamente todos os componentes, pacotes terceiros, direitos de imagens, binários ou infraestrutura.

## Funcionalidades identificadas

| Fluxo | Evidência em código | Situação |
| --- | --- | --- |
| Catálogo de produtos/espécies/serviços | GET /api/products, /api/species, /api/services; modelos SQLAlchemy | Implementado, dados demo sintéticos |
| Compra de produto | POST /api/orders → checkout | Implementado; preço calculado no servidor, baixa e conta a receber |
| Replay/idempotência | chave request_key e payload normalizado | Implementado e coberto por testes |
| Estoque e auditoria | change_stock, StockMove, AuditEvent | Implementado com transação/locks |
| Cancelamento | POST /api/orders/{id}/cancel | Implementado, reposição única e bloqueio quando pago |
| Orçamento e projeto | POST /api/quotes → PATCH price → POST approve | Implementado com autorização e criação de Project e ProjectEvent |
| Financeiro | Ledger/contas com status e vínculo do pedido | Implementado como registro; não é gateway bancário |
| Gestão de usuários e perfis | Login, current_user e admin | Implementado; autorização também no servidor |
| Rafinha | Catálogo local e integrações opcionais BYOK | Implementado com configurações/limites; não demonstrar como IA externa sempre ativa |
| Aplicativo Windows/packaging | packaging e scripts | Presente; não houve nova execução do instalador nesta etapa |

## Caminho de compra real

1. A API exige usuário cliente autenticado para comprar.
2. checkout agrega quantidades por produto, não confia em preço enviado pelo navegador.
3. Adquire locks de usuário/produtos; rejeita estoque insuficiente sem gravar pedido parcial.
4. Persiste Order, Ledger pendente, baixa de estoque e auditoria na transação.
5. O mesmo request_key com payload idêntico devolve o pedido existente; chave reutilizada com conteúdo diferente retorna conflito.
6. No cancelamento autorizado e ainda não pago, devolve unidades, cancela a conta e registra o evento; repetir cancelamento gera conflito.
7. Pedido já pago exige processo de reembolso e não pode ser cancelado automaticamente.

Referências: [checkout.py](../../backend/app/checkout.py), [main.py](../../backend/app/main.py), [transactions.py](../../backend/app/transactions.py).

## Caminho do orçamento real

1. Cliente autenticado solicita orçamento de serviço; outro cliente não pode atribuir a solicitação para si indevidamente.
2. Somente admin altera preço e envia orçamento.
3. O cliente titular pode aprovar apenas orçamento enviado; uma segunda aprovação falha.
4. A aprovação cria Project e ProjectEvent; outro cliente não tem acesso aos projetos do titular.

Referências: [main.py](../../backend/app/main.py), [test_flows.py](../../backend/tests/test_flows.py).

## Segurança e limitações relevantes

**Pontos positivos:** JWT validado, senha com hash via pwdlib, verificação administrativa no servidor, ownership de pedidos e orçamentos, preço vindo do banco, locks e rollback comercial, upload com restrições e testes anteriores de isolamento.

**Pontos que exigem atenção antes de qualquer serviço público:** o frontend armazena access token em sessionStorage (superfície frente a XSS), há um segredo de desenvolvimento salvo em arquivo local quando não configurado (produção exige JWT_SECRET), as tabelas são criadas automaticamente com metadata.create_all no lifespan apesar das migrations explícitas, e as integrações de Rafinha exigem revisão independente de credenciais, provedores, consentimento e custos. Fazer threat modeling, CSP, renovação de sessão e estratégia de migrations antes do deploy. Estes são riscos de revisão, não alegações de exploração.

**Não existe evidência de:** gateway de pagamento online real, faturamento de clientes externos, conformidade tributária automaticamente garantida, prontidão LGPD, implantação pública segura, operação do negócio ou certificação do assistente.

## Recomendação para currículo/entrevista

Descrever: "Ateliê Verde — aplicação demonstrativa Full Stack em React/TypeScript + FastAPI/SQLAlchemy, com fluxos transacionais de pedidos, estoque, contas e aprovação de orçamentos, protegidos por perfis e testes em SQLite/PostgreSQL." Não chamar de loja com vendas reais nem divulgar métricas comerciais não medidas.

[Estudo de caso](ESTUDO_DE_CASO.md) · [Arquitetura](ARQUITETURA.md) · [Evidências](EVIDENCIAS.md) · [Plano de melhorias](PLANO_DE_MELHORIAS.md).
