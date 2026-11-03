# Auditoria do Rafinha e restauração das referências visuais

## Conclusão

O Rafinha não é uma cópia exata do aplicativo ChatGPT com o nome alterado. É uma interface própria que pode conversar com um modelo OpenAI por meio da conta ChatGPT autorizada. O projeto acrescenta instruções, recuperação de dados, regras de acesso, limites, memória própria e uma alternativa de catálogo. Essas camadas explicam diferenças de comportamento.

A instrução mais recente foi recuperar a experiência em que uma descrição como “suculenta, parece a orelha do Sherek” produzia uma hipótese de identificação, explicação, fontes e imagens. Esse comportamento foi restaurado no fluxo da conta ChatGPT, sem ativar Ollama, Tavily ou uma API paga alternativa, e sem desfazer os ajustes de interface e expressões.

## O que a investigação encontrou

| Ponto | Evidência | Consequência e correção |
| --- | --- | --- |
| Resposta do print | O cabeçalho mostra “Resposta guiada”; o texto de identificação existe como alternativa local no código. O log da instalação registrou `server_is_overloaded`. | A resposta do print não veio do ChatGPT. Falhas reais agora são informadas e não iniciam um questionário sobre plantas. Não é possível provar apenas pelo print se aquela falha ocorreu na instalação de desenvolvimento ou em um executável sem conexão. |
| Personalidade forçada para jardinagem | O prompt definia o Rafinha exclusivamente como assistente de jardinagem. No teste real anterior, “Boa noite, dormiu bem?” recebeu “Dormi bem, sim” e um convite para falar de plantas. | O prompt agora orienta responder ao assunto trazido, conversar naturalmente e não inventar vivências físicas. Isso foi verificado com respostas reais. |
| Desvio antes da geração | Identidade e toda a classe de intenções comerciais bypassavam o ChatGPT. | Identidade e dados públicos de produtos/preços/estoque/serviços agora podem ser respondidos pelo modelo. As consultas privadas de clientes, agenda, pedidos e projetos mantêm recuperação interna autorizada. |
| Imagens não solicitadas | A otimização recente retirou `search_content_types`, `image_settings` e `web_search_call.results`. | Os parâmetros documentados foram restaurados nas pesquisas de identificação com imagens habilitadas. Consultas de texto comuns continuam sem pedir imagens. |
| Identificação respondida sem pesquisa | A referência interna conhecida podia suprimir a pesquisa mesmo com imagens ativadas. | Quando imagens estão habilitadas, novas pistas de identificação podem novamente usar a busca com referências visuais. Com imagens desativadas, a referência interna ainda evita consultas desnecessárias. |
| Miniatura externa quebrada | A galeria escondia a imagem ao falhar o thumbnail, mesmo havendo uma imagem original válida. | A imagem original agora é tentada antes de ocultar o resultado. Legendas ausentes não aparecem como “None”. |
| Histórico e memória | Contexto recente de até 20 mensagens/20 mil caracteres, conversa própria e encerramento ao fechar. | Não existe importação das conversas, memória ou personalização do aplicativo ChatGPT. A memória de hipótese botânica foi preservada, e fechar continua encerrando a conversa conforme solicitado. |
| Modelo | Conexão selecionada com `gpt-5.6-sol`, limite pessoal de 100 consultas/dia e até 30 segundos configurados. | O modelo foi preservado. Não se pode afirmar que ele seja o mesmo modelo selecionado no ChatGPT mostrado no print. |

## Testes reais após a restauração

As respostas vieram da conta ChatGPT autorizada. As conversas usadas na verificação foram excluídas ao terminar.

| Cenário | Resultado | Tempo da resposta completa |
| --- | --- | --- |
| “Boa noite, dormiu bem?” | Respondeu cordialmente que é uma IA e não dorme, perguntando como o usuário estava; não mudou para plantas. | 2,89 s |
| “Pode corrigir esta frase: eu foi na loja ontem.” | Corrigiu para “Eu fui à loja ontem.” | 3,42 s |
| Descrição por “orelha do Sherek” | Sugeriu *Crassula ovata* ‘Gollum’ como hipótese, distinguiu uma variedade semelhante, consultou três fontes e retornou uma imagem com página de origem. | 13,92 s |
| Relato seguinte de excesso de rega | Aproveitou a hipótese anterior, manteve orientação contextual e expressão séria, sem uma nova pesquisa. | 7,55 s |

Os tempos são amostras, não garantia. “Até três imagens” é um limite máximo; no teste o provedor retornou uma referência válida. Uma descrição ou imagem não confirma sozinha espécie, cultivar ou doença.

## O que permanece diferente do ChatGPT

- O nome, as expressões, o contexto da loja e as instruções são próprios do Rafinha.
- O login fornece autorização de uso do plano elegível e modelos disponíveis; não fornece acesso às conversas ou à memória pessoal do ChatGPT.
- Pesquisa e imagens dependem da disponibilidade da ferramenta na conta/modelo. A aplicação não usa uma conta ou API paga diferente se ela falhar.
- O projeto possui limites próprios: 2 mil caracteres por mensagem, 4 mil por resposta, histórico recente limitado, orçamento de até 30 segundos e 100 tentativas diárias no perfil pessoal atual. O aplicativo ChatGPT tem seu próprio comportamento e limites.
- Nesta interface, os anexos são fotos privadas; voz é apresentação local opcional. Ferramentas como execução de código, arquivos gerais, áudio em tempo real e todas as integrações do aplicativo ChatGPT não foram implementadas aqui.
- Preços, estoque, dados privados e permissões são controlados pelo projeto. Uma conversa natural não concede permissão para consultar dados de outro cliente ou alterar registros.

## Validação técnica

- 551 testes gerais de backend/distribuição aprovados; após os ajustes finais de imagem e legenda, 78 testes do fluxo ChatGPT/pesquisa novamente aprovados.
- 17 testes de navegador aprovados, incluindo todas as 12 expressões, permanência até outra mensagem, minimizar/reabrir, privacidade de fotos e citações. O cenário de galeria foi novamente aprovado com thumbnail inválido e imagem original válida.
- TypeScript/Vite e Ruff aprovados.
- Os testes novos verificam conversa social, escrita, identidade, produtos públicos, falha real sem questionário, busca com imagens, hipótese não confirmada e continuidade sem nova pesquisa.

## Referências oficiais

- [Login ChatGPT e uso do plano em aplicações](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt): autoriza inferência elegível, sem acesso às conversas do ChatGPT.
- [Modelos e inferência](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference): o aplicativo escolhe um modelo disponível e fornece suas próprias instruções e contexto.
- [Pesquisa web e resultados de imagem](https://developers.openai.com/api/docs/guides/tools-web-search?trk=article-ssr-frontend-pulse_little-text-block): `search_content_types`, `image_settings` e metadados `web_search_call.results`.

## Entrega e conferência visual

- A imagem retornada na consulta real foi exibida na interface em navegador separado, reutilizando a resposta já concluída, sem nova chamada de IA. O navegador confirmou imagem carregada e visível. A conversa visual de teste também foi excluída.
- As referências aparecem logo depois da apresentação da hipótese, antes dos detalhes longos. A conferência final confirmou a imagem dentro da área visível da janela, sem precisar procurar a galeria no fim da resposta.
- Captura privada da conferência: `.local/rafinha-restored-image-desktop-20261011.png`.
- Pacote atualizado: `release/windows/20261011-215419/AtelieVerde-Windows.zip`.
- Scanner sem achados; 13 verificações da instalação isolada aprovadas, com zero chamadas externas. A conta do desenvolvedor não foi incorporada ao executável.
- Integridade dos 1.049 arquivos conferida contra a pasta compilada; 231.720.873 bytes.
- SHA-256: `239cab82ed11be3d7a5f3c83688d095ebb4528fd0866b1691304d6905e80bd3a`.
- O limite pessoal de 100 consultas diárias, as 12 expressões persistentes, as fotografias do catálogo e a transparência atual dos containers foram mantidos.
