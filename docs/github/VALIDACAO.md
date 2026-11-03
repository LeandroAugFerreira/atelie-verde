# Validação atual — 03/11/2026

A cópia foi validada após corrigir a preparação dos testes PostgreSQL e atualizar expectativas antigas da demonstração. Nenhum teste foi removido, ignorado ou marcado como falha permitida.

| Verificação | Resultado |
| --- | --- |
| API + empacotamento locais | 554 aprovados em execução completa |
| Ruff remoto | Aprovado |
| API SQLite no GitHub | 535 aprovados |
| API PostgreSQL no GitHub | 535 aprovados |
| Migrações e alembic check SQLite/PostgreSQL | Aprovados |
| Frontend build | Aprovado |
| Playwright Chromium | 60 aprovados |

Evidência remota: [GitHub Actions #2](https://github.com/LeandroAugFerreira/atelie-verde/actions/runs/41737751245), commit e72155bfb5680c48b7042c877cf6b55b52e8658e.

A fixture original inseria IDs fixos em tabelas recém-criadas; PostgreSQL não avançava as sequências. A fixture agora usa a geração de IDs do banco. A aplicação não precisou mudar sua lógica de persistência. Os testes de interface conferem os registros atuais da API, a superfície translúcida já definida no CSS e a área utilizável de tabelas em diferentes telas. Controles, imagens e filtros continuam exercitados; não foram afrouxadas as verificações de acesso, upload, fotos ou fluxos de negócio.

O backend local usou banco temporário, sem segredos herdados e com serviços externos bloqueados. O CI usa apenas bases descartáveis do runner e dados fictícios. Não houve conexão pessoal de IA, envio real de e-mail, implantação de produção ou novo instalador Windows. Os arquivos WAL/SHM e a chave local .jwt-secret foram excluídos antes da primeira publicação.

As evidências de 02/11/2026 abaixo são históricas e foram superadas pela execução completa e pelos resultados remotos acima.

---

# Validação da cópia fonte — 02/11/2026

Backend/checagens existentes: **553 casos na suíte + 1 caso aprovado no reteste da seleção**.

Frontend: build: aprovado.

Suíte completa: 553 passaram e 1 falhou pela referência do mascote omitida da seleção. A referência foi reincluída, sem alterar pixels/código/testes; o único caso afetado passou no reteste. São 554 casos distintos verificados, sem afirmar nova execução completa após a inclusão.

Playwright e a configuração PostgreSQL do workflow existente não foram executados nesta rodada.

Os testes Python usaram ambientes já instalados, com segredos de ambiente removidos e arquivos temporários confinados à pasta de trabalho. O processo principal bloqueou DNS/conexões externas; conexões de loopback e subprocessos existentes foram revisados. Não foram iniciados n8n, envio SMTP real, conexão pessoal de IA ou transmissão fiscal. As simulações e documentos produzidos pelos testes são fictícios e não acompanham o pacote fonte.

Os testes inicialmente executados no sandbox não concluíram a inicialização; a execução isolada com acesso local adequado resolveu esse bloqueio de ambiente. Duas execuções completas pararam no limite inicial de cinco minutos, sem serem contabilizadas como aprovação. Os resultados acima usam as execuções concluídas e o reteste explicitado.

Dependências Python não foram instaladas ou adicionadas. Os builds reutilizaram dependências locais copiadas; para Chronos, o frontend foi restaurado em diretório novo pelo mesmo lockfile, sem scripts de instalação. Nenhum manifest da aplicação foi alterado. Os avisos de depreciação do adaptador de TestClient e o aviso de tamanho de chunk no build Chronos não foram tratados como novas funcionalidades ou como testes reprovados; não houve troca de dependências para suprimi-los.

Não houve instalação completa do backend a partir de ambiente vazio, teste de produção, novo build de EXE ou implantação. Os comandos do README foram conferidos no código, incluindo o preenchimento local de campos secretos deixados vazios nos exemplos. Consulte as execuções remotas na página de Actions; este documento registra a validação local.

As evidências estruturadas nesta pasta registram resultados reais. Os originais e os arquivos de lógica da aplicação foram preservados; somente documentação, exemplos sem credenciais e configuração de CI diferem na cópia.
