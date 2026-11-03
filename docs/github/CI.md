# GitHub Actions

O workflow .github/workflows/ci.yml usa permissões contents: read, sem secrets pessoais, deploy ou serviços empresariais. Executa Ruff, API com SQLite, API com PostgreSQL 17 descartável, migrações e alembic check em ambos os bancos, build React e Playwright Chromium.

Execução comprovada: [Actions #2 — sucesso](https://github.com/LeandroAugFerreira/atelie-verde/actions/runs/41737751245). Foram aprovados 535 testes em cada banco, 60 casos de navegador e o build. Consulte [VALIDACAO.md](VALIDACAO.md) para as correções e os limites da verificação.

As dependências são as já declaradas nos manifests. Provedores de IA e credenciais pessoais não são usados. O job de navegador mantém evidências visuais como artefato; nenhum teste foi suprimido para alterar o resultado.
