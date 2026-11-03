# Rafinha — assistente do Ateliê Verde

A arquitetura atual, com memória estruturada, pesquisa institucional, anexos privados e limite operacional de dez segundos, está documentada em [RAFINHA-HIBRIDO.md](RAFINHA-HIBRIDO.md). As descrições abaixo também registram a primeira implantação; a revisão híbrida prevalece para tempo, estados e expressões.

Validação em 05/10/2026: build TypeScript/Vite e Ruff aprovados; suíte geral de backend com 62 casos e, após os últimos refinamentos, os dez casos do módulo de assistente aprovados; 27 testes de navegador aprovados. Migração de banco vazio e upgrade do banco existente aprovados, sem diferenças pendentes no Alembic. Registros comerciais e anexos comparados com o backup e preservados; a verificação de consistência retornou zero erros e zero avisos. PostgreSQL, Docker e inferência de modelo instalado não foram executados localmente.

O portal do cliente apresenta o Rafinha no canto inferior direito. Clique em **Fale com o Rafinha**, escreva uma pergunta e envie com Enter. Shift+Enter cria uma linha. O histórico pertence à conta autenticada e acompanha a navegação. Cada conversa pode ser retomada ou excluída.

Na página de produto, biblioteca, guia de Aprender e memorial do planejamento, os botões **Perguntar ao Rafinha** abrem uma conversa com contexto. É possível remover esse contexto. Informações comerciais vêm do cadastro atual. As ações abrem produtos, espécies, guias, serviços e a solicitação de orçamento correspondente; conversar não contrata serviços, aprova orçamentos nem altera estoque ou finanças.

## Experiência e preferências

O personagem usa cinco poses PNG individuais: saudação, pensamento, explicação, alegria e atenção. As reações são contextuais: relatos de falta de rega, murcha ou folhas amareladas recebem uma expressão de preocupação; agradecimento e melhora recebem alegria. São reações de empatia, sem afirmar um diagnóstico. A pose é mantida durante a resposta, com pelo menos 1,5 segundo no estado de consulta. A escrita progressiva pode ser dispensada com **Mostrar resposta completa**. O sistema respeita redução de movimento e navegação por teclado. A área de mensagens possui rolagem própria.

O diálogo foi ampliado e a apresentação aparece em um balão, com o personagem à esquerda. Ao fechar ou seguir uma ação que encerra o diálogo, a conversa ativa é excluída, a tela é limpa e a próxima abertura começa vazia. Históricos anteriores à mudança não são apagados em massa, nem carregados automaticamente. Modais de compra, orçamento e planejamento também encerram a conversa ativa.

Use a engrenagem para ajustar movimento, escrita e a opção de voz. O usuário pode ocultar o personagem durante a sessão ou desativá-lo para sua conta. Para reabrir ou reativar, use **Menu da conta → Rafinha · preferências e conversa**. A voz é opcional: o botão só aparece quando o navegador oferece uma voz local em português e a preferência está habilitada. Não há reprodução automática, acesso ao microfone ou clonagem de voz.

Em **Administrador → Configurações**, a seção do Rafinha permite habilitar o assistente, editar apresentação e sugestões e testar uma pergunta sem criar uma conversa ou mexer em vendas. Conversas privadas não são exibidas nessa seção.

## Modo disponível nesta máquina

Após a instalação do Ollama pelo usuário em 05/10/2026, foi configurado o modelo local **qwen3:4b**. Uma resposta real sobre Lavanda foi validada usando os dados do catálogo. O modelo está rodando na CPU, sem memória de GPU utilizada; os testes levaram aproximadamente 44 a 72 segundos. O tempo varia conforme carga e hardware. O modo **Orientações do catálogo** continua como alternativa quando a inferência falha ou excede o limite.

A integração também foi verificada com transporte HTTP controlado, incluindo resposta válida, timeout, JSON inválido e preço inventado. O Codex utilizou o modelo que já estava instalado; não contratou serviço externo nem baixou outros pesos.

A configuração local está em `.local/rafinha-provider.json` e é carregada por `scripts/iniciar.ps1` quando não há variáveis de ambiente explícitas. O arquivo não contém credenciais e não é incluído no repositório. A configuração por variáveis de ambiente continua disponível.

## Ativar inferência local

1. Instale o Ollama conforme a [documentação oficial](https://docs.ollama.com/api/introduction).
2. Escolha e instale explicitamente um modelo local compatível com português e com a memória disponível. O tamanho do download e o consumo de memória dependem do modelo escolhido. Não use um modelo com sufixo `:cloud`.
3. Confirme que o modelo está presente com `ollama list` e valide uma pergunta em português com `ollama run NOME_DO_MODELO`.
4. Defina as variáveis abaixo no ambiente usado para iniciar o backend. O projeto não carrega automaticamente `.env.example`.

```powershell
$env:RAFINHA_PROVIDER = 'auto'
$env:RAFINHA_OLLAMA_URL = 'http://127.0.0.1:11434'
$env:RAFINHA_OLLAMA_MODEL = 'NOME_EXATO_DO_MODELO_INSTALADO'
cd C:\Projetos\GreenScape
& .\scripts\parar.ps1
& .\scripts\iniciar.ps1 -NoBrowser
```

Depois, verifique a seção administrativa de teste. Uma resposta efetivamente produzida pelo modelo recebe a indicação **IA local**. Se o modelo não estiver disponível, se falhar ou retornar conteúdo inválido, a resposta usa o catálogo e identifica esse modo.

Para manter somente o catálogo, configure `RAFINHA_PROVIDER=catalog`. O backend chama o serviço de modelos; o navegador não acessa o Ollama diretamente. O host aceita apenas endereços locais previstos, não é editável pelo cliente e não usa proxy do ambiente. Nenhum segredo é enviado ao frontend.

No Docker, `localhost` é o contêiner do backend. Para um Ollama no host, configure `RAFINHA_OLLAMA_URL=http://host.docker.internal:11434` com o serviço local acessível ao contêiner; no Linux configure o mapeamento de host apropriado. Esse caminho não foi executado localmente.

## Estrutura e limites

- `assistant.py`: rotas, configuração, preferências, histórico e reservas atômicas por conversa.
- `assistant_knowledge.py`: recuperação autorizada de conteúdo e respostas do catálogo.
- `assistant_provider.py`: chamadas locais limitadas, sem download ou fallback em nuvem.
- `RafinhaAssistant.tsx`: widget, histórico, contexto, ações e configuração administrativa.
- Migração `a51005af0001`: quatro tabelas novas, sem alteração dos registros comerciais.

Uma conversa admite até 100 trocas; uma conta, até 100 conversas. Mensagens têm até 2.000 caracteres. A resposta validada tem até 4.000 caracteres. O provedor recebe contexto limitado e até seis mensagens anteriores, não dados de fornecedores ou outras contas. Cancelamento invalida a reserva no banco, evitando persistência tardia da resposta; o serviço local pode terminar sua requisição corrente antes do timeout de 75 segundos. Uma reserva abandonada expira após 90 segundos.

As ações e fontes são construídas pelo servidor a partir de registros recuperados, não executadas livremente pelo modelo. Valores monetários retornados pelo modelo são conferidos contra o contexto. Um modelo generativo ainda pode produzir texto impreciso; não há garantia de diagnóstico botânico. O catálogo sempre oferece a orientação estruturada como alternativa.

Identificação por fotografia, atendimento humano e animação labial não fazem parte desta versão. Os áudios do briefing ficam apenas nas referências de desenvolvimento e não estão no diretório público.

## Imagens e marca

O original de **Logo empresa correto.jpeg** continua preservado em `frontend/public/rafinha/atelie-verde-logo.jpeg`. A versão usada no login e no cabeçalho do cliente é `atelie-verde-logo-transparent.png`: apenas o fundo externo claro foi removido pela ferramenta integrada de imagens, preservando a cena interna e o lettering. Não há nome duplicado ao lado nesses locais. No computador, o logo grande fica no alto à esquerda do painel da foto, com a frase principal abaixo; o texto “Da primeira planta ao jardim dos sonhos…” fica no canto inferior direito do mesmo painel. No celular, a marca aparece acima do formulário. O retrato ilustrado e a folha de expressões serviram como referência para cinco cutouts transparentes individuais; a imagem do logo não foi utilizada para gerar os personagens.

Prompts e inventário: [RAFINHA-ASSETS.md](RAFINHA-ASSETS.md). Referências originais em `docs/referencias/rafinha`; transcrição em `docs/rafinha-audios-transcricao.json`.
