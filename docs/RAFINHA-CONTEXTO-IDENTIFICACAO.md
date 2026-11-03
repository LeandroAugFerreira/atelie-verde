# Interpretação de pistas e respostas úteis — 8 de outubro de 2026

O problema relatado misturava três falhas: palavras genéricas digitadas incorretamente, predicados tratados como nomes e respostas do modelo que prometiam ajudar sem responder. A correção atua na interpretação e na validação da conversa, mantendo a interface e as expressões existentes.

- Erros evidentes em termos genéricos, como `suculent5a`, são normalizados somente para interpretação. O texto original enviado pelo usuário continua no histórico. Nomes botânicos não são corrigidos automaticamente.
- `Ganhei, parece…` e `lembra…` introduzem características; `parece`, `vc sabe qual é` e `me diga` não viram nomes de plantas. Pedidos curtos retomam a intenção e as pistas da memória.
- Memórias antigas contendo grupos ou palavras de diálogo como nomes são reparadas quando a conversa continua, preservando os relatos de rega, luz e sintomas.
- Comparações não são confundidas com pedidos de recomendações do catálogo. Suculência e família Cactaceae são conceitos diferentes; não se aplica uma rotina única de cultivo a todos os integrantes desses grupos.
- Uma pequena biblioteca de referências internas relaciona apelidos a hipóteses e características verificáveis. Ela inclui Crassula ovata 'Gollum', planta-jade e Sedum morganianum. As hipóteses permanecem separadas de `plant_name` e `species_id`, sem criar plantas, produtos ou registros comerciais.
- O modelo recebe a referência e o contexto. Ecos, promessas vazias e respostas que contradizem a referência são rejeitados. Uma frase como `pode ser confirmada` não conta como indicação de incerteza. Família botânica incorreta também invalida a resposta apoiada na referência.
- Tavily configurada continua sendo consultada quando as pistas exigem identificação. As referências internas ajudam quando não há pesquisa disponível. Elas não são apresentadas como uma busca online realizada durante a conversa. Uma hipótese anterior e os relatos seguintes são reaproveitados sem pesquisar em toda mensagem.
- Relatos de rega excessiva ou terra encharcada usam a orientação interna verificada de umidade e drenagem. O modelo pequeno não pode substituir esses cuidados por uma identificação diferente ou inferir pouca luz a partir de ausência de sol direto. A umidade não é perguntada novamente se já foi informada.

As regras de credenciais, permissões administrativas, limites e autorização de pesquisa paga permanecem em vigor. Nenhuma chave é necessária para essas referências internas.

## Referências

- [NC State — Crassula ovata e variedades](https://plants.ces.ncsu.edu/plants/crassula-ovata/): características de jade, Gollum e Hobbit; família Crassulaceae.
- [NC State — Sedum morganianum](https://plants.ces.ncsu.edu/plants/sedum-morganianum/): características da planta conhecida como rabo-de-burro.
- [RHS — cultivo de cactos e suculentas](https://www.rhs.org.uk/plants/types/cacti-succulents/houseplants/growing-guide): variação de necessidades e exceções dos cactos de floresta.

## Validação

`backend/tests/test_assistant_contextual_identification.py` cobre famílias de grafias, nomes reais, memórias antigas, pistas negadas ou ambíguas, pedidos curtos, comparações, respostas vazias e identificação indevidamente afirmada pelo modelo. `test_installation_research.py` também reproduz a sequência com Tavily simulada: comparação sem busca, identificação com uma busca e continuidade sem chamadas duplicadas ou pesquisa paga.

A sequência original de seis mensagens também foi repetida no portal local com `qwen3:0.6b`, sem chaves externas: comparação correta, hipótese cautelosa, pedidos curtos respondidos com o nome e continuidade de cuidados sem perder o contexto. Na repetição final, as respostas levaram entre 0,06 e 27,38 segundos. A conversa temporária de validação foi removida.

## Continuidade após uma apresentação

A validação de respostas também rejeita uma saudação genérica quando o usuário já informou uma planta, trouxe uma condição ou fez uma pergunta. Repetições quase idênticas são verificadas ao mudar a intenção ou acrescentar dados à memória, incluindo o objetivo dos cuidados e informações que a pessoa não sabe. Saudações acompanhadas de uma resposta útil e pedidos explícitos para repetir continuam permitidos.

Repetir `tenho uma roseira` mantém o assunto e o objetivo ainda pendente, sem repetir a mensagem de boas-vindas ou pedir novamente o nome. Os testes usam também Lavanda, begônia e samambaia; a regra não depende de uma espécie específica. O detector consome frases de maneira limitada, inclusive quando o modelo repete muitas saudações em um mesmo parágrafo.

A apresentação sem dúvida ou sintomas usa uma pergunta contextual da política de diálogo, com o nome já reconhecido, sem aguardar geração pelo modelo. As dúvidas e continuações seguem utilizando o Ollama e os demais fluxos existentes. A validação também rejeita a inversão `Tenho uma roseira` na fala do assistente e saudações vazias retornadas pela síntese de pesquisa.

Perguntas são extraídas da resposta mesmo quando há uma frase depois do ponto de interrogação. Isso permite rejeitar perguntas sobre nome, ambiente, rega ou objetivo de cuidados já informados. Na validação real de `Olá → tenho uma roseira → tenho uma roseira → quero cuidados gerais`, as apresentações levaram cerca de 0,06 segundo e o objetivo permaneceu na memória; não foi repetida a saudação nem a pergunta sobre querer cuidados gerais.

A biblioteca é limitada e não substitui uma identificação profissional ou um modelo de linguagem capaz. As validações reduzem erros nos fluxos cobertos; não garantem que toda resposta de um modelo local pequeno tenha a qualidade do ChatGPT. Novos apelidos podem ser acrescentados como registros com fontes, sem criar respostas específicas para uma conversa.

Esta correção atualiza o projeto e o portal local. O ZIP datado de `20261008-092351` corresponde ao build anterior; para distribuir estas alterações, gere uma nova saída com `scripts/gerar_exe_seguro.ps1` e suas verificações de segurança.
