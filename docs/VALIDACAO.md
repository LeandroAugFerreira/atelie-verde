# Validação local — 04/10/2026

## Resultado

- API: 24 testes passaram, com banco SQLite temporário isolado.
- Navegador Chromium: 11 cenários validados, com servidores e banco próprios (8 fluxos existentes e 3 novos testes administrativos).
- TypeScript e build de produção Vite: concluídos sem erros.
- Ruff: sem erros; dependências Python: `pip check` sem conflitos.
- Alembic: migração inicial aplicada a banco vazio; `alembic check` sem diferenças.
- Windows: inicialização, detecção de execução existente, encerramento e reinicialização conferidos pelos scripts em `scripts/`.

## Cobertura funcional

Os testes da API verificam autenticação, papéis, isolamento entre clientes, validação de imagens e PDFs, filtros, importação atômica de estoque, compra com linhas repetidas, concorrência sobre a última unidade, rollback em saldo insuficiente e devolução única no cancelamento. Também verificam aprovação única de orçamento, preservação do planejamento, etapas do projeto, conflitos de agenda, baixa financeira única, reconhecimento de receita, favoritos, avaliações após compra e acesso de clientes desativados.

Os testes de navegador verificam criação de produto e movimentação de estoque, compra e cancelamento pelo cliente, navegação administrativa, catálogo, detalhe de produto, favoritos, carrinho e ausência de transbordamento horizontal no celular.

## Visual

Capturas em `screenshots/` com viewport 1672 × 941 e escala 1, correspondente às referências fornecidas, além de viewport móvel 390 × 844. Sem ajuste global de zoom ou transformação para reduzir a interface. Sem rolagem geral do documento; o conteúdo extenso rola nos cards.

Os dados apresentados são calculados a partir da demonstração persistida. As estruturas seguem as referências; valores, datas, nomes de usuários e contagens podem variar com os dados. As 40 espécies usam 80 fotografias reais licenciadas. Os créditos estão na interface e em FONTES_PLANTAS.md. Banners e fotos de serviços continuam baseados nas referências fornecidas.

## Não executado localmente

Docker e PostgreSQL não foram executados porque Docker não está instalado nesta máquina. O Compose e a validação PostgreSQL no GitHub Actions estão configurados; não houve execução remota nem publicação externa. Pagamento, transporte e emissão fiscal externos não fazem parte do MVP.

## Atualização Ateliê Verde · 04/10/2026

- Banco local atualizado com Alembic; `alembic check` não detectou diferenças.
- 40 espécies, incluindo 4 cactos e 6 frutíferas; nenhuma sem produto ativo para venda. Total: 46 produtos e 10 guias.
- As 80 imagens foram decodificadas e verificadas com Pillow; cada uma tem autor, licença e origem no manifesto.
- Comparação com backup confirmou preservação dos 18 pedidos, 5 projetos, 10 orçamentos, 55 lançamentos, 20 agendamentos, históricos e demais registros anteriores. Preços e saldos dos 16 produtos existentes preservados.
- Testes adicionais cobrem atualização de perfil sem alteração de papel, conflito de e-mail, propriedade e substituição de avatar, progresso privado e idempotente, importação do catálogo sem sobrescrever alterações posteriores e venda de todas as espécies.
- Navegador: upload e remoção de avatar persistidos, progresso de leitura, cactos e frutíferas no carrinho e todas as abas em 1672 × 941, 1366 × 768 e 390 × 844, com zoom/escala padrão. A validação inclui alcançar o botão de compra dentro do card sem cortar seu conteúdo.

## Ajustes administrativos e projetos

- Cards revisados nas dez abas administrativas em 1672 × 941, 1366 × 768 e 1024 × 768, mantendo zoom/escala padrão.
- KPIs mais baixos, plantas decorativas fotográficas inteiras com fundo transparente, `object-fit: contain`, sem recorte e opacidade de 65%.
- Gráficos redimensionados pelo espaço disponível. Testes verificam ausência de rolagem no corpo dos gráficos, legendas dentro do card e SVG com dimensões correspondentes ao espaço renderizado.
- Contas a pagar e a receber com altura mínima verificada de 270 px nessas resoluções. Textos de tabela em uma linha; excesso horizontal e linhas extensas rolam dentro das tabelas, mantendo cabeçalho e paginação acessíveis.
- Filtros combinados de categoria, tipo de planta, estoque/situação, cidade, vínculo com projetos, serviço, responsável, etapas e intervalo de solicitação. Busca ignora acentos, filtros reiniciam a paginação e seleção de perfil acompanha os resultados.
- Cinco imagens ilustrativas distintas, criadas com IA, correspondem ao jardim frontal, varanda, entrada florida, área externa e pátio comercial. A interface identifica a origem; fotos enviadas têm prioridade nas capas, inclusive após recarregar.
- Migração `b9e74d0123ac` aplicada ao banco local e `alembic check` sem diferenças. Backup: `.local/backups/antes-cards-projetos-20261004-215542.db`. Comparação de todas as colunas anteriores confirmou preservação dos dados em usuários, produtos, espécies, projetos, orçamentos, pedidos, financeiro, agenda, imagens, movimentações, eventos, documentos e progresso.

## Cadastros comerciais e precificação

- Fornecedores ocupa a posição acima de Clientes, substituindo Produtos no menu. Cadastro de produtos permanece em Estoque, com fornecedor, marca, variação, código de barras, unidade e formação de preço.
- Códigos automáticos, identidade normalizada de produtos, prevenção de documentos/e-mails/códigos duplicados e inativação de fornecedores preservando vínculos. Cadastro comercial de cliente com senha opcional e acesso ao portal condicionado à sua existência.
- Cálculo de preço no servidor e prévia na interface: custo, margem sobre custo, alíquotas configuráveis por regime, PIS/COFINS sobre base sem ICMS no modo detalhado e IPI por fora. Rejeita combinações incompatíveis, taxas negativas e carga de 100% ou maior. Valores manuais e todos os preços antigos preservados.
- Estoque com saldos, referência, origem e destino; conta a pagar opcional vinculada à compra; idempotência, concorrência, bloqueio de saída sem saldo e reversão integral em falha financeira. Pedidos/cancelamentos também registram os saldos.
- Auditoria privada registra responsável, criação, edição, inativação, entrada e saída. Importação CSV/XLSX reutiliza as mesmas regras e permanece integralmente transacional.
- 33 testes de backend aprovados. Os 11 fluxos de navegador anteriores foram aprovados com Fornecedores no menu, inclusive layout em 1672 × 941, 1366 × 768 e 1024 × 768. Um novo fluxo completo foi aprovado: criar fornecedor, formar preço com impostos, persistir edição, lançar compra com conta a pagar, cadastrar cliente sem senha e consultar auditoria.
- Migrações `7360d6abb529` e `d4278ee1024a`; backup em `.local/backups/antes-cadastros-comerciais-20261004-225954.db`. Em uma cópia descartável, comparação de **todas as colunas anteriores** após upgrade confirmou dados preservados, `foreign_key_check` e `integrity_check` válidos e manutenção dos CHECKs de saldo, preço e lançamento. Downgrade e reaplicação também validados somente nessa cópia. PostgreSQL continua sem execução local.
- A extensão da demonstração cria seis fornecedores fictícios, identificados nas observações, sem inventar CNPJ nem contatos e sem substituir valores comerciais existentes.

## Revisão geral · 05/10/2026

- Checkout com identificador por tentativa de compra e teste de repetição concorrente: apenas um pedido, uma conta e uma baixa. Total excessivo é rejeitado sem alterar estoque.
- Pagamento e cancelamento usam o mesmo bloqueio do pedido; teste simultâneo confirma somente um resultado vencedor e estado consistente do financeiro e estoque.
- Consumo administrativo vinculado a projetos em execução/manutenção; custo unitário histórico, custo parcial explícito quando ausente, controle de saldo e acesso negado ao cliente para custos internos.
- Orçamento rejeitado não pode ser reaberto pelo preço, espécies selecionadas são validadas e novas solicitações exigem cliente/serviço ativo.
- Distribuição de centavos na composição dos impostos mantém valores não negativos e soma exata. Upload corrige orientação EXIF e arquivos ausentes retornam 404.
- Sessão expirada remove dados/token e informa o novo login; consultas antigas são canceladas, paginação acompanha páginas avançadas, foco do modal considera controles visíveis, falha inicial de conexão permite nova tentativa e erros de renderização têm tela de recuperação.
- Migração `e118c5d02005` testada na cópia do banco, preservando **todas as colunas e registros anteriores**, com integridade e referências verificadas e `alembic check` sem diferenças. Backup apontado por `.local/latest-review-backup.txt`.
- Testes de navegador: **15 aprovados**, incluindo projeto/consumo, sessão e paginação, além dos fluxos anteriores e validação de cards em 1672 × 941, 1366 × 768, 1024 × 768 e celular. Build TypeScript/Vite aprovado.
- O CI passa a verificar lint e as migrações em bancos vazios SQLite e PostgreSQL. Essa configuração não foi executada remotamente nesta revisão; PostgreSQL e Docker continuam sem execução local.

## Tabelas, cadastros e realidade demonstrativa

Atualização do portal e paisagismo: cards de serviços com conteúdo completo e detalhes de escopo/entregas/documentos, ofertas virtual/presencial, planejador 2D com importação CSV/JSON, fotos/PDFs privados e cópia do levantamento para o projeto aprovado. Migração `f80510c00001` validada em cópia do banco preservando todas as colunas/registros anteriores; `alembic check` sem diferenças e integridade/referências válidas. Backup apontado por `.local/latest-landscape-backup.txt`. Testes de backend verificam geometria, espécie, proprietário, revisão, proposta/aprovação e documentos herdados sem cópia. Navegador verifica o ciclo completo de importação → solicitação → aprovação → projeto → download do PDF, além dos limites do hero/cards em 1852 × 964, 1366 × 768 e 390 × 844. Arquivos inválidos não interrompem o planejador. O banner e a composição lateral preservam a frase inteira; o desenho no projeto possui opção de ampliação. Escopo e referências em [PAISAGISMO-VIRTUAL.md](PAISAGISMO-VIRTUAL.md).

Validação dessa etapa: **53 testes de backend aprovados**, suite anterior completa com **22 testes de navegador aprovados**, além de verificação adicional de importação inválida e nova execução dos quatro fluxos de paisagismo após o encaixe final da planta. Build e lint aprovados. Banco local: oito serviços disponíveis, zero erros/avisos de coerência, integridade válida e nenhum registro anterior perdido.

Atualização do filtro de plantas: Estoque, Loja e Biblioteca usam a mesma classificação calculada pela API a partir dos usos, família e nome cadastrados. As 40 espécies possuem pelo menos um grupo; o catálogo oferece Cactos, Frutíferas, Suculentas, Flores, Folhagens, Aromáticas e temperos, Palmeiras, Samambaias, Trepadeiras, Cercas vivas e Ornamentais. Os grupos podem se sobrepor. Espécies novas sem classificação conhecida aparecem em Outras plantas. Dois testes de backend e quatro verificações de navegador/layout aprovados, além do build. Nenhum saldo, preço ou registro comercial foi alterado.

- Colunas redundantes retiradas das listagens; tabela fixa com largura do card e texto em uma linha. SKU aparece junto ao produto; contatos e endereços ficam nos perfis; movimentações e consumo possuem botão de detalhes. As exportações conservam os campos completos. Testes verificam `scrollWidth <= clientWidth` nas tabelas administrativas de 1672, 1366 e 1024 px.
- Vendas por categoria agora usa barras comparativas, unidades e percentuais, com acesso ao filtro de categoria do estoque. Períodos: mês, ano, últimos 30 dias e intervalo personalizado. O gráfico e o restante do dashboard usam o mesmo período; a categoria da venda nova é registrada como histórico no item do pedido.
- Dados complementares de **10 clientes, 6 fornecedores e 46 produtos demonstrativos**: documentos/contatos de teste identificados nas observações, marca, apresentação, custo e código interno. Dados particulares e campos já preenchidos não foram substituídos. NCM e alíquotas fiscais não foram inventados.
- Oito descrições genéricas de orçamento foram adaptadas ao serviço solicitado. Vinte compromissos da semana atual foram acrescentados, preservando os anteriores e sem sobreposição de responsável/horário. Um orçamento aprovado sem vínculo ganhou seu projeto correspondente, copiando cliente, área, endereço, orçamento e planejamento.
- A origem das 54 unidades da base anterior foi confirmada: **18 pedidos exclusivamente de plantas**. Cinco pedidos demonstrativos adicionais completam as outras categorias, com movimento de estoque e conta a receber paga, todos vinculados. No banco local, o ano passa a conter **79 unidades: Plantas 54, Vasos 12, Substratos 2, Fertilizantes 6, Ferramentas 4 e Acessórios 1**. Esses números são derivados dos pedidos, não fixados no gráfico.
- **Relatórios → Consistência dos dados** confere saldos por movimentação, valores dos itens/pedido/conta, cliente e cancelamento, projeto de orçamento aprovado e conflitos de agenda. A conferência local registrou **zero erros e zero avisos** em 46 produtos, 23 pedidos, 10 orçamentos e 40 compromissos. Resultado salvo em `.local/data-coherence.json`.
- Complementação e vendas são executadas uma única vez mediante marcadores de versão da demonstração. Pedidos, contas, compromissos e projetos anteriores foram preservados; as novas saídas de estoque correspondem às vendas acrescentadas. Backup prévio: arquivo apontado por `.local/latest-demo-details-backup.txt`.
- **46 testes de backend aprovados**, incluindo idempotência da complementação, vendas ligadas a estoque/financeiro, categoria histórica, projeto de orçamento aprovado e detecção de divergências pelo diagnóstico. Build TypeScript/Vite aprovado.
