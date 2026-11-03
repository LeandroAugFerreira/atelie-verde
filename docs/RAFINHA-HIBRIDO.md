# Rafinha híbrido — relatório de evolução

Revisão concluída em 06/10/2026 no projeto local Ateliê Verde. Auditoria prévia: [AUDITORIA-RAFINHA-HIBRIDO.md](AUDITORIA-RAFINHA-HIBRIDO.md).

Revisão posterior das famílias de erro de interpretação: [REVISAO-INTERPRETACAO-RAFINHA.md](REVISAO-INTERPRETACAO-RAFINHA.md). Essa revisão substitui a extração anterior de nomes por uma camada compartilhada, acrescenta confirmação de ambiguidades e amplia o limite textual de pesquisa para 1 MB.

## Arquitetura implementada

Mensagem → autenticação e contexto autorizado → estado da sessão → recuperação interna → decisão de necessidade externa → pesquisa/cache quando apropriado → uma chamada ao Ollama quando necessária → validação → resposta, fontes e memória persistida.

O código controla banco, permissões, ações, fatos comerciais, fontes, orçamento de tempo e persistência. O Ollama recebe um contrato JSON para formular texto, extrair informações e sugerir intenção e expressões. A resposta é validada antes do uso; o modelo não executa SQL, comandos, navegação arbitrária nem alterações comerciais.

O limite operacional é de dez segundos por resposta: oito são reservados para consulta/pesquisa/geração a partir da entrada da rota, e dois para persistência e entrega. A geração utiliza deadline assíncrono real, não apenas um timeout renovado a cada pacote. Não há espera artificial para apresentar expressões. Etapas simples de identificação, saudações e consultas comerciais respondem diretamente. Sob carga do sistema, transporte HTTP e disputa pelo banco podem acrescentar latência fora da geração; não se trata de uma garantia de tempo real do computador.

## Memória, continuidade e mudança de assunto

`AssistantConversation.memory` guarda intenção, fase, espécie/produto reconhecidos, campos informados, campos desconhecidos, pergunta pendente, campos já perguntados, última resposta contextual e referência ao cache de pesquisa. Esse objeto funciona como resumo estruturado; somente as quatro mensagens anteriores relevantes e limitadas são enviadas ao modelo.

“Não sei”, “não faço ideia”, “não lembro” e “não conheço” são interpretados em relação à pergunta pendente. Nome desconhecido não volta a ser perguntado: o fluxo segue por foto de referência e características. “Dentro”, “fora”, “não” e “mais ou menos” podem preencher o campo que estava sendo discutido. Informações conhecidas ou explicitamente desconhecidas bloqueiam perguntas repetidas, incluindo perguntas retornadas pelo modelo.

As perguntas são políticas de campos reutilizáveis, não respostas cadastradas para cada espécie. Textos de cuidados e comércio usam registros recuperados. Mudanças explícitas de assunto, como cuidados de uma planta para serviços de poda, trocam a intenção sem obrigar a reiniciar o diálogo. Uma nova planta desconhecida limpa os dados específicos da anterior. Nome de produto ou SKU pode ser solicitado quando faltar contexto; produto inexistente não recebe preço ou estoque inventado.

Uma declaração de espécie interrompe a identificação por características. Novas perguntas não são gravadas como respostas a campos pendentes. Indicações explícitas, como “fora” e “sol direto”, preenchem ambiente e luz respectivamente. Informar outra planta depois de consultar preço ou estoque também troca o assunto e descarta a identidade anterior. Fontes botânicas não são exibidas como respaldo de preços comerciais.

Nova conversa limpa a tela e inicia estado vazio. Fechar o diálogo continua encerrando a conversa ativa, conforme a preferência anterior do usuário. Dados comerciais e demais cadastros não são apagados. Conversas permanecem isoladas por usuário.

## Expressões

`assistant_emotions.py` centraliza reação inicial, processamento e reação final. `rafinhaExpressions.ts` centraliza os assets e os rótulos. A classificação considera recuperação, negação, temporalidade e fatos disponíveis antes de sintomas históricos. “Não está mais murchando” e “antes estava amarela, mas agora está verde” recebem alívio; perda recebe tristeza; primeira floração pode receber surpresa e entusiasmo.

As poses existentes foram reaproveitadas. Foram acrescentados três PNGs transparentes — tristeza, surpresa e entusiasmo — usando as referências do personagem. Estados próximos compartilham poses: curiosidade/dúvida usam pensamento; confiança usa explicação; alívio usa alegria. O frontend mostra reação curta enquanto o processamento realmente ocorre, segue os metadados da resposta e retorna ao repouso depois de sete segundos. Não há vídeo ou sincronização labial.

## Pesquisa: decisão, provedor e qualidade

A decisão é registrada com motivo. Saudações, agradecimentos, preço, estoque, serviços, telefone, orçamento e dados de projeto ficam nos registros internos. Informações botânicas externas só são buscadas quando uma identidade foi informada e o conteúdo necessário não está suficientemente coberto. Responder a um campo do diálogo reutiliza contexto e não dispara nova busca. Ingestão potencialmente urgente recebe encaminhamento profissional imediato, sem esperar a pesquisa ou a IA.

O provedor padrão é um **índice institucional**: o sitemap XML público da NC State Extension. Ele permite descobrir páginas botânicas sem scraping de resultados de buscadores. O serviço valida que a página contém o nome informado ou seu sinônimo antes de utilizar o conteúdo. A consulta real de Calathea orbifolia encontrou [Goeppertia orbifolia na NC State](https://plants.ces.ncsu.edu/plants/goeppertia-orbifolia/) e foi validada com cache.

Uma API **SearXNG** com JSON habilitado pode ser configurada como alternativa. As instâncias públicas avaliadas retornaram HTML, verificação anti-bot ou limitação; nenhuma proteção foi contornada. O código usa uma interface de provedor para facilitar substituição. Não foi criado serviço pago, contratado plano ou adquirido chave.

Somente fontes institucionais previstas são aceitas: NC State Extension, RHS, Kew, Embrapa, Missouri Botanical Garden, ASPCA e instituições de extensão/universidades configuradas no código. URLs com credenciais, esquemas inadequados, destinos privados e redirecionamentos são bloqueadas. Downloads têm prazo e tamanho máximo. O índice é XML padronizado, sem DTD/entidades; conteúdo de scripts, navegação e instruções aparentes é descartado. Trechos limitados são enviados como dados, não instruções.

Resultados são ordenados pela correspondência e limitados a dois editores distintos, quando disponíveis. O padrão institucional geralmente oferece uma fonte, não uma confirmação independente por duas instituições. Essa limitação é explícita: o sistema não transforma uma fonte isolada em identificação definitiva. Vocabulários estruturados da publicação podem ser apresentados em português; divergências detectadas de luminosidade são expostas em vez de escolher uma delas arbitrariamente. Formulações generativas ainda exigem avaliação: filtros e referências reduzem risco, mas não constituem uma prova automática de toda afirmação botânica.

## Cache e modo offline

`AssistantResearchCache` guarda apenas material botânico público, por hash de espécie/assunto, com expiração. Perguntas equivalentes podem reutilizar o mesmo resultado; o índice e os resultados válidos têm TTL de 24 horas. Resultados sem informação têm TTL curto de cinco minutos. O contexto da conversa pode reutilizar a pesquisa anterior sem novas requisições. Conversas, fotos e dados privados não são chaves de busca externa nem conteúdos desse cache.

Sem internet, catálogo e dados internos continuam disponíveis; falhas de pesquisa produzem uma resposta explicativa e preservam o estado. Sem Ollama, com resposta inválida ou fora do prazo, o modo guiado usa dados internos, material público já validado quando disponível e perguntas de campos para continuar. Fatos comerciais são renderizados a partir do banco, sem substituição por preços externos. A interface distingue origem — Catálogo, Identificação, Cuidados, Serviços ou Pesquisa — e indica “Resposta guiada” quando a formulação não veio do modelo. Assim, a pesquisa externa não aparece rotulada como base interna.

## Fotos e limites reais

O cliente pode anexar até três JPEG/PNG de até 5 MB por conversa. Os arquivos têm nomes aleatórios, verificação de imagem, limite de pixels, armazenamento privado, autorização por conversa e exclusão ao encerrar a conversa. O modelo **qwen3:4b** instalado é textual: as fotos são referências privadas e a identificação continua pela descrição, sem simular análise visual.

O modelo local foi mantido. A CPU desta máquina anteriormente levou 44–72 segundos em geração sem o novo limite. Com a meta de dez segundos, algumas formulações recorrem ao modo guiado. Não foi baixado modelo menor ou multimodal sem autorização. PostgreSQL e Docker permanecem preparados, mas não foram executados localmente.

## Configuração e execução

Variáveis, sem credenciais no código:

```dotenv
RAFINHA_PROVIDER=auto
RAFINHA_OLLAMA_URL=http://127.0.0.1:11434
RAFINHA_OLLAMA_MODEL=qwen3:4b
WEB_SEARCH_PROVIDER=institutional
WEB_SEARCH_URL=
```

O backend lê somente essas opções de `.env`, sem sobrescrever variáveis explícitas nem alterar configuração de banco/autenticação. O arquivo local não é versionado. `.env.example` e Compose foram atualizados. O script Windows também mantém o suporte à configuração local anterior.

Para SearXNG, use `WEB_SEARCH_PROVIDER=searxng` e uma `WEB_SEARCH_URL` HTTPS pública cuja API permita JSON. Nenhuma chave é exigida pelo provedor padrão. O fallback institucional continua sendo a configuração funcional desta máquina.

```powershell
cd C:\Projetos\GreenScape
& .\scripts\parar.ps1
& .\scripts\iniciar.ps1 -NoBrowser
```

## Arquivos criados

- Backend: `assistant_budget.py`, `assistant_state.py`, `assistant_engine.py`, `assistant_research.py`, `assistant_uploads.py`, `assistant_settings.py`.
- Migração: `b51005af0002_hybrid_assistant.py` — memória de conversa, cache público e anexos privados.
- Frontend: `rafinhaExpressions.ts`.
- Testes: `test_hybrid_assistant.py`.
- Assets: `sad.png`, `surprised.png`, `excited.png`, em `frontend/public/rafinha/`.
- Documentação: auditoria prévia e este relatório.

## Arquivos modificados

`assistant.py`, `assistant_provider.py`, `assistant_emotions.py`, `models.py`, `main.py`; `RafinhaAssistant.tsx`, `rafinha.css`, `api.ts`; `.env.example`, Compose, configuração do Playwright e fixtures/testes do assistente. O logo foi ampliado para até 400 px no login e a frase principal ganhou mais espaço abaixo dele, mantendo a posição aprovada.

`assistant_knowledge.py` também recebeu ajuste de pontuação na apresentação da rega. README e a documentação anterior apontam para esta revisão.

## Validação

Os testes cobrem o protocolo real do Ollama com transporte controlado, deadline, JSON inválido, indisponibilidade, preço inventado, memória privada, pronomes, respostas curtas, conhecido-desconhecido, mudança de assunto, pergunta repetida pelo modelo, expressões e negação, cache/expiração, destinos proibidos, instruções maliciosas em páginas, perda de conexão, foto privada e exclusão. O navegador valida os fluxos, o reinício do diálogo, os anexos e o layout em computador e celular com zoom de 100%.

Resultados em 06/10/2026:

- Backend completo: **102 testes passaram**. A suíte de assistente foi executada novamente após os ajustes de contexto; 47 testes passaram nessa execução específica.
- Navegador: **31 testes passaram** na suíte completa. Depois dos últimos ajustes de estado, os oito testes específicos do Rafinha passaram novamente.
- Build do frontend: TypeScript e Vite concluídos. Ruff sem erros; Alembic sem diferenças pendentes após aplicar a migração, validada em banco novo e no banco local.
- Projeto em execução, Ollama disponível: 12 mensagens cobriram identificação, desconhecimento, nome informado, rega, resposta curta, serviços, preço, estoque, nova espécie externa, cache e recuperação. Respostas diretas ficaram entre 0,05 e 0,16 segundo; as três consultas que aguardaram geração ficaram entre 8,05 e 8,09 segundos. Nesta medição o modelo não concluiu dentro do prazo, e todas as respostas usaram o modo guiado. O protocolo generativo bem-sucedido também é testado com transporte controlado.
- Pesquisa real da Calathea retornou a página institucional correspondente; a segunda etapa reutilizou o cache da conversa, sem nova pesquisa. Fotos são referência, conforme o limite textual já explicado.
- Conferência visual do logo ampliado, frase inferior, legenda no canto direito, personagem à esquerda do diálogo e imagens com alpha. Computador e celular também são cobertos pelo navegador.
- Coerência do banco: **61 produtos, 28 pedidos, 11 orçamentos e 40 agendamentos; zero erros e zero alertas**. Todas as linhas e colunas anteriores de produtos, usuários, pedidos, estoque, fornecedores, orçamentos, projetos, financeiro, agenda, imagens, documentos e configurações foram comparadas ao backup e permanecem iguais. SQLite íntegro, sem violações de chaves estrangeiras.

Dois avisos do ambiente de testes permanecem: depreciação do transporte Starlette/httpx e falta de permissão para gravar o cache do pytest; nenhum causou falha de teste. Evidência da medição está em `.local/hybrid-live-validation.json`. O backup anterior à mudança está apontado em `.local/latest-hybrid-backup.txt`. Nada foi publicado ou enviado à produção.

## Referências de implementação

- [API SearXNG](https://docs.searxng.org/dev/search_api.html).
- [NC State Extension Plant Toolbox](https://plants.ces.ncsu.edu/).
- [API de chat local do Ollama](https://docs.ollama.com/api/chat).
- [ASPCA: orientação para suspeita de intoxicação](https://www.aspca.org/pet-care/aspca-poison-control).
