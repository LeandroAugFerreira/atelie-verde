# Lançamentos demonstrativos nos perfis de clientes

A lista de clientes já estava preenchida, mas cinco perfis fictícios estavam sem projetos, dois sem serviços e um sem histórico de recebimentos. A complementação preencheu esses vínculos em 12/10/2026.

- Cinco projetos adicionados, com espécies, materiais, serviços, cronograma, etapas, referência visual e planta 2D.
- Dois atendimentos concluídos adicionados aos perfis sem serviços.
- Um recebimento fictício de consultoria adicionado ao perfil sem histórico, no mesmo valor do atendimento: R$ 250,00.

Projetos associados a pagamentos históricos usam os valores já registrados. Nenhum pagamento existente foi duplicado ou alterado, e os estoques foram preservados. Os registros pertencem somente aos clientes de demonstração ativos, identificados pelos e-mails reservados `cliente@...` e `cliente2` a `cliente10` nos domínios de demonstração.

O módulo `backend/app/customer_activity_demo.py` é chamado apenas na carga `SEED_DEMO=true`, após o catálogo e os projetos iniciais. O marcador `demo-customer-activity-2026-10-12-v1` evita duplicações em reinícios. Cadastros pessoais e clientes inativos são preservados.

Aplicação local: cinco projetos, dois serviços e um recebimento criados. Totais após a complementação: 17 projetos, 42 atendimentos e 48 receitas pagas. Todos os dez clientes fictícios passaram a ter pelo menos um projeto.

Validação: cinco testes de demonstração passaram, incluindo isolamento por cliente, preservação dos pagamentos, idempotência e proteção dos perfis fora da demonstração. Lint aprovado; a consistência dos dados retornou zero erros. As abas Projetos, Serviços e Histórico foram conferidas nos perfis de André Santos, Patrícia Lima e Roberto Nunes. Evidências em `.local/qa-client-activity/`.

Backup anterior: `.local/backups/customer-activity-20261012-115934.db`.

## Distribuição atualizada

A nova distribuição está em `release/windows/20261012-120258/AtelieVerde-Windows.zip`, com 231.727.691 bytes e SHA-256 `275ea653f7a04c068966f02d510efe416bd43e8ce578b7cab4d15e64cfeb2852`. O executável passou nas treze verificações de instalação isolada e no scanner de segredos. A base criada pelo executável também foi conferida: todos os dez clientes fictícios possuem projetos.

PR do download: https://github.com/LeandroAugFerreira/leandroaugferreira.github.io/pull/6

Release pública: https://github.com/LeandroAugFerreira/leandroaugferreira.github.io/releases/tag/atelie-verde-2026.10.12-clientes

Commit publicado: `aca96fd0dfe3f7d28c77cb12c03df55de806fb3a`. GitHub Pages concluído com sucesso no workflow `38268630372`; link e SHA-256 conferidos na página pública e download respondeu HTTP 200.
