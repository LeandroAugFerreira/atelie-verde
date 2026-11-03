# Ateliê Verde no portfólio

O projeto foi incluído no portfólio de Leandro Augusto Ferreira em 11/10/2026.

- Cartão: https://leandroaugferreira.github.io/index.html#atelie-verde
- Página: https://leandroaugferreira.github.io/atelie-verde.html
- Release: https://github.com/LeandroAugFerreira/leandroaugferreira.github.io/releases/tag/atelie-verde-2026.10.11
- Download: https://github.com/LeandroAugFerreira/leandroaugferreira.github.io/releases/download/atelie-verde-2026.10.11/AtelieVerde-Windows.zip
- PR integrado: https://github.com/LeandroAugFerreira/leandroaugferreira.github.io/pull/3
- Commit de publicação: `5cb7a1bd091365a9e137d5badeeff10d71c14376`.

## Conteúdo

Cartão destacado na seção de aplicações, página própria, sete capturas atuais (loja, produtos, detalhes da planta, projetos, serviços, dashboard e Rafinha), galeria com ampliação, controles de teclado, arquitetura e instruções para executar a demonstração.

A página apresenta a conexão ChatGPT como opcional e própria de cada instalação. Não promete reproduzir todas as funções do aplicativo ChatGPT. Os dados são identificados como demonstrativos e o checkout não realiza cobranças online.

O cabeçalho do portfólio passou a permitir quebra do nome e dos botões em celulares pequenos. A referência inexistente `img/fundo-tech-2.jpeg` foi substituída pelo fundo já presente no repositório. As páginas e os controles do NexoLog foram preservados.

## Distribuição

Foi usada a distribuição já validada em `release/windows/20261011-215419/AtelieVerde-Windows.zip`, sem recompilar ou alterar seu conteúdo.

- Tamanho: 231.720.873 bytes.
- SHA-256: `239cab82ed11be3d7a5f3c83688d095ebb4528fd0866b1691304d6905e80bd3a`.
- Mesmo digest confirmado pelo GitHub no asset publicado.
- Checksum público: `AtelieVerde-Windows.sha256` na mesma release.
- Nenhuma credencial do desenvolvedor acompanha o pacote; o executável mantém o cofre público separado do ambiente de desenvolvimento.

O ZIP foi anexado a uma release, sem adicioná-lo ao histórico Git do portfólio. Sua pasta completa deve ser extraída, mantendo `_internal` ao lado de `AtelieVerde.exe`.

## Validação

25 verificações locais passaram: imagens, galerias, ampliação, navegação pelo teclado, Escape, retorno do foco, navegação entre as páginas, layouts de 320/390/768/1440 px, ausência de transbordamento e arquivos ausentes, vídeo Full HD e seleção de legendas do NexoLog. Capturas inspecionadas no desktop e no celular.

GitHub Pages: workflow `38193294111`, concluído com sucesso. Página e download público responderam HTTP 200; tamanho do download conferido com o arquivo local.

As evidências de QA ficam em `.local/portfolio/`, fora da publicação. O checkout do site está em `C:/Projetos/NexoLog-portfolio`; os arquivos adicionados são `atelie-verde.html`, `assets/atelie-verde.css`, `assets/atelie-verde.js` e `img/atelie-verde/`, além do cartão em `index.html`.

## Padronização dos cards e espaços reservados

Na revisão seguinte, o cartão do Ateliê Verde passou ao mesmo formato vertical das demais aplicações: imagem no topo, miniaturas, categoria, título, descrição, tecnologias e link para a página completa. O grid agora reúne os três projetos existentes e três espaços vazios (`novo-projeto-1`, `novo-projeto-2`, `novo-projeto-3`). A página do projeto e o download permanecem disponíveis.

17 conferências locais passaram, incluindo estilo e dimensões dos cards, três espaços sem ações fictícias, miniaturas, ampliação, independência das galerias, navegação e telas de 320/390 px sem transbordamento. Capturas de desktop e celular foram inspecionadas. A folha de estilos possui versão no endereço para atualizar o cache dos navegadores.

- PR: https://github.com/LeandroAugFerreira/leandroaugferreira.github.io/pull/4
- Commit integrado: `3fd9b8c2ceff798adb407d5189e655ffddac7311`.
