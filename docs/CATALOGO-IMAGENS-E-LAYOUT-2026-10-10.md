# Catálogo e apresentação dos produtos — 10 de outubro de 2026

Os 21 produtos demonstrativos de vasos, substratos, fertilizantes, ferramentas e acessórios receberam imagens individuais. Cada arquivo mostra o item nomeado, inteiro e centralizado sobre fundo claro. Imagens de categorias são usadas somente na navegação por categorias. Um produto sem foto não herda a fotografia de uma categoria. As imagens novas são ilustrativas e identificadas dessa forma na ficha; fotos próprias cadastradas permanecem prioritárias e não são substituídas.

Arquivos: `C:/Projetos/GreenScape/frontend/public/catalog-media/products/`. Ferramenta utilizada: `imagegen` integrada. O conjunto de prompts está em [PROMPTS-PRODUTOS-INDIVIDUAIS.md](PROMPTS-PRODUTOS-INDIVIDUAIS.md). O vínculo por SKU e nome está em `backend/app/product_media_manifest.json` e é aplicado uma vez, sem alterar estoque, preços, nomes ou vendas.

As 80 imagens das 40 espécies foram conferidas visualmente com seus nomes científicos e referências de origem. A revisão priorizou fotografias identificadas na fonte e vistas que ajudam a reconhecer a planta, retirando ilustrações, imagens de detalhes pouco representativos e duplicações das galerias selecionadas. Vinte e duas fotografias em resolução maior foram escolhidas para 11 espécies; outras quatro galerias tiveram a imagem principal reorganizada. Os novos arquivos terminam em `-catalog-1-v1.jpg` ou `-catalog-2-v1.jpg`, dentro de `frontend/public/plants/`. Os créditos, licenças e referências permanecem no manifesto `backend/app/photo_curated_manifest.json`. Os originais são preservados.

As miniaturas usam a imagem inteira, com dimensões limitadas ao botão e alinhamento central. O mesmo enquadramento aparece nos itens da tabela, do carrinho e dos guias. As fichas de produtos sem espécie associada abrem na descrição e apresentam informações comerciais, sem dados de cultivo.

O fundo é a imagem fornecida pelo usuário, sem edição, salva em `frontend/public/decor/botanical-watercolor-v1.jpeg`. Projetos, Serviços, Aprender e a ficha do produto ficam sobre containers claros e opacos. A mensagem de projetos vazios ocupa a largura do campo e fica centralizada; o aviso repetido foi removido.

A ficha do produto foi reorganizada para desktops a partir de 1024 px de largura e 700 px de altura. As informações botânicas aparecem em duas colunas, o resumo não repete a foto, e os cuidados usam uma distribuição própria. A necessidade geral de água fica no resumo; a frequência detalhada continua em Cuidados. Créditos e fontes abrem em janelas próprias, evitando aumentar a página principal. Em telas menores, o layout mantém a navegação e a rolagem necessárias para preservar todo o conteúdo.

## Validação

- 527 testes de backend e distribuição aprovados.
- 29 cenários de interface aprovados, incluindo as três resoluções de desktop, produtos com e sem fotografia, galerias, filtros e recursos do Rafinha.
- Verificações de preservação de fotos próprias, descrições, preços e estoque, além da existência de uma imagem exclusiva para cada SKU demonstrativo.
- Ficha conferida em 1280 × 720, 1366 × 768 e 1920 × 1080; miniaturas e containers também conferidos em 390 × 844.
- Capturas locais em `.local/qa-catalog-individual/`; conferência botânica em `.local/plant-audit/` e `.local/plant-candidates/`.
- O Rafinha permanece no modo ChatGPT da conta autorizada; o executável público exige conexão própria e não distribui credenciais de desenvolvimento.

## Executável atualizado

- Pacote: `release/windows/20261010-170652/AtelieVerde-Windows.zip` (231.708.217 bytes).
- SHA256: `51186639afb4e0fac2c8c5cd17195a135385bb71163cb09d1b8bd98a205dae3e`.
- Os 1.049 arquivos do ZIP foram comparados com a pasta verificada.
- Scanner sem achados: 1.047 arquivos, 1.931 entradas compiladas e 288 recursos públicos; comparação de três segredos locais sem expor seus valores.
- Teste de instalação sem credenciais: 13 verificações aprovadas, ChatGPT bloqueado até login próprio e zero chamadas externas.
- Portal final saudável e ativo em `http://127.0.0.1:5173`, com 21 itens e 21 imagens exclusivas confirmados no catálogo.
