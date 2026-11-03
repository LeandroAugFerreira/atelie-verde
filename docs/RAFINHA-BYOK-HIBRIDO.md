# Rafinha — arquitetura híbrida BYOK

Relatório da evolução de 8 de outubro de 2026. Esta é a configuração vigente; os documentos de conexões pessoais e pesquisa institucional anteriores descrevem etapas históricas.

## AUDITORIA INICIAL

O projeto já possuía React/TypeScript/Vite, FastAPI, SQLAlchemy, login JWT, perfis admin/cliente, dados comerciais, Ollama, memória estruturada por conversa, histórico privado, cancelamento, 12 expressões oficiais, balão, fontes e galeria. As integrações externas eram pessoais e o cliente podia configurá-las. O índice institucional dependia de um nome utilizável; não atendia bem descrições ou apelidos. A pesquisa OpenAI da etapa anterior funcionava na conexão pessoal, mas não correspondia à nova regra de instalação administrada e Tavily primeiro.

Foram preservados o banco comercial, o login, os perfis, a memória/histórico, os assets e a composição visual. Não houve migração de dados comerciais. As credenciais pessoais antigas permanecem protegidas, sem participar do roteamento automático; os endpoints legados agora exigem administrador e acesso local.

## ARQUIVOS ALTERADOS

- Backend: `assistant.py`, `assistant_ai.py`, `assistant_connections.py`, `assistant_credentials.py`, `assistant_engine.py`, `assistant_language.py`, `assistant_provider.py`, `assistant_routing.py`, `assistant_settings.py`, `assistant_web_search.py` e `main.py`.
- Testes backend: `conftest.py`, `test_personal_ai.py`, `test_assistant_web_search.py`, `test_assistant_routing.py` e `test_hybrid_assistant.py`.
- Frontend: `AdminPages.tsx`, `RafinhaAssistant.tsx`, `admin.css` e `tests/rafinha.spec.ts`.
- `.gitignore`, `.env.example`, `backend/requirements.txt` e `README.md`.

## ARQUIVOS CRIADOS

- `backend/app/assistant_installation.py`: configuração compartilhada da instalação, cofre e limites.
- `backend/app/assistant_admin_ai.py`: permissão e endpoints administrativos.
- `backend/app/assistant_search_providers.py`: Tavily/OpenAI oficiais e resultado normalizado.
- `backend/app/assistant_hybrid_search.py`: síntese local, confiança, cache e escalonamento.
- `backend/app/assistant_sensitive.py`: proteção contra credenciais no chat/fontes.
- `backend/tests/test_installation_research.py`: cenários de roteamento, segurança, concorrência e regressões.
- `frontend/src/AdminAISettings.tsx`, `rafinhaModes.ts` e `frontend/tests/admin-ai.spec.ts`.
- `packaging/launcher.py`, `AtelieVerde.spec`, `build_manifest.py` e dois arquivos de teste em `packaging/tests`.
- `scripts/gerar_exe_seguro.ps1`, `verificar_release.py`, `testar_exe_seguro.py` e `backend/requirements-build.txt`.
- Este relatório e as capturas `docs/screenshots/rafinha-admin-ai-desktop.png` e `rafinha-admin-ai-mobile.png`.

## TAVILY

O provider utiliza `POST https://api.tavily.com/search`, autenticação Bearer, pesquisa `basic`, parâmetros automáticos desligados e até cinco resultados. Solicita conteúdo estruturado, preservando título, URL, domínio, snippet, conteúdo, score, provider e data quando disponível. Dá preferência a instituições, sem excluir automaticamente boas fontes especializadas. Atualidade utiliza janela de datas; imagens são solicitadas somente quando auxiliam a identificação.

A chave é validada com `GET /usage`, sem executar uma pesquisa. Uma chave inválida não é salva como validada. São tratados autenticação, cota, timeout, resposta inválida, falta de internet e ausência de resultados. O uso informado pelo provider aparece no painel; valores monetários não são inventados.

Tavily utiliza créditos da conta cadastrada. A cota gratuita não é ilimitada; confira o plano, limite da chave e pay-as-you-go na própria conta. O aplicativo adiciona limites locais de tentativas.

Documentação consultada: [Search](https://docs.tavily.com/documentation/api-reference/endpoint/search), [Usage](https://docs.tavily.com/documentation/api-reference/endpoint/usage) e [créditos](https://docs.tavily.com/documentation/api-credits).

## OPENAI

O provider pago utiliza exclusivamente a API pública `POST https://api.openai.com/v1/responses` com `web_search`. Usa a chave BYOK da instalação, modelo escolhido entre os autorizados, `store:false`, resposta completa transmitida e limite de uma chamada de ferramenta por requisição. Fontes vêm dos metadados oficiais. O resultado é material de pesquisa para a síntese local, não uma lista de links entregue ao cliente.

Validar a chave via lista de modelos mantém `paid_search_enabled=false`. Autorizar exige checkbox e salvamento explícito pelo administrador. Remover/trocar a chave desliga a autorização; atingir limite diário ou mensal bloqueia novas tentativas. Não há mudança automática para chave do desenvolvedor, OAuth pessoal antigo ou outra conta paga.

Documentação consultada: [OpenAI Web Search](https://developers.openai.com/api/docs/guides/tools-web-search). Não foram utilizados endpoints privados do ChatGPT, cookies nem engenharia reversa.

## OLLAMA

Ollama continua como mecanismo local principal. Conversa usando memória e dados internos; na pesquisa, recebe evidências normalizadas e devolve resposta contextual, avaliação de suficiência, concordância/divergência e candidato científico quando sustentado pelas fontes. Chaves não são enviadas ao modelo.

Respostas locais repetidas ao receber novos fatos de problema são rejeitadas em favor de orientação local pertinente. Perguntas sugeridas não são apresentadas ao modelo como fatos da planta. Regas esquecidas com murcha usam orientação interna prudente, sem inventar umidade ou frequência. A família “esqueci de regar e ela…” não é tratada como uma nova planta. O modelo disponível na instalação é `qwen3:0.6b`; a qualidade linguística depende do modelo/hardware. O `qwen3:4b` instalado não concluiu a síntese em duas medições limitadas a 20 segundos, portanto a configuração atual foi mantida. O código não baixa modelos.

## ROTEAMENTO

1. GreenScape, memória e conhecimento local são consultados primeiro. Cumprimentos, preços, estoque, serviços, clientes, projetos e agenda não pesquisam.
2. Pistas de identificação, falta de informação botânica, toxicidade, pragas específicas, atualidade ou pedido explícito podem justificar internet.
3. Tavily é a primeira pesquisa. Ollama avalia as fontes e sintetiza.
4. Só se houver insuficiência concreta, divergência ou verificação importante e autorização administrativa, OpenAI acrescenta evidência.
5. Ollama compara os resultados; URLs são deduplicadas. Não chama Tavily e OpenAI simultaneamente por padrão.

HIGH exige fontes independentes confiáveis, relevância, suficiência e concordância na avaliação local. Contagem de links sozinha não produz HIGH. Identificação por descrição permanece hipótese, com confiança limitada; fontes sem datas não confirmam informação atual. Divergências são ressalvadas na resposta.

Cache evita repetir pesquisa. Tentativa paga falhada também recebe marcador temporário para impedir repetir gasto imediatamente ao repetir a mesma pergunta. Referências positivas comuns têm cache de 24 horas; atualidade, 15 minutos; falha/inconclusão, cache curto de 5 minutos. Cache não altera dados da loja.

## BYOK

Cada instalação configura suas próprias contas. Uma instalação nova não contém chave Tavily/OpenAI e não autoriza pesquisa paga. O cliente conversa, recebe fontes e consulta dados permitidos; configurar providers ou custo é responsabilidade exclusiva do administrador.

## SEGURANÇA

Credenciais ficam em `%LOCALAPPDATA%\AtelieVerde\Rafinha`, protegidas por DPAPI do usuário Windows, fora do projeto, SQLite, frontend e pacote. DPAPI é o equivalente seguro escolhido, reaproveitando a implementação existente sem biblioteca desnecessária. Depois de salvar, somente máscara e últimos três caracteres são retornados ao administrador. O cliente não recebe essa configuração.

Limites e alterações compartilhadas usam lock entre threads e processos. Testar uma credencial verifica a geração antes de atualizar o cofre: remoção/substituição concorrente não restaura a chave antiga. Remover uma chave também impede que o fallback de ambiente a reative.

Chaves/tokens reconhecidos colados no chat são rejeitados antes da gravação; conteúdo pesquisado é redigido para não propagar credenciais. Erros de validação administrativa não devolvem valores sensíveis. Logs não registram headers de autenticação ou chaves.

O desenvolvimento pode usar variáveis locais somente com `RAFINHA_ALLOW_DEV_API_KEYS=true`. Elas precisam de validação administrativa e são ignoradas pelo executável. `.env.example` contém campos vazios; `.env`, `.env.*`, cofres, build/dist/release, logs e dados privados são protegidos por `.gitignore`.

O build usa allowlist de recursos públicos, verifica alterações durante compilação, inspeciona arquivos e conteúdo compilado descomprimido e compara segredos locais sem imprimi-los. O release validado não inclui `.env`, SQLite do desenvolvedor, uploads, logs ou cofre. O executável gera sua própria sessão protegida fora do pacote. Não possui assinatura digital; isso é distinto da verificação de segredos.

Referência: [CryptProtectData / DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).

## PORTAL ADMINISTRATIVO

Local: **Administrador → Configurações → Inteligência Artificial**. Permissão equivalente: `MANAGE_AI_SETTINGS`, vinculada ao perfil administrativo existente e acesso pela instalação local. GET/PUT/POST/DELETE administrativos, configuração legada e encerramento do EXE recusam cliente com 403.

O painel apresenta saúde/modelo Ollama, validação/alteração/remoção de chaves, política, modelo pago, imagens, tempo de resposta, limites e uso da instalação. Campo de chave é temporário, fica vazio após envio e não é persistido em armazenamento do navegador.

## CONTEXTO DO RAFINHA

A pesquisa alimenta `research_context` e `identity_hypothesis`, separados da identificação confirmada. O exemplo “suculenta, parece orelha do Shrek” pode gerar possível *Crassula ovata* ‘Gollum’, com fontes; não altera `species_id` ou o catálogo. O relato seguinte de excesso de rega reaproveita a hipótese e os sintomas sem recomeçar a conversa nem pesquisar novamente sem motivo.

Falta de sol direto não é automaticamente registrada como baixa luminosidade. O histórico permanece privado por usuário; fechar o diálogo preserva o comportamento vigente de encerrar a conversa ativa.

## FONTES

“Rafinha · Pesquisa web” identifica a origem. Referências `[1]` são clicáveis; “Fontes consultadas” expande títulos/links. A origem é sempre metadado de pesquisa ou referência interna disponível, sem inventar URLs.

Galeria usa até três imagens retornadas com origem identificável. Imagens Tavily por resultado têm a página-fonte; imagens soltas sem origem não são exibidas. Mantém proporção, responsividade, lazy loading e ausência de referrer. Os assets oficiais do Rafinha não são substituídos.

## TESTES EXECUTADOS

| Grupo | Resultado |
|---|---|
| Backend completo | 410 aprovados |
| Rafinha no navegador | 13 aprovados |
| Painel administrativo no navegador | 4 aprovados |
| Empacotamento | 18 aprovados |
| EXE em instalação temporária | 12 verificações aprovadas, zero chamadas externas |
| Ruff e build frontend | Aprovados |
| Segurança do pacote | Nenhuma credencial detectada em arquivos e conteúdo compilado |

Os cenários obrigatórios incluem ausência de chave, pesquisa desativada, chave válida sem autorização paga, autorização explícita, confiança alta sem escalonamento, divergência/verificação, cota/timeout/offline, remoção real, cliente403/admin permitido, cache, fontes/imagens e conversa com contexto. Modelos/providers externos usam MockTransport nesses testes; não representam uma chamada online real.

Ollama foi consultado realmente, sem API externa, e a regressão de “e ela” foi encontrada e corrigida. Conversas de verificação são apagadas ao terminar. O aviso de depreciação Starlette/httpx já existente não impediu os testes.

## COMO INICIAR O PROJETO

Na instalação de desenvolvimento preparada:

```powershell
cd C:\Projetos\GreenScape
.\scripts\iniciar.ps1 -NoBrowser
```

Para preparar um clone:

```powershell
cd C:\Projetos\GreenScape
py -3.12 -m venv .venv
.\scripts\iniciar.ps1 -Install
```

Acesso local: `http://127.0.0.1:5173`. O executável abre sua própria versão do portal no navegador, usa dados fora do pacote e não exige Node/Python instalados pelo usuário final. Ollama e seu modelo continuam dependências locais opcionais; o aplicativo não os inclui nem baixa automaticamente.

## COMO CONFIGURAR TAVILY

1. Crie/use sua própria conta Tavily e obtenha uma chave.
2. Entre como administrador da instalação.
3. Abra Configurações → Inteligência Artificial.
4. Informe a chave no campo Tavily → Salvar e validar chave.
5. Confirme “Configurada e validada”; Testar credencial atualiza a validação sem executar uma pesquisa.
6. Confira a cota/pay-as-you-go na conta e limites locais no aplicativo.
7. Salve a política desejada e teste a descrição da Orelha-de-Shrek pelo cliente.

## COMO CONFIGURAR OPENAI

1. Obtenha uma chave API de sua própria conta com modelo compatível com `web_search`.
2. No mesmo painel administrativo, use Salvar e validar chave.
3. Escolha um modelo liberado. A validação da chave não testa uma busca paga.
4. Somente se desejar autorizar gasto, marque Permitir pesquisa paga e salve a política.
5. Ajuste limites diário/mensal; desligue a opção ou remova a chave para impedir novas tentativas.

Não é obrigatório preencher `OPENAI_API_KEY` no `.env`; prefira o cofre. A API tem faturamento separado do ChatGPT. Credenciais pessoais/OAuth antigas não substituem a configuração BYOK da pesquisa paga.

## COMO GERAR O EXE SEGURO

```powershell
cd C:\Projetos\GreenScape
.\scripts\gerar_exe_seguro.ps1 -InstallBuildDependencies
```

O script gera uma saída nova em `release\windows\<data-hora>`, faz build frontend, scanner de entrada, PyInstaller com allowlist, scanner de arquivos/archives, smoke test com cofre vazio, manifesto e ZIP. Não distribua uma saída que falhe nesses passos. A distribuição é uma pasta: mantenha `_internal` junto de `AtelieVerde.exe`, ou extraia o ZIP completo.

Verificações reproduzíveis:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q --tb=short -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest packaging/tests -q --tb=short -p no:cacheprovider
.\.venv\Scripts\ruff.exe check backend/app backend/tests scripts packaging
cd frontend
npx.cmd playwright test tests/rafinha.spec.ts tests/admin-ai.spec.ts
npm.cmd run build
```

Sem alterar o pacote, também é possível repetir o scanner e smoke com `scripts/verificar_release.py <pasta>` e `scripts/testar_exe_seguro.py <pasta>`. Leia `LEIA-ME.txt` da distribuição para iniciar/encerrar. Nenhuma publicação GitHub foi realizada.

Referência de build: [PyInstaller](https://pyinstaller.org/en/stable/usage.html).

## PENDÊNCIAS

Tavily e OpenAI ainda não possuem chaves na instalação de desenvolvimento. Os testes reais online desses dois providers dependem de o administrador configurar as próprias credenciais; a integração e os fluxos foram testados com respostas simuladas. Pesquisa paga permanece desligada. Nenhuma credencial de outra conta foi reutilizada para contornar essa ausência.


## DISTRIBUIÇÃO VALIDADA

- ZIP: `release/windows/20261008-092351/AtelieVerde-Windows.zip` (130,18 MiB).
- EXE: `release/windows/20261008-092351/AtelieVerde/AtelieVerde.exe`, Windows x64 sem console.
- SHA256 ZIP: `ffc53acb1d41a875c4d665414923a8a06b3aed8af334e6f27e4fbdf68231c6d4`.
- Scanner aprovado: 970 arquivos, 1.923 entradas compiladas e 211 recursos públicos, sem achados de credenciais.
- ZIP comparado byte a byte com os 972 arquivos da pasta aprovada.
- Relatórios: `security-report.json` e `release-manifest.json` dentro da distribuição. O smoke test em uma instalação temporária confirmou 12 verificações, com zero chamadas externas.

A pasta completa deve acompanhar o EXE. Os dados ficam em `%LOCALAPPDATA%\AtelieVerde\Data` e o cofre em `%LOCALAPPDATA%\AtelieVerde\Rafinha`, fora dessa distribuição. Nenhuma publicação GitHub foi realizada.
