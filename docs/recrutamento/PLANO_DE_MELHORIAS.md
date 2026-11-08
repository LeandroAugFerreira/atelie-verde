# Ateliê Verde — oportunidades para recrutamento e evolução do produto

**Revisão:** 08/11/2026. O Ateliê Verde é sistema demonstrativo, não operação comercial validada. Priorizar comprovação técnica sobre acumular mais funcionalidades.

| Prioridade | Trabalho | Impacto para recrutamento | Esforço | Risco | Critério de aceite |
| --- | --- | --- | --- | --- | --- |
| P0 | Testes integrados de pedido/estoque/financeiro e orçamento/projeto | Alta credibilidade de backend | Baixo | Baixo | Três casos novos aprovados em SQLite/PostgreSQL |
| P0 | Tour web estático sem backend com dois fluxos | Fácil acesso em celular | Médio | Baixo | Compra/idempotência/cancelamento e orçamento demonstráveis, avisos claros |
| P0 | Estudo de caso com evidências e limites comerciais | Comunicação e maturidade | Baixo | Baixo | Documentos e links verificáveis |
| P1 | Revisar autenticação de SPA, CSP, XSS e sessão | Segurança | Médio | Alto se mal implementado | Testes de regressão e revisão de threat model |
| P1 | Definir política de migrações para instalação/produção | Resiliência do banco | Médio | Médio | Sem depender de create_all para evoluir schema |
| P1 | E2E browser focado no fluxo do cliente com pedido e orçamento (além das 60 verificações existentes) | Prova visual end-to-end | Médio | Médio | Chrome + API + SQLite, dados descartáveis, sem terceiros |
| P1 | Revisar qualidade de imagens, acessibilidade, teclado e mobile | Experiência do usuário | Médio | Baixo | Lighthouse/axe e captura/teste por viewport |
| P1 | Revisar credenciais e permissões das integrações pessoais Rafinha | Segurança e privacidade | Alto | Alto | Sem export de tokens, com opt-in e política de armazenamento |
| P2 | Separar componentes React extensos e regras do assistente em módulos menores | Manutenção | Alto | Médio | Refatoração por etapas com testes preservados |
| P2 | Fluxo de reembolso, pagamentos reais e conciliação (somente caso negócio evolua) | Completude comercial | Alto | Alto | Gateway confiável, sandbox, controles financeiros e validação fiscal |
| P2 | Operação real, backups, logs, política LGPD, monitoramento e DNS HTTPS | Produto publicável | Alto | Alto | Aceites institucionais e QA de segurança |

## Decisão de arquitetura: apresentação pública

Foi escolhida uma **simulação estática** do fluxo comercial, em https://leandroaugferreira.github.io/atelie-verde-demo.html. Ela não executa API, não coleta dados e não gera transações. Isso evita publicar uma instância insegura apenas para mostrar um projeto ao recrutador.

A aplicação completa continua disponível no repositório e pacote Windows, com dados de demo e uso local. Para hospedagem pública da API, é preciso decidir orçamento e domínio, configurar HTTPS, isolamento, contas descartáveis com privilégios mínimos, política de expurgo, segurança das chaves e dos provedores externos e verificação de integração.

## Itens que NÃO devem ser tratados como concluídos

- Vendas, clientes, receita ou redução de custos reais; não há evidências.
- Checkout bancário, gateway de cartão ou integração financeira externa.
- Segurança operacional da autenticação e LGPD para contas de clientes externos.
- Qualidade irrestrita de recomendações botânicas ou dos provedores de IA; configuração opcional e revisão específica.
- Deploy público da API ou nova homologação de EXE nesta etapa.

## Regra de prioridade

Não criar novos módulos apenas para aumentar a quantidade de projetos. Recrutadores valorizam a capacidade de **explicar uma transação, mostrar teste reproduzível, discutir risco e documentar limite**. A próxima evolução de maior retorno seria E2E de cliente com Playwright e revisão de sessão/segurança, não outro chatbot.

[Auditoria](AUDITORIA.md) · [Evidências](EVIDENCIAS.md) · [Roteiro](ROTEIRO_DEMO.md).
