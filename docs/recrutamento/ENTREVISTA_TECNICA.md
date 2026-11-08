# Ateliê Verde — 15 perguntas técnicas para entrevistas Full Stack/Python

Respostas sustentadas no repositório. Revise o código e diferencie o que você implementou, o que investigou e onde utilizou apoio de IA antes de narrar experiência em primeira pessoa.

## 1. Qual problema você resolveu?
Sistema demonstrativo que conecta catálogo, compras, estoque, orçamentos, projetos e lançamentos financeiros para um negócio planejado de jardinagem. Não houve vendas reais comprovadas. Fonte: [README](../../README.md).

## 2. Qual a arquitetura da aplicação?
React/TypeScript/Vite no portal e administração, API FastAPI/Pydantic, SQLAlchemy e Alembic, banco SQLite local ou PostgreSQL configurável. Fonte: [Arquitetura](ARQUITETURA.md). **Estudar:** separação de responsabilidades.

## 3. Onde o preço do pedido é definido?
No backend, a partir da entidade Product, não do preço que o cliente possa tentar enviar. checkout agrega itens e calcula total. Fonte: [checkout.py](../../backend/app/checkout.py). **Estudar:** confiança em dados do cliente.

## 4. Como evita cobrança ou baixa duplicada ao repetir uma requisição?
Usa request_key e payload normalizado para identificar replay: mesma chave/mesmos itens retorna pedido existente; chave reaproveitada com outro conteúdo gera 409. Fonte: [checkout.py](../../backend/app/checkout.py). **Estudar:** idempotência em sistemas distribuídos.

## 5. O que acontece se um item não tem estoque?
A compra é recusada sem persistir pedido/baixa parciais; operações de estoque usam bloqueios/transação para lidar com concorrência. Fonte: [transactions.py](../../backend/app/transactions.py) e [test_flows.py](../../backend/tests/test_flows.py). **Estudar:** ACID, lock, rollback.

## 6. Como a venda afeta o financeiro?
Após pedido confirmado, é criado Ledger de Receita/Loja pendente, vinculado ao pedido; isso **não** representa pagamento bancário efetivo. Fonte: [checkout.py](../../backend/app/checkout.py). **Estudar:** eventos contábeis vs pagamentos.

## 7. Como funciona cancelamento?
O proprietário cancela pedido Confirmado se a conta ainda não foi paga, e o estoque é reposto uma vez; conta passa a Cancelado. Segunda tentativa retorna 409; quando pago, exige reembolso fora do cancelamento automático. Fonte: [main.py](../../backend/app/main.py). **Estudar:** transições de estado, compensações.

## 8. Como você protege dados entre clientes?
Filtra Orders e Quotes por customer_id e recusa acesso/cancelamento por outro usuário; endpoints admin validam papel também no servidor. Fonte: [main.py](../../backend/app/main.py) e [security.py](../../backend/app/security.py). **Estudar:** IDOR e autorização por recurso.

## 9. Como um orçamento vira projeto?
Cliente solicita, admin envia preço, apenas titular aprova quando status é Enviado; criação de Project e ProjectEvent ocorre na mesma transação e segunda aprovação falha. Fonte: [main.py](../../backend/app/main.py). **Estudar:** invariantes de domínio.

## 10. Para que serve Alembic?
Versionar alterações no esquema relacional em SQLite/PostgreSQL; o CI executa upgrade e check em ambos. O startup chama também create_all, o que merece revisão para futuras instalações em produção. Fonte: [CI](../../.github/workflows/ci.yml). **Estudar:** migrações versus criação automática.

## 11. Qual é o risco de salvar access token em sessionStorage?
Código JavaScript da mesma origem pode lê-lo, por isso XSS e conteúdo de terceiros são pontos críticos; antes de produção, estudar CSP e sessão com refresh/HttpOnly. Fonte: [frontend/src/api.ts](../../frontend/src/api.ts). **Estudar:** XSS, CSRF e cookies.

## 12. O Rafinha é uma IA obrigatoriamente conectada?
Não. O sistema possui respostas de catálogo e integrações configuráveis; provedores externos dependem de configuração, autorização e credenciais próprias. Fonte: [assistant_provider.py](../../backend/app/assistant_provider.py) e [documentação](../RAFINHA-BYOK-HIBRIDO.md). **Estudar:** segurança de segredos, custo e fallback.

## 13. Quais testes técnicos são verificáveis?
Suite pytest em SQLite/PostgreSQL, migrações Alembic, lint Ruff, build React e testes Playwright Chromium. Três novos testes percorrem compra/cancelamento, orçamento/projeto e bloqueio de cancelamento após pagamento. Consulte [EVIDENCIAS.md](EVIDENCIAS.md). **Estudar:** regressão e QA.

## 14. O que um recrutador consegue experimentar agora?
Um tour estático de duas jornadas fictícias em [atelie-verde-demo.html](https://leandroaugferreira.github.io/atelie-verde-demo.html), sem API real, pagamentos, tokens nem persistência. Código e logs do CI comprovam as regras reais. **Estudar:** diferença entre mock visual e sistema funcional testado.

## 15. O que você faria antes de publicar?
Threat modeling, cookies/sessão, headers/CSP, HTTPS, varredura de dependências, revisão das integrações do Rafinha, banco externo, migrations, observabilidade, backup, política de dados e testes de aceitação. O projeto não prova segurança nem conformidade fiscal/LGPD de produção. Fonte: [PLANO_DE_MELHORIAS.md](PLANO_DE_MELHORIAS.md).

---

## Treino recomendado

Abra os testes e explique em 90 segundos por que pedir duas lavandas de R$ 24,90 resulta em estoque 3 e conta pendente de R$ 49,80, e por que reenviar a requisição ou cancelar novamente não deve duplicar operações. Depois explique a transição de orçamento para projeto, incluindo autorização e estado.

**Não inventar:** clientes, vendas, receita, tempo economizado, integração bancária, IA externa ativa ou resultado comercial.
