# Navegação, projetos e fotografias — 10 de outubro de 2026

O caminho de navegação é compartilhado pelas áreas do cliente e do administrador. Os níveis anteriores são clicáveis: loja, catálogo, categoria, serviços, projetos, aprendizado, biblioteca e áreas administrativas. Detalhes de produtos, projetos, serviços e guias mostram o nome do registro atual. Os filtros de guias limpam a seleção anterior para manter o caminho coerente. No administrador, o caminho divide a linha do título para conservar o espaço dos gráficos e tabelas.

O menu superior usa **Produtos**, com acesso inicial a todas as categorias. A categoria **Plantas** continua disponível no catálogo. Cada escolha de categoria atualiza o caminho e o filtro correspondente.

Os fundos dos painéis, cabeçalho e controles claros passaram a ser opacos, mantendo o fundo botânico fora dos containers. A ficha do produto usa uma galeria grande à esquerda e informações à direita no desktop; fotos inteiras, centralizadas e ampliáveis. O catálogo usa quadros quadrados iguais para todas as fotos. A escala das fotografias foi aumentada sem modificar os arquivos botânicos nem seus créditos. O botão fechado do Rafinha fica à esquerda na ficha para não encobrir os campos.

Seis projetos fictícios foram acrescentados à conta de demonstração de Rafael, um por etapa: Orçamento, Aprovado, Planejamento, Execução, Finalizado e Manutenção. Incluem espécies, custos planejados, tarefas, histórico, referência visual e planta 2D. A inserção é versionada, não duplica registros nem altera projetos existentes. Não gera cobranças ou consumos de estoque.

## Verificação

- 529 testes do backend e da distribuição aprovados.
- 39 cenários distintos da interface aprovados, incluindo navegação, aprendizado, filtros, projetos, fotos, fichas, áreas administrativas e Rafinha. Os cenários afetados foram repetidos após os ajustes finais.
- Galeria e campos conferidos em 1280 × 720, 1366 × 768 e 1920 × 1080. Navegação e leitura também conferidas em 390 × 844.
- Portal local: sete projetos visíveis para Rafael, incluindo os seis novos exemplos.
- Capturas locais em `.local/qa-navigation-photos/`.

A conta ChatGPT e o cofre privado do Rafinha permanecem separados da distribuição pública.

## Distribuição

- ZIP: `release/windows/20261010-191006/AtelieVerde-Windows.zip` (231.715.329 bytes).
- SHA256: `15b81440f7f41c663d879e49f37ba648355c8c7ae752fefa019a6f7b38cb57f7`.
- Os 1.049 arquivos do ZIP foram comparados com os da pasta verificada.
- Scanner sem achados: 1.047 arquivos, 1.932 entradas compiladas e 288 recursos públicos. Três segredos locais foram comparados sem expor seus valores.
- Teste de instalação sem credenciais: 13 verificações aprovadas, incluindo ChatGPT bloqueado até login próprio; zero chamadas externas.
- Portal final ativo e saudável em `http://127.0.0.1:5173`.
