# Revisão da interpretação do Rafinha — 06/10/2026

A frase “tenho uma roseira e não sei como cuidar” revelou uma falha geral: o extrator confundia a descrição da planta com a dúvida, enquanto o fluxo de identificação tratava parte da frase como desconhecimento do nome. A revisão cobre famílias de falhas e usa os nomes cadastrados, sem respostas específicas escritas para cada espécie.

## Mudanças

- `assistant_language.py` centraliza normalização, nomes informados, frases, negação, informações declaradas, respostas desconhecidas e seleção entre opções. “Tenho”, “minha”, “ganhei”, “é”, “cuidar”, “regar” e outras formas preservam o nome separado de localização, sintomas e dúvida. Nomes científicos, compostos e com hífen seguem o mesmo processo.
- A busca no catálogo usa palavras completas, acentos normalizados, espaços/hífens e variações de plural. Nomes compostos maiores têm prioridade quando se sobrepõem a nomes curtos. Uma parte de outra palavra não passa por identificação botânica.
- Erros de digitação geram sugestões baseadas nos cadastros. O assistente pede confirmação antes de vincular a espécie. Identidade incerta e vários nomes também exigem escolha; “sim”, “a primeira” e “a segunda” podem confirmar opções existentes. Negar uma sugestão não a confirma.
- Desconhecimento do nome, da foto, da luz e da rotina de rega são distintos. “Não sei cuidar” não preenche nem torna desconhecido o campo do nome. Uma nova pergunta não é registrada como resposta a um campo pendente.
- Ambiente, luz e rega podem ser informados juntos. Perguntas sobre essas condições não são tratadas como declarações. Negação de ambiente, luz e sintomas é considerada antes de persistir dados e escolher a expressão.
- Gratidão ou comemoração no início de uma mensagem não apaga sintomas relatados depois. Recomendações do catálogo também não identificam automaticamente a planta da pessoa, mesmo quando há apenas uma opção.
- Nomes novos têm prioridade sobre o contexto anterior. A autorização de projetos e orçamentos é verificada antes de substituir o contexto; mudar de assunto não contorna a privacidade.
- Preço e estoque continuam vindo do banco. Saudação, serviços e consultas comerciais seguem internos. Não foram geradas vendas, alterados estoques ou substituídos cadastros nesta revisão.

## Pesquisa externa

O nome popular “roseira” tem uma referência geral do gênero **Rosa**, validada pela página [NC State Extension](https://plants.ces.ncsu.edu/plants/rosa/). Isso não identifica a variedade nem a confunde com rosa-do-deserto.

A página institucional real tinha 642.012 bytes e excedia o limite anterior. O teto de texto passou a 1 MB, mantendo validação de destino, tipo de conteúdo e prazo total. O prazo por fonte foi ajustado dentro do orçamento da resposta. Uma falha em outra fonte não descarta material válido já recuperado. Scripts e instruções aparentes continuam excluídos; somente trechos limitados são armazenados e enviados ao modelo.

A consulta real do exemplo retornou a referência institucional, explicou o alcance geral da informação e perguntou sobre o ambiente. Levou **8,05 segundos**, usando resposta guiada quando o Ollama não concluiu no prazo.

## Validação

- Matriz de reconhecimento no catálogo real: **40 espécies e 200 consultas, sem falhas**, incluindo nome popular, científico, espaços/hífens e frases completas. Script somente de leitura.
- Testes de linguagem: diferentes estruturas de frase para seis tipos de nome, plural, colisões, negação, não nomes, campos desconhecidos e mensagens com sintomas e comemoração.
- Testes de integração: confirmação de grafia, seleção entre plantas, identidade incerta, mudança de contexto, privacidade, recomendação única, fonte parcialmente indisponível, respostas curtas e o fluxo original do print.
- Suíte geral do backend: **212 testes passaram**. Ruff sem erros. Os **oito testes de navegador** do Rafinha passaram após a revisão da interpretação. A matriz de 200 consultas nas 40 espécies foi validada separadamente, sem alterar cadastros.

## Limites

Revisão do novo print: o limite de palavra nas preposições impede interpretar “dela/dele” como “de” mais um nome. Pronomes e demonstrativos foram cobertos em testes de regressão. O seletor reutiliza o registro botânico de nomes, permitindo escolher “Rosa” para a opção “roseira”. A suíte específica de linguagem e assistente passou com 168 testes nesta execução.

O reconhecimento exato usa os registros do catálogo. Sugestões aproximadas precisam de confirmação; termos genéricos ou fora do catálogo não se tornam uma espécie específica por inferência. A pesquisa institucional não é um índice universal de nomes populares. Quando faltar correspondência ou a fonte não responder, o Rafinha mantém o nome informado, explica a falta de informação e continua pedindo dados úteis. O modelo textual não identifica fotos automaticamente.

Arquivos principais: `assistant_language.py`, `assistant_state.py`, `assistant_knowledge.py`, `assistant_engine.py`, `assistant_emotions.py`, `assistant_research.py`, `test_assistant_language.py` e `test_hybrid_assistant.py`. Nenhuma migração adicional foi necessária: os novos campos da sessão têm defaults e usam o JSON de memória existente.

## Continuidade da conversa — revisão dos novos prints

A apresentação e o atalho de conexão pessoal aparecem somente antes da primeira mensagem. A engrenagem continua abrindo as configurações durante a conversa. Nas respostas curtas sobre ambiente, luz e rega, o assistente confirma a informação e avança para o próximo campo pendente. As fontes consultadas continuam disponíveis sem repetir a apresentação da pesquisa ou consultar novamente a rede.

Pedidos como “gostaria de saber qual é a melhor planta para apartamento” buscam opções do catálogo compatíveis com ambiente interno; não viram nomes de plantas nem reutilizam automaticamente uma planta externa discutida antes. Uma resposta sobre a luz refina as opções, mantendo a distinção entre recomendação e planta identificada.

Períodos como “durante uma semana”, artigos isolados e referências ao espaço não são identidades botânicas. O relato de esquecimento de rega mantém o nome informado, registra o período declarado e usa uma expressão preocupada. Mudar de roseira para orquídea limpa os dados e a referência da planta anterior, sem criar uma segunda planta a partir da descrição.

Validação desta revisão: **190 testes de linguagem e assistente**, **nove testes do Rafinha no navegador**, compilação do frontend e Ruff aprovados. A pesquisa dos testes usa fontes simuladas; não foram realizadas chamadas pagas de IA nem alterados cadastros comerciais.
