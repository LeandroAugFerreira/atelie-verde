# Rafinha: resposta progressiva e contexto

O Rafinha continua usando exclusivamente a conta ChatGPT selecionada na instalação local. As 12 expressões oficiais, a análise de fotos, a conversa contextual e o bloqueio de credenciais no executável foram preservados.

## Mudanças

- O texto do ChatGPT é exibido durante a geração, pelo endpoint privado de progresso, consultado a cada 350 ms sem requisições sobrepostas. Os trechos ficam em memória, limitados e vinculados ao usuário, conversa e solicitação; não vão ao banco ou a logs. Cancelar, fechar ou terminar elimina o estado temporário. O endpoint impede acesso por outro usuário e não entrega o texto a origens externas.
- O transporte encerra ao receber `response.completed`, sem aguardar o fechamento do socket. As verificações de conexão e cancelamento têm intervalo de 200 ms e uma verificação obrigatória na conclusão, evitando acesso ao cofre e banco em cada linha de tokens.
- O modelo configurado `gpt-5.6-sol` usa esforço `none` na conversa normal e `low` para toxicidade e pesticidas. Não há troca do modelo escolhido nem inclusão de outro provedor.
- Pesquisas mantêm até 10 segundos, dentro do orçamento compartilhado da solicitação, deixando tempo para uma resposta da mesma conta quando a ferramenta demora. Um timeout da busca não coloca toda a conexão em espera. Fontes de pesquisa só são apresentadas após validação dos resultados; esse texto aguarda a validação antes de aparecer.
- Cuidados cotidianos podem usar o conhecimento do ChatGPT mesmo quando a espécie está fora do cadastro. Uma hipótese de identificação já coberta por referência interna não exige uma pesquisa adicional. Perguntas explícitas de pesquisa, riscos, informações atuais e problemas que exigem evidências continuam seguindo a política de busca.
- O contexto recente conserva mensagens completas até 20 mensagens/20 mil caracteres, em vez de cortar cada fala em mil caracteres. A última pergunta e fotos privadas continuam sendo enviadas separadamente.
- O prompt orienta começar pela resposta direta, aproveitar os dados recebidos e detalhar conforme a necessidade. Referências botânicas e observações já disponíveis acompanham a conversa. Não afirma diagnósticos ou identificação definitiva a partir de descrição/foto.
- A interface mostra imediatamente a resposta recebida, sem buscar novamente o histórico nem repetir a animação de digitação após o streaming. A animação das respostas sem streaming ficou mais curta. As expressões de preocupação, perda e alerta permanecem durante a espera e acompanham o texto que chega.

## Validação

- Build TypeScript/Vite e Ruff aprovados.
- Suíte geral: 537 testes de backend/distribuição aprovados. Após o ajuste final da seleção de pesquisas, 67 testes do fluxo ChatGPT/pesquisa aprovados, incluindo os novos casos de cuidados e referências internas.
- 16 testes distintos da interface do Rafinha aprovados (15 na suíte e o teste de citações reexecutado após adaptar o mock à resposta direta do envio).
- Os testes cobrem término do SSE sem fechamento da conexão, contexto longo, visualização durante a espera, privacidade, cancelamento/exclusão, falha de geração, timeout da pesquisa, minimização e todas as 12 expressões oficiais.
- Na primeira medição real, a resposta sobre cuidados da roseira começou a aparecer em 3,08 s e terminou em 9,50 s. Dois outros turnos preservaram contexto e preocupação, com a busca ainda consumindo 10 s antes do ajuste final da política de pesquisa. Esses tempos são amostras, não garantia de latência do serviço.
- O limite diário local configurado chegou a 20/20 consultas durante as verificações; novos testes reais dependem de ampliar esse limite ou da virada do dia. A contagem e o limite foram preservados.

Documentação oficial consultada: [Streaming API responses](https://developers.openai.com/api/docs/guides/streaming-responses) e [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization).

## Distribuição

- Executável atualizado: `release/windows/20261010-225340/AtelieVerde/AtelieVerde.exe`.
- Pacote: `release/windows/20261010-225340/AtelieVerde-Windows.zip`, 231.718.833 bytes; 1.049 arquivos conferidos integralmente contra a pasta compilada.
- SHA-256: `90e8d5015b901f2ece82876a1a34370355df042d716782241d0da390ba9ae142`.
- Scanner aprovado, sem achados; 13 verificações da instalação isolada aprovadas, sem chamadas externas. Inclui o bloqueio do ChatGPT até login próprio, cofre público vazio e separado, privacidade e as 12 imagens oficiais.
- Portal de desenvolvimento e API confirmados disponíveis após a geração do pacote.
