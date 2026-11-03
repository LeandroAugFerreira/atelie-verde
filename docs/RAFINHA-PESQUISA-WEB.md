# Rafinha — pesquisa web real

Implementação em 7 de outubro de 2026, mantendo a interface e as 12 expressões oficiais.

## Causa do estado anterior

A instalação utilizava `WEB_SEARCH_PROVIDER=institutional`. Esse provider descobre fichas por um sitemap botânico; exige um nome utilizável e não é um mecanismo amplo para apelidos, descrições ou alertas atuais. `WEB_SEARCH_URL` estava vazio, portanto não havia servidor SearXNG configurado. A conversa com ChatGPT funcionava, mas as requisições não disponibilizavam uma ferramenta de pesquisa ao modelo.

## Funcionamento

A decisão considera intenção, evidência interna, pistas de identificação, necessidade de atualidade, temas sensíveis, pedido explícito e contexto. Cumprimentos, identidade, produtos, preços, estoque, serviços e agenda não usam a ferramenta web. Relatos simples de rega/luz também não pesquisam por padrão. Pistas novas de identificação, toxicidade, defensivos, pragas específicas e informações atuais podem justificar pesquisa. Pedidos explícitos são atendidos quando a pesquisa está habilitada; consultas privadas do sistema não são enviadas à ferramenta.

Quando a conexão pessoal está habilitada e permite pesquisa, uma requisição à Responses API pode pesquisar, ler resultados e produzir a resposta final. Não encadeia busca institucional, pesquisa OpenAI e todos os modelos. Em falha da pesquisa, o atendimento local continua, sem tentar outra conta paga. Sem conexão pessoal, a pesquisa institucional já existente continua disponível dentro de seus limites.

A ferramenta só é adicionada quando necessária e autorizada. A integração usa `POST https://api.openai.com/v1/responses`, `web_search`, metadados de fontes e, nas identificações, resultados de imagens. Mantém o token/chave pessoal, a cota diária, cancelamento, `store:false`, transmissão de resposta e uma única janela de tempo. Requisições com chave de API limitam a uma chamada de ferramenta; a conexão ChatGPT omite esse parâmetro por exigência da documentação. Nela, a instrução pede preferencialmente uma busca bem formulada, e o número de operações internas depende do modelo.

Há preferência por fontes institucionais e técnicas sem excluir automaticamente boas fontes especializadas. O modelo sintetiza as evidências e mantém incerteza. Não é um diagnóstico automático nem confirmação botânica por texto.

## Contexto e fontes

O nome científico candidato é guardado separadamente, como `identity_hypothesis.status=hypothesis`. A hipótese não vira `species_id` nem altera o catálogo. A síntese pesquisada e suas fontes ficam na memória privada da conversa; a próxima mensagem aproveita esse contexto. Declarar outra planta limpa a hipótese anterior. Relatos de deterioração não são apagados apenas porque uma mensagem posterior contém a palavra “não”.

Títulos, URLs e domínios vêm dos metadados da ferramenta. Links escritos livremente pelo modelo não são aceitos como comprovação. Citações aparecem como referências numéricas clicáveis no texto; a lista completa fica em “Fontes consultadas”. URLs inseguras são descartadas e parâmetros comuns de rastreamento são removidos. Fontes reutilizadas na conversa não são apresentadas como uma nova pesquisa.

## Imagens

Somente nas identificações, e com a opção ativada, são solicitados resultados de imagem. A galeria mostra até três thumbnails com origem clicável e proporção uniforme; adapta-se à largura disponível com rolagem horizontal. Não gera nem inventa imagens e não identifica a foto do cliente. Ausência de resultados não impede a resposta textual. Imagens remotas são exibidas a partir da URL retornada, com `referrerPolicy=no-referrer`; não são copiadas para o projeto.

No primeiro teste real a ferramenta retornou texto e fontes, sem imagens. A leitura dos metadados de imagem e a galeria foram verificadas com resultados simulados. O suporte efetivo depende do modelo e da política da conta.

## Ativação e configuração externa

Abra o Rafinha → preferências → **Pesquisa na internet**. Use **Ativar pesquisa web**, escolha **Automaticamente quando fizer sentido** ou **Somente quando eu pedir** e, se desejar, habilite imagens. As alterações são salvas automaticamente. Em preferências avançadas, escolha respostas de até 10 ou 30 segundos. Fechar as preferências também salva alterações pendentes.

Nesta instalação, a conta ChatGPT já conectada foi configurada para busca automática e até 30 segundos, conforme a escolha do usuário. Modelo, limite diário e credenciais foram preservados. A pesquisa real funcionou nessa conta sem `OPENAI_API_KEY`. A autorização da ferramenta depende do modelo e da política da conta/workspace.

Para usar uma chave de API, abra **OpenAI API · configurações avançadas**, informe sua própria chave, verifique-a, selecione um modelo liberado e ative sua API. Depois habilite pesquisa. A API e a ferramenta podem ter cobrança separada do plano ChatGPT. Não existe mudança automática para uma API paga nem uma chave da empresa embutida.

Não é necessário criar `OPENAI_API_KEY` no `.env`: esta integração usa o cofre pessoal já existente, separado por usuário, protegido no Windows por DPAPI, fora dos arquivos do projeto. Nunca coloque uma chave no frontend, em código ou em arquivos versionados. Configurar conexão, limites e pesquisa exige acesso pela instalação local.

Sem conta/chave pessoal, Ollama e o catálogo continuam funcionando. Para busca ampla externa pelo provider SearXNG já existente, é necessário fornecer um servidor HTTPS público com JSON habilitado; esse servidor não foi configurado nem simulado nesta fase.

## Arquivos criados

- `backend/app/assistant_observations.py`: grupos de plantas e relatos de cuidados separados da identidade.
- `backend/app/assistant_web_search.py`: decisão de pesquisa, configuração da ferramenta, leitura de fontes/imagens e validação de URLs.
- `backend/tests/test_assistant_observations.py` e `backend/tests/test_assistant_web_search.py`: famílias de regressão e protocolo da pesquisa.
- `frontend/src/SearchImageGallery.tsx`: galeria com origem e validação de links.
- `docs/RAFINHA-PESQUISA-WEB.md`: configuração e evidências desta etapa.
- `docs/screenshots/rafinha-pesquisa-desktop.png` e `rafinha-pesquisa-mobile.png`: conferência visual da resposta real previamente obtida, sem nova consulta de IA.

## Arquivos alterados

- Backend: `assistant.py`, `assistant_ai.py`, `assistant_budget.py`, `assistant_connections.py`, `assistant_emotions.py`, `assistant_engine.py`, `assistant_knowledge.py`, `assistant_language.py`, `assistant_openai.py`, `assistant_provider.py`, `assistant_routing.py` e `assistant_state.py`.
- Testes backend: `test_personal_ai.py`.
- Frontend: `RafinhaAssistant.tsx`, `RafinhaConnection.tsx`, `RafinhaMessageText.tsx`, `rafinhaExpressions.ts`, `rafinha.css` e `tests/rafinha.spec.ts`.
- `README.md`.

Não houve migração nem alteração de dados comerciais. Imagens oficiais do Rafinha foram preservadas. Scripts locais de verificação e registros sanitizados ficam em `.local`, que já é ignorado pelo Git; as conversas reais de teste foram excluídas ao terminar.

## Teste manual

1. Abra a demonstração Cliente e o Rafinha.
2. Confira busca automática nas preferências.
3. Envie “Olá”: não deve pesquisar.
4. Envie “Tenho uma planta que está morrendo e não sei o que fazer”.
5. Envie “eu só sei que é uma suculenta, parece com a orelha do Shrek”: deve consultar fontes e sugerir uma identificação provável, sem certeza artificial.
6. Envie “eu não deixei ela no sol e reguei muito”: deve continuar os cuidados, preservar a hipótese e demonstrar preocupação.
7. Teste modo somente quando pedir, desative pesquisa e recarregue: a preferência deve permanecer salva. Use “Pesquise essa planta para mim” no modo de pedido explícito.

O teste real dessa sequência retornou hipótese de *Crassula ovata* ‘Gollum’, fontes institucionais e citações em 11,72 segundos. A resposta seguinte levou 6,25 segundos e não realizou nova pesquisa. O cumprimento foi respondido internamente. Foram utilizadas três consultas da cota da conexão nessa validação, sem API paga alternativa.

## Verificação automatizada

```powershell
cd C:\Projetos\GreenScape
.\.venv\Scripts\ruff.exe check backend/app backend/tests
.\.venv\Scripts\python.exe -m pytest backend/tests -q --tb=short -p no:cacheprovider
cd frontend
npx.cmd playwright test tests/rafinha.spec.ts
npm.cmd run build
```

Os testes cobrem roteamento, pedido explícito, controles persistentes, conexão/API desativada, falha HTTP, falta de internet, metadados de fonte, imagens, URLs inseguras, restrição a acesso local, histórico privado, hipótese contextual, atendimento urgente e layout em desktop/mobile. São executados em dados e credenciais temporários, com respostas externas simuladas, sem gastar consultas reais.

Resultado: **366 testes backend e 13 testes do Rafinha no navegador aprovados**. Ruff e build de produção aprovados. Após ajustar o indicador durante a pesquisa, os 36 testes específicos da ferramenta também passaram. A resposta real foi conferida visualmente em desktop e celular. O único aviso backend foi a depreciação já existente de Starlette/httpx; não houve falhas finais.

## Documentação oficial consultada

- [Web search na Responses API](https://developers.openai.com/api/docs/guides/tools-web-search).
- [Inferência com a conexão ChatGPT](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).
- [Limites atuais da conexão ChatGPT](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations).

Não foram utilizados endpoints privados do ChatGPT, APIs depreciadas de pesquisa nem automação da página de login para obter cookies.
