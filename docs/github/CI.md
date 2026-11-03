# GitHub Actions — preparação local

Os workflows estão versionados; consulte o resultado remoto em https://github.com/LeandroAugFerreira/atelie-verde/actions. As evidências locais são registradas separadamente. Foram preparados/revisados com permissões de leitura e sem referência a secrets do autor, deploy, prefeitura, SMTP de operação ou conta pessoal de IA.

Os novos fluxos de testes usam apenas dependências já declaradas. As referências checkout, setup-python e setup-node foram conferidas nos README oficiais em 02/11/2026 e usam v7 nas cópias preparadas. Não foram inventados hashes de commits. A execução em Linux e o provisionamento do runner ainda precisam de comprovação no GitHub.

O workflow existente recebeu somente permissions/contents: read nesta cópia. PostgreSQL do runner e Playwright continuam sendo verificações planejadas, sem resultado remoto atribuído nesta sessão.

Referências primárias consultadas: [checkout](https://github.com/actions/checkout/blob/main/README.md), [setup-python](https://github.com/actions/setup-python/blob/main/README.md), [setup-node](https://github.com/actions/setup-node/blob/main/README.md). A consulta confirmou os exemplos com v7; os jobs propostos ainda não foram executados no GitHub.
