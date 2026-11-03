# Pesquisa e expressão persistente do Rafinha

O limite pessoal foi alterado para 100 consultas diárias pelo endpoint administrativo da conexão selecionada e confirmado após reiniciar o projeto. A contagem existente, o modelo escolhido e as credenciais foram preservados. Esse limite pessoal não é incorporado ao executável público.

## Expressões

Foi removido o temporizador que trocava a pose pela expressão neutra após sete segundos. A expressão da resposta permanece até a próxima mensagem enviada. Digitar um rascunho, finalizar a animação de texto, reduzir movimento ou minimizar/reabrir a janela não troca a expressão. Fechar ou iniciar outra conversa continua limpando o estado.

As 12 imagens oficiais permanecem. O teste de navegador avança o relógio por dois minutos e confirma a permanência da expressão; uma nova mensagem permite mudar a reação.

## Pesquisa

- Pedidos explícitos de pesquisa botânica são enviados ao ChatGPT mesmo quando o analisador local sugere mais de um nome de planta. Permanecem as restrições de origem local, propriedade da conversa, dados privados, limites e situações de emergência.
- A pesquisa usa esforço baixo, contexto de busca reduzido e parâmetros compatíveis com a autorização de login ChatGPT. O texto normal continua usando esforço `none` no modelo configurado, mantendo esforço baixo para assuntos de toxicidade e pesticidas.
- A busca é direcionada. O prompt prioriza pontos essenciais em dúvidas gerais e detalhamento quando solicitado ou necessário para segurança. Não acrescenta buscas de imagens à espera; referências visuais podem aparecer quando o provedor realmente as retornar com origem verificável. As fotos privadas enviadas pelo cliente continuam chegando ao modelo.
- A configuração envia `store: false`, `stream: true`, contexto em uma lista e solicita apenas metadados de fontes suportados. Não envia `max_tool_calls` na rota de login ChatGPT: a documentação oficial identifica esse campo como incompatível com o compartilhamento do plano.
- O prazo inicial da pesquisa cobre a obtenção de evidências. Quando uma busca concluída fornece URLs públicas válidas, a geração pode terminar dentro do orçamento total já configurado, sem descartar uma pesquisa pronta por ainda estar escrevendo a resposta.
- Após haver metadados de fontes válidos, o texto da pesquisa aparece durante a geração, sem esperar a resposta inteira. Pensamentos internos, fontes privadas, credenciais e preços sem suporte continuam bloqueados. Somente mensagens concluídas são salvas no histórico.

## Validação

- TypeScript/Vite e Ruff aprovados.
- 17 testes de navegador aprovados, incluindo permanência da expressão, minimização, referências e as 12 imagens.
- Suíte geral de backend/distribuição: 543 testes aprovados. Após os ajustes de compatibilidade e síntese, 70 testes dos fluxos ChatGPT/pesquisa novamente aprovados.
- Testes específicos verificam preview com fontes válidas, bloqueio de fontes privadas, término após o prazo inicial da busca, cancelamento e ausência de parâmetros incompatíveis.
- Testes reais da conta confirmaram a pesquisa com fontes institucionais. Uma consulta curta terminou em 5,83 s. Pelo portal, a versão final começou a aparecer em 6,36 s, terminou em 15,95 s e incluiu 12 fontes efetivamente retornadas. Uma amostra anterior da mesma pergunta levou 20,36 s; são amostras, não garantia de latência.
- Respostas sem pesquisa também foram medidas: uma começou em 2,16 s e terminou em 8,34 s, preservando o contexto da conversa.

Fontes oficiais consultadas: [limitações do login ChatGPT](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations), [modelos e inferência com a conta ChatGPT](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference) e [pesquisa web](https://developers.openai.com/api/docs/guides/tools-web-search).

## Executável

- Pacote atualizado: `release/windows/20261011-130749/AtelieVerde-Windows.zip`.
- Scanner sem achados; 13 verificações da instalação isolada aprovadas, com zero chamadas externas. A conta do desenvolvedor continua fora do pacote, e o ChatGPT fica bloqueado até login próprio.
- Integridade dos 1.049 arquivos conferida contra a pasta compilada; tamanho de 231.717.068 bytes.
- SHA-256: `8659b90f897c2e8daff6087eb226ca2e3d9026ab49e5a981d59e619fad6bf475`.
- A configuração pessoal de 100 consultas foi novamente consultada após reiniciar e permaneceu salva.
