# Rafinha — relatório da fase oficial, 07/10/2026

## Resumo da implementação

O projeto existente foi mantido. A auditoria examinou os módulos reais do backend, frontend, providers, testes, scripts e referências. As mudanças completam o Rafinha preservando o logo, o personagem, os cadastros e os fluxos comerciais.

| Área | O que já existia | Resultado |
|---|---|---|
| Gestão | Loja, estoque, clientes, fornecedores, pedidos, financeiro, serviços, orçamentos e projetos | Preservados e cobertos pelos testes gerais |
| Conversa | Memória JSON, histórico privado e contexto autorizado | Extração duplicada consolidada; apartamento e nomes genéricos deixam de virar espécies |
| Respostas | Ollama, ChatGPT opcional, API pessoal, texto progressivo e fonte da resposta | Preservados; parágrafos, destaques e listas apresentados com elementos próprios |
| Personagem | Oito imagens recriadas e aliases de estados | Doze recortes oficiais extraídos diretamente da folha fornecida |
| Posição | Personagem fora do painel, à esquerda e no meio | Composição dentro da conversa, na parte inferior esquerda, junto ao input |
| Balão | Ponta associada ao painel inteiro | Resposta atual à direita, com ponta calculada pela âncora da boca |
| Expressões | Reações básicas e algumas informações de cultivo | Estados oficiais, contexto anterior, eventos, resultados do sistema e negações |
| Integração | Produto, preço, serviços, agenda e projetos | Resumo de estoque, mínimo por permissão, projetos em andamento/atrasados e agenda de hoje/semana |
| Segurança | Autorização, DPAPI, PKCE, scopes e credenciais privadas | Mantidos; consultas operacionais privadas continuam locais |

Foi corrigido um segundo extrator que aceitava “planta” e “apartamento” como nomes. A recuperação de serviços também substituía resultados de consultas de projetos; esses resultados agora são preservados. Pedir para planejar um jardim e consultar um projeto existente são intenções distintas. O teste de categorias aguarda as opções carregarem antes de verificá-las.

## Expressões do Rafinha

Original: `C:\Users\leand\Downloads\Espressões do Rafinha.jpeg`. Cópia preservada: `C:\Projetos\GreenScape\docs\referencias\rafinha\Espressões do Rafinha.jpeg`. Os dois arquivos têm SHA-256 `fa375521d5707da052379d4c69c1598ff7455c47d6f2d3c742c6e4149bf28d89`.

Pasta: `C:\Projetos\GreenScape\frontend\public\rafinha\official`.

| Nº | Asset | Função |
|---|---|---|
| 01 | `rafinha_happy.webp` | Agradecimento, melhora e interação positiva |
| 02 | `rafinha_sad.webp` | Perda relatada; sem uso para falha técnica |
| 03 | `rafinha_serious.webp` | Atenção a um procedimento que pode prejudicar a planta |
| 04 | `rafinha_angry.webp` | Reação inicial rara a uma ação prejudicial planejada, mantendo respeito |
| 05 | `rafinha_thinking.webp` | Interpretação, dúvida, processamento e pesquisa |
| 06 | `rafinha_sleepy.webp` | Conversa noturna contextual; sem representar lentidão |
| 07 | `rafinha_greeting.webp` | Recepção e estado normal escolhido |
| 08 | `rafinha_surprised.webp` | Informação inesperada ou frequência exagerada relatada |
| 09 | `rafinha_shy.webp` | Elogio amistoso; sem comportamento romântico |
| 10 | `rafinha_skeptical.webp` | Informação contraditória; sem acusar o cliente |
| 11 | `rafinha_delighted.webp` | Floração e satisfação |
| 12 | `rafinha_celebrating.webp` | Recuperação contextual e conclusão/aprovação relatada ou verificada |

Os recortes utilizam os pixels da folha, sem uma nova ilustração. `scripts/extrair_expressoes_rafinha.py` remove o fundo claro conectado ao perímetro, separa contornos que encostam em poses vizinhas e conserva os símbolos. Áreas claras internas, como a camisa, são protegidas pelo contorno.

WebP lossless com alpha real; canvas comum de **320 × 400**, escala uniforme e boca em **50% da largura e 52,5% da altura**. O conjunto ocupa **1.124.918 bytes**, cerca de 1,07 MiB. `manifest.json` registra nomes, coordenadas, âncora, margens e hash. As oito imagens anteriores foram mantidas para compatibilidade; a interface utiliza as doze oficiais.

Reproduzir os recortes:

```powershell
cd C:\Projetos\GreenScape
.\.venv\Scripts\python.exe .\scripts\extrair_expressoes_rafinha.py
```

## Interface do Rafinha

`RafinhaCharacter` conserva a imagem ativa e a anterior numa transição de 260 ms. O canvas e a âncora compartilhados evitam saltos. A reação inicial tem pelo menos 750 ms; pensar entra após 800 ms apenas se o processamento continuar. A resposta aparece assim que chega. O retorno normal conserva o tempo anterior de sete segundos após a apresentação.

O personagem ocupa espaço próprio em grid, na base esquerda da conversa. A resposta atual fica à direita e as mensagens anteriores têm rolagem. O balão cresce até o limite e permite ler respostas longas. Campo, enviar e upload continuam abaixo da composição.

O rabicho usa a metade da largura do personagem e 47,5% da altura medida a partir da base. Isso corresponde à boca normalizada e funciona mesmo com balão mais alto. O teste admite menos de dois pixels de diferença entre ponta e âncora.

Desktop: 128 × 160. Mobile: 84 × 105, mesma relação de âncora, sem sobrepor o input. Movimento reduzido desativa a troca animada. Há descrição alternativa e o texto mantém a informação principal.

O texto progressivo ajusta caracteres por quadro para terminar em aproximadamente 2,4 segundos em respostas longas. “Mostrar resposta completa” permanece disponível. Parágrafos, listas e destaques são renderizados por React com escapamento, sem HTML executável.

## Arquivos

Criados nesta fase:

- `frontend/src/RafinhaCharacter.tsx`.
- `frontend/public/rafinha/official/`: doze WebP e manifesto.
- `scripts/extrair_expressoes_rafinha.py`.
- `backend/tests/test_rafinha_official.py`.
- Este relatório.

Alterados/consolidados:

- `frontend/src/RafinhaAssistant.tsx`, `rafinhaExpressions.ts`, `rafinha.css`.
- `backend/app/assistant_state.py`, `assistant_language.py`, `assistant_emotions.py`, `assistant_engine.py`.
- `frontend/tests/rafinha.spec.ts`, `plant-groups.spec.ts` e testes anteriores de linguagem/conversa.
- `README.md` e documentação dos assets.

`RafinhaMessageText.tsx`, providers e conexão pessoal da etapa anterior foram aproveitados. Nenhum endpoint, módulo comercial ou asset anterior foi removido. Não houve nova dependência nem migração: Pillow já existia, e os campos de memória usam o JSON atual.

## Contexto, roteamento e prevenção de repetições

A memória mantém planta informada, espécie confirmada do catálogo, opções de identificação, objetivo do cuidado, ambiente, luz, rega, sintomas, perguntas feitas e informações desconhecidas. A pergunta pendente guarda sua formulação: “sim” pode responder a uma pergunta específica sobre sol direto, mas não escolhe entre sol, claridade e pouca luz.

Nomes, apposições e pronomes passam pelo mesmo parser. “Tenho uma planta, uma roseira” reconhece a roseira. “Não sei o nome da flor” não vira uma espécie chamada flor. Mudança de planta limpa pistas anteriores. O modelo recebe memória e até dez mensagens relevantes. Fechar o diálogo elimina a sessão ativa, conforme a preferência anterior.

Os registros autorizados são a primeira fonte para informações do sistema. Estoque, preço, agenda e projetos são consultados naquele momento. Saudações e perguntas simples não fazem pesquisa por rotina. Relatos de sintomas podem começar pelo contexto; atualidades, assuntos específicos ausentes e pesquisa explícita passam pela decisão de busca.

O motor visual considera intenção, sintomas atuais/negados, frequência relatada, necessidade de água cadastrada, expressão anterior e resultados verificados. Palavras ajudam, mas não determinam sozinhas a reação. Resposta, expressão, fonte, confiança e metadata permanecem separados.

## Inteligência artificial

**Ollama:** execução local sem cobrança por requisição. Nesta máquina: `qwen3:0.6b`; o `qwen3:4b` permanece instalado. Preparação em segundo plano e tratamento de modelo ausente, serviço parado, timeout e resposta inválida. Um modelo pequeno tem limitações; não há promessa de equivalência a modelos maiores.

**ChatGPT:** preservado o login oficial com PKCE, loopback, identidade/scopes, catálogo e renovação. A autorização prepara o modelo; o plano escolhido pelo usuário tem prioridade. Documentação atual conferida: [registro](https://developers.openai.com/siwc/token-sharing-open-source/sign-in), [streaming](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference), [limitações](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations). A elegibilidade depende da conta e da autorização da OpenAI.

**OpenAI API:** opção avançada, desativada até configuração/ativação da chave pessoal, com faturamento separado. Falha do ChatGPT não escolhe outra chave paga. O limite de consultas é salvo sem trocar modelo ou autorização.

**Pesquisa web:** índice institucional, destinos validados, cache de informações pouco voláteis e fontes verificadas. SearXNG público pode ampliar a descoberta. Dados comerciais atuais não usam esse cache. Falta de fonte recente não gera um alerta inventado.

## Fallback

Os dados do GreenScape funcionam sem modelo. O provider escolhido tenta responder no orçamento; falha, limite, falta de autorização ou resposta incompleta permitem a alternativa local e depois a resposta guiada. Somente conclusão terminal OpenAI é aceita; deltas compõem o texto quando o evento final não repete o conteúdo. A interface indica o mecanismo real da resposta.

O orçamento permanece em oito segundos de processamento dentro da meta de dez para entrega. Não há sequência obrigatória chamando todos os serviços nem pausa artificial para expressões.

## Segurança

Propriedade e permissões são verificadas antes de usar projeto, orçamento, conversa ou foto. Estoque mínimo é administrativo; agenda/projetos de clientes são filtrados pelo dono. Consultas operacionais privadas permanecem locais.

No Windows, tokens e chaves ficam fora do projeto, em `%LOCALAPPDATA%\AtelieVerde\Rafinha`, cifrados com DPAPI e separados pelo usuário do portal. Senhas, cookies e tokens manuais não são solicitados. Segredos não vão ao frontend nem aos logs. `.env`, ambientes, módulos, builds, dados locais e logs são excluídos do Git.

## Configurações externas

Ollama, modelo e conexão pessoal existentes foram preservados. Nenhuma nova conta ou chave é obrigatória para usar os recursos locais. Em outra máquina, instalar/iniciar Ollama e baixar o modelo, ou usar o modo guiado. ChatGPT exige autorização da própria conta no navegador; API e SearXNG precisam de configuração somente se forem desejados.

## Testes realizados

- **309 testes gerais do backend aprovados**, com verificações adicionais das revisões finais também aprovadas.
- **34 testes de navegador aprovados**, incluindo operações comerciais, portal, paisagismo, relatórios e onze cenários do Rafinha.
- Doze poses trocadas programaticamente: transparência, canvas, posição, margens e peso dos arquivos aprovados.
- Ponta por coordenadas em desktop/mobile; resposta longa, input, scroll, movimento reduzido e sobreposição cobertos.
- TypeScript/Vite e Ruff aprovados.
- Banco real somente lido: SQLite `ok`, nenhuma violação de chave estrangeira e nenhum erro/alerta comercial. 61 produtos, 28 pedidos, 11 orçamentos e 40 compromissos.
- Provider ausente, timeout, erro, resposta incompleta, quota, desconexão, privacidade e pesquisa falhando usam transporte controlado e banco temporário.
- Nesta fase não enviei novas consultas generativas pela conta real nem usei chave paga. O teste real anterior confirmou ChatGPT em 2,75 e 5,25 segundos.

Permanece um aviso de depreciação Starlette/httpx nos testes, sem impedir a execução. As regressões e a corrida de carregamento encontradas nas primeiras rodadas foram corrigidas antes dos resultados acima.

## Como iniciar no Windows

Backend e frontend juntos:

```powershell
cd C:\Projetos\GreenScape
.\scripts\iniciar.ps1 -NoBrowser
```

Portal: `http://127.0.0.1:5173`. API: `http://127.0.0.1:8015/docs`. Parar: `.\scripts\parar.ps1`.

Execução separada, em dois terminais:

```powershell
cd C:\Projetos\GreenScape
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8015
```

```powershell
cd C:\Projetos\GreenScape\frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Ollama, quando o aplicativo Windows não estiver servindo a porta 11434:

```powershell
ollama serve
```

Em outro terminal:

```powershell
ollama pull qwen3:0.6b
ollama list
ollama run qwen3:0.6b
```

Variáveis utilizadas em `.env`:

```env
RAFINHA_PROVIDER=auto
RAFINHA_OLLAMA_URL=http://127.0.0.1:11434
RAFINHA_OLLAMA_MODEL=qwen3:0.6b
```

Verificações reproduzíveis:

```powershell
cd C:\Projetos\GreenScape
.\.venv\Scripts\python.exe -m pytest backend/tests -q --tb=short -p no:cacheprovider
.\.venv\Scripts\ruff.exe check backend/app/assistant_*.py scripts/extrair_expressoes_rafinha.py
cd C:\Projetos\GreenScape\frontend
npm.cmd run build
npx.cmd playwright test
```

## Próximos passos e limites reais

A fase de conversa, expressões oficiais e composição visual está implementada e disponível localmente.

Análise automática de fotos é uma evolução opcional: upload privado e contexto estão preparados, mas a identificação atual utiliza descrição e referências, sem prometer visão ou certeza. Busca mais ampla exige endpoint configurado. Instalador/executável e IA paga gerenciada pela empresa permanecem fora desta fase; não foram simulados nem distribuídos com credenciais pessoais.
