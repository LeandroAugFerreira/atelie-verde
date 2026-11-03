# Rafinha: IA local e conexões pessoais opcionais

Implementação local de 06/10/2026. O Ollama continua como alternativa gratuita; catálogo, regras e dados comerciais funcionam sem uma conta OpenAI. O ChatGPT conectado assume as conversas sobre plantas, sem habilitar uma chave paga por falta de uso do plano.

## Como testar

1. Abra o portal Cliente e o Rafinha. Clique na engrenagem **Preferências do Rafinha**.
2. Clique **Continuar com ChatGPT** e autorize o uso do plano no navegador oficial. Depois da autorização, a tela se atualiza, escolhe o primeiro modelo liberado pela conta e ativa a conversa automaticamente. Não há segunda etapa obrigatória de seleção ou ativação.
3. Para pausar o uso do plano, clique **Usar Rafinha local**. Para ajustar modelo, limite ou conexão local, abra **Preferências avançadas**.
4. O limite diário (20 por padrão, entre 1 e 100) é salvo automaticamente ao editar, sair do campo ou fechar as preferências. A interface informa quando salvou ou quando houve falha. Alterar o limite não troca o modelo nem habilita/desabilita a conta. Refazer o login na mesma conta conserva a escolha de modelo e o limite. Desconectar/reconectar não zera o contador do dia.
5. A API convencional continua em **Preferências avançadas → OpenAI API · configurações avançadas**. A chave é pessoal, a cobrança é separada e a ativação permanece explícita.

Saudação, identidade, preço, estoque, dados de clientes autorizados e agenda usam o sistema interno. Nas conversas botânicas, inclusive respostas curtas e recomendações, o modelo recebe a memória e o histórico. O ChatGPT autorizado tem prioridade; se falhar ou atingir o limite, tenta o Ollama e depois o modo guiado. A API convencional mantém o comportamento de complemento da IA local. O indicador de cada resposta mostra o mecanismo que realmente a produziu.

## ChatGPT e API são modalidades diferentes

O login utiliza o fluxo oficial de [ChatGPT plan usage para apps locais](https://developers.openai.com/siwc/token-sharing-open-source). Sua elegibilidade depende das regras e da autorização da OpenAI. A documentação de uso descreve planos [Plus/Pro elegíveis](https://learn.chatgpt.com/docs/sign-in-with-chatgpt). Não há promessa de usar o plano gratuito como API. A compatibilidade de aplicações comerciais/remotas precisa de autorização adicional da OpenAI.

O fluxo local segue [registro e autorização oficiais](https://developers.openai.com/siwc/token-sharing-open-source/sign-in): PKCE S256, tentativa com state e nonce, listener em 127.0.0.1, verificação da identidade assinada, permissão explícita para usar o plano e renovação de tokens. Senha, cookie e token manual do ChatGPT não são solicitados.

As chamadas seguem a [Responses API autorizada por conta](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference), com histórico necessário, `store:false` e streaming. Apenas a conclusão terminal é aceita como resposta. A API convencional utiliza sua chave pessoal e a [cobrança de API](https://developers.openai.com/api/docs/pricing). Não há chave global compartilhada nem leitura automática de OPENAI_API_KEY.

## Credenciais e distribuição

No Windows, os dados pessoais ficam em `%LOCALAPPDATA%\AtelieVerde\Rafinha`, protegidos com DPAPI vinculada ao usuário do Windows. Em outros sistemas, o arquivo é cifrado com chave local e permissões restritas. O vínculo também é separado pelo usuário do portal. Credenciais não são retornadas à interface, não entram no SQLite de demonstração e não ficam no frontend ou código distribuído. A chave inserida no formulário é transitória e é limpa depois da submissão.

Para distribuir o projeto, exclua `.env`, `.local`, `backend/data`, qualquer pasta privada de credenciais, caches e logs. A pasta pessoal padrão já fica fora do projeto. Outra instalação começa sem conta conectada e cria seu próprio identificador de instalação. Testes usam diretórios temporários e chaves fictícias.

Este repositório ainda não tinha um empacotador de executável; esta etapa prepara o comportamento da aplicação, mas não cria um instalador Windows. Não copie uma instalação completa contendo dados pessoais para formar um pacote. Instalação compartilhada deve usar cadastros próprios, evitando compartilhar o perfil demonstrativo que uma pessoa tenha conectado.

## Roteamento, custo e contingência

Dados comerciais continuam nas consultas internas autorizadas. Nas conversas: memória e fatos → ChatGPT pessoal autorizado → Ollama → resposta guiada. Sem plano conectado, a conversa começa pelo Ollama. Fontes externas são recuperadas quando faltam informações verificáveis sobre o assunto específico; uma ficha com rega/luz não passa por orientação de propagação, poda ou ocorrência atual. Conhecimento geral pode ser explicado com cautela pelo modelo, sem ser apresentado como pesquisa verificada, diagnóstico ou dado comercial.

O orçamento continua em dez segundos, com oito reservados para processamento. A pesquisa tem até três segundos para deixar tempo à conversa. O ChatGPT tem até seis segundos dentro do tempo restante, e o modo local usa a sobra em caso de falha. O modelo local é preparado em segundo plano, sem bloquear a abertura do portal. Não há espera artificial para trocar expressões.

Sem internet, conta, autorização, modelo local disponível ou resposta válida, o atendimento continua com os recursos locais e o catálogo. Falhas de nuvem, excesso de uso e respostas incompletas não acionam outra credencial paga. Uma troca de conta durante uma resposta não reaproveita silenciosamente a nova conta para a requisição antiga.

Pesquisa botânica permanece institucional, com cache e fontes verificadas. Perguntas atuais regionais requerem fonte recente e relevante; o índice botânico padrão não é um buscador de notícias. Sem uma API de busca configurada e fonte verificável, essa limitação é explicada. Toxicidade, defensivos e doenças não recebem confirmação ou dosagem inventada. Fotos continuam como referências: não foi habilitada análise visual automática.

## Arquivos e validação

Novos módulos: `assistant_credentials.py`, `assistant_connections.py`, `assistant_openai.py`, `assistant_ai.py`, `assistant_request.py`; componente `RafinhaConnection.tsx`; testes de conexão pessoal e roteamento factual. Os módulos existentes de roteamento, conhecimento, memória, pesquisa, personalidade, interface e configuração foram integrados. `cryptography` foi acrescentado para a verificação criptográfica e a proteção de arquivos em sistemas sem DPAPI. Nenhuma migração de dados comerciais foi necessária.

Os testes verificam: isolamento entre usuários, cifra, ausência de credenciais nos retornos, consentimento negado, PKCE/state/nonce, identidade verificada, modelo autorizado, limite diário, desconexão, SSE incompleto, erro de autenticação, quota, serviço indisponível, prioridade local, mensagens internas sem chamadas externas e escopo local de uso das credenciais. A suite de navegador também verifica configuração opcional, formulário privado e continuidade do atendimento gratuito.

Não foi usado login real ou chave real durante o desenvolvimento. O protocolo foi validado com transporte controlado, sem custo. A validação real de elegibilidade e geração requer que o próprio usuário conclua o login e a autorização no navegador. Nada foi publicado ou enviado a produção.

Para um portal comercial público, uma IA fornecida pela empresa no servidor elimina a necessidade de o cliente configurar uma conta externa; exige um serviço próprio com orçamento e credenciais protegidas no backend. O fluxo pessoal desta demonstração atende ao projeto local distribuído, não compartilha credenciais entre clientes e não implementa esse serviço comercial.

No computador de desenvolvimento com 8 GB de RAM e aproximadamente 800 MB livres, o `qwen3:4b` não terminou de carregar em 45 segundos. Foi instalado e selecionado o `qwen3:0.6b`, de cerca de 523 MB, preservando o modelo anterior. O modelo menor carregou em 3,6 segundos, mas sua capacidade e velocidade não equivalem às de um modelo ChatGPT; a inferência ainda depende da memória e da carga do computador. Trechos brutos em inglês e explicações sobre timeout não são mais apresentados como resposta de contingência.

A inicialização respeita variáveis explícitas, depois `.env`, usando `.local/rafinha-provider.json` somente como fallback. Essa ordem evita que um registro antigo substitua o modelo recém-configurado. O prompt local e a saída foram compactados para caber no prazo e evitar conselhos sem respaldo nos fatos. Um teste real com a descrição do print respondeu em 3,48 segundos, perguntando sobre a luz; em carga concorrente houve timeout, tratado pelo modo guiado.

Validação da simplificação: 266 testes gerais do backend e dez testes do Rafinha no navegador aprovados; as revisões finais passaram também nos 58 testes híbridos, nos 18 testes de conexão e no cenário específico do aviso de uso do plano e salvamento do limite. Compilação e Ruff aprovados. A conta já autorizada do perfil demonstrativo, ainda sem modelo e sem ativação pelo fluxo anterior, foi preparada com uma opção liberada. O contador permaneceu em zero; não houve geração com a conta real.

Resultados registrados: 249 testes de backend aprovados, build TypeScript/Vite aprovado, Ruff sem erros e banco íntegro. A medição local de 12 mensagens ficou em até 9,34 segundos durante testes concorrentes. A conferência comercial mostrou 61 produtos, 28 pedidos, 11 orçamentos e 40 compromissos, sem erros ou alertas. Os registros anteriores foram comparados ao backup e permanecem iguais. Dois avisos do ambiente de pytest (transporte obsoleto e cache sem permissão de escrita) não impediram os testes.

Validação final da interface: os 32 testes de navegador passaram após corrigir a prontidão inicial dos controles. A captura da configuração local foi conferida visualmente. Houve um aviso de conexão encerrada no event loop Windows durante cancelamento em teste, sem falha de execução.
