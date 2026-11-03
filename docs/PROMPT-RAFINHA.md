# Prompt completo — Rafinha no Ateliê Verde

Copie o texto abaixo para o Codex em `C:\Projetos\GreenScape`.

---

Implemente no projeto existente **Ateliê Verde**, em `C:\Projetos\GreenScape`, um assistente virtual de jardinagem chamado **Rafinha**. Quero uma funcionalidade integrada à aplicação e ao banco, com a identidade visual das referências fornecidas. Aproveite a arquitetura e as regras atuais. Execute a implementação e a validação, não entregue somente um plano ou uma tela estática.

## 1. Conceito e experiência

O Rafinha é um pequeno jardineiro ilustrado que acompanha o cliente no portal. Ele fica no canto inferior direito, gesticula discretamente, muda de expressão e conversa por um balão ao seu lado. A inspiração são os diálogos de personagens em jogos antigos e histórias em quadrinhos, com acabamento profissional e discreto.

O cliente escreve dúvidas sobre plantas, cuidados, técnicas de plantio ou seu planejamento paisagístico. O Rafinha responde usando informações reais do sistema. O texto aparece progressivamente, como se estivesse sendo escrito. A experiência deve ser acolhedora, divertida e simples, sem interromper a navegação. **A voz não é obrigatória: priorize personagem, expressões, balões e texto.**

## 2. Referências fornecidas

Leia os arquivos em `docs/referencias/rafinha/`:

- `Rafinha.jpeg`: identidade principal do personagem.
- `Espressões do Rafinha.jpeg`: folha com doze poses e expressões.
- `Logo empresa.jpeg`: identidade visual da marca.
- `Audio 1.ogg`, `audio 2.ogg`, `Audio 3.ogg`, `Audio4.ogg` e `Audio 5.ogg` até `Audio 10.ogg`: briefing da ideia.

A transcrição automática dos dez áudios está em `docs/rafinha-audios-transcricao.json`. Pode conter erros de reconhecimento; confronte termos estranhos com o contexto e as imagens. O nome adotado é **Rafinha**. “Netinho” foi outra alternativa discutida, não um segundo personagem.

Os áudios são conversas pessoais de briefing, não falas prontas para reprodução no aplicativo. Não os publique, não os use como trilha sonora nem faça clonagem de voz. Comentários sobre ferramentas, limites e horários nas conversas não são requisitos do produto.

Preserve cabelo escuro com mechas claras, óculos, barba, camisa clara, avental verde, luvas e ferramentas de jardinagem. Prepare poses individuais com fundo transparente, margens uniformes e boa resolução. Se precisar gerar ou editar imagens, utilize a ferramenta de imagens disponível e preserve a identidade. Salve os assets finais no projeto, sem depender da pasta Downloads.

Não use a folha inteira como avatar. Cada pose deve aparecer inteira, sem partes das poses vizinhas, fundos retangulares, contornos serrilhados ou aparência pixelada. O logotipo ilustrado completo pode aparecer na apresentação do assistente ou em uma área institucional; mantenha a marca do cabeçalho compacta e legível.

## 3. Arquitetura e preservação do projeto

Inspecione o repositório, suas instruções, README e documentação antes de alterar. Reutilize React, TypeScript, Vite, FastAPI, SQLAlchemy, JWT, Alembic e os componentes existentes. Preserve a compatibilidade com SQLite local e PostgreSQL.

Integre com as espécies, produtos, serviços, guias de **Aprender** e planejador paisagístico virtual. As espécies já possuem luminosidade, rega, porte, ambiente, dificuldade, descrição, cuidados, substrato, propagação, precauções, fotos e fontes. Os guias possuem seções e referências. Não crie outra biblioteca desconectada.

Preserve vendas, estoque, clientes, fornecedores, imagens, documentos, orçamentos e projetos. Não recrie o banco nem sobrescreva registros existentes. Faça backup antes de migrações e alterações persistentes. Dados demonstrativos novos não devem gerar faturamento fictício ou movimentos de estoque sem uma operação real.

Mantenha o banner compacto e a faixa de benefícios fixa da loja. No computador, preserve a ausência de rolagem geral da página: mensagens e conteúdo excedente devem rolar dentro de suas áreas. O assistente não pode criar barras horizontais.

## 4. Widget e interface

Crie um componente reutilizável, como `RafinhaAssistant`, integrado ao portal do cliente. Não adicione outra aba principal: um personagem discreto e um botão acessível devem abrir a conversa. A área Aprender também pode oferecer um convite contextual.

Estados obrigatórios:

- **Recolhido:** avatar pequeno e “Fale com o Rafinha”.
- **Aberto:** personagem, apresentação, balão, histórico e entrada de mensagem.
- **Pensando:** expressão pensativa e indicação de processamento.
- **Respondendo:** texto progressivo e pose amigável.
- **Concluído:** orientação, referências e ações relacionadas quando pertinentes.
- **Indisponível:** aviso claro, tentar novamente e orientações do catálogo.

Inclua enviar, recolher, nova conversa, histórico, excluir conversa e interromper resposta em andamento. Enter envia e Shift+Enter quebra linha. Bloqueie mensagens vazias e duplicação acidental. Preserve a conversa ao navegar entre as abas.

Limite o painel ao viewport, com entrada sempre acessível e rolagem somente no histórico. No celular, use um painel compacto ou folha sobreposta que considere teclado e áreas seguras. Não cubra confirmação de compra, orçamento, controles do planejador ou modais: recolha o widget nesses contextos.

Use os verdes, tons claros e tipografia atuais. Evite mascote gigante, sombras fortes e efeitos permanentes. Ofereça ocultar o personagem durante a sessão e desativar animações. O assistente deve enriquecer o portal sem deixá-lo poluído.

## 5. Expressões, movimento e efeito de escrita

Crie um mapa de assets para estados como `welcome`, `idle`, `thinking`, `explaining`, `happy`, `concerned`, `surprised` e `sleeping`, escolhendo poses da referência. Não use raiva ou irritação para repreender o cliente. Não é necessário dar uma função a todas as doze poses.

CSS e transições entre poses são suficientes para o MVP: saudação, pequena inclinação e movimento discreto ao responder. Não é necessário produzir vídeos ou sincronização de boca. Evite movimento contínuo enquanto o cliente preenche formulários.

Implemente texto progressivo sem alterar a resposta. Inclua “Mostrar resposta completa”. Respeite `prefers-reduced-motion`, acentos, emojis e caracteres compostos. Leitores de tela devem receber frases compreensíveis, não anúncios a cada caractere. Limpe timers e requisições ao interromper, fechar ou trocar de conversa.

## 6. Conhecimento e personalidade

O Rafinha deve ajudar com cuidados, luminosidade, rega, solo, adubação, poda, manutenção e plantio. Atenda cactos, suculentas, frutíferas e todos os demais grupos presentes no catálogo. Ajude a escolher espécies conforme espaço, ambiente, luz e disponibilidade para manutenção.

Também explique os serviços, indique guias de Aprender e ajude o cliente a entender as plantas selecionadas no próprio planejamento virtual. Identificação de plantas por fotografia pode ficar documentada como evolução futura; não simule reconhecimento visual neste MVP.

Use português brasileiro, tom acolhedor e respostas curtas. Faça uma pergunta útil por vez quando faltarem dados: qual espécie, vaso ou solo, sol recebido, drenagem ou rotina de cuidados. Use emojis com moderação e evite bordões repetitivos.

Apresentação sugerida:

“Oi! Eu sou o Rafinha, o assistente virtual do Ateliê Verde 🌿 Posso ajudar com cuidados das plantas, ideias para seu jardim e nossos serviços. O que vamos cuidar hoje?”

Apresente-o como assistente virtual, sem afirmar que há uma pessoa respondendo ao vivo ou que substitui a revisão do paisagista. Reconheça quando não houver informação suficiente. Não dê diagnóstico definitivo com base em uma descrição genérica nem invente produtos químicos ou dosagens ausentes das fontes.

Sugestões iniciais: “Como cuidar da minha planta?”, “Quais plantas combinam com meu espaço?”, “Quero planejar meu jardim” e “Conhecer os serviços”. Recomende produtos apenas quando forem pertinentes, não em toda resposta.

Ao citar preços, estoque, disponibilidade e serviços, consulte os dados atuais. Não invente plantas cadastradas, descontos, avaliações, prazos, contratação ou links. A expressão visual deve vir de estados validados da aplicação, nunca de um arquivo ou comando arbitrário retornado pelo modelo.

## 7. IA local e recuperação de conteúdo

Quero evitar dependência obrigatória de serviços pagos ou assinaturas externas. Implemente uma camada de provedores no FastAPI com **inferência local via Ollama** e um modo de orientações do catálogo quando o modelo estiver indisponível.

O FastAPI chama a API local. O navegador conversa somente com o backend da aplicação. Configure host e modelo por variáveis de ambiente, sem chaves no frontend. Não escolha modelos em nuvem por engano nem envie conversas a serviços externos por padrão.

Verifique ferramentas e recursos já instalados. Escolha um modelo compatível com português e o hardware disponível, sem fixar um nome não testado. Se runtime ou pesos estiverem ausentes, entregue a integração, testes com provedor controlado e instruções reproduzíveis para ativação. Não declare inferência real validada sem executá-la. Não baixe modelos grandes silenciosamente nem torne o modelo obrigatório para iniciar a loja.

Recupere contexto do banco: espécies, guias e trechos relacionados à dúvida. Inclua identificadores e fontes reais no contexto do modelo. Comece com busca simples e bem testada; não introduza banco vetorial ou infraestrutura pesada sem necessidade.

Quando não houver modelo, responda com orientações estruturadas, perguntas guiadas e links dos registros existentes. Identifique esse modo como **“Orientações do catálogo”**, sem fingir inferência generativa. Se a base não permitir responder, indique consultoria.

Implemente timeout, limite de mensagem e histórico, cancelamento e tratamento de falhas. Se a IA estiver fora do ar, compra, consulta ao catálogo e criação de orçamento continuam funcionando.

## 8. Integrações e ações

No detalhe de uma espécie ou produto, ofereça “Perguntar ao Rafinha sobre esta planta”. Em Aprender, permita perguntar sobre o guia aberto. No planejador, permita dúvidas sobre as espécies selecionadas e ajuda para completar o levantamento.

Envie identificadores de contexto, não cópias arbitrárias de dados. Mostre o contexto utilizado e permita removê-lo. O backend deve consultar e autorizar os registros solicitados.

Retorne ações estruturadas e limitadas, como `open_species`, `open_product`, `open_article`, `open_service` e `request_quote`, com IDs reais. Valide no servidor e no cliente. As ações devem abrir as telas existentes, preservando o serviço selecionado.

Uma sugestão de mudança no levantamento deve ser apresentada para revisão e aplicação pelas regras atuais do planejador. Não altere automaticamente plantas, quantidades, área ou orçamento durante uma conversa. Respeite revisões e estados editáveis.

Preserve **solicitação → proposta → aprovação → projeto**. O Rafinha não aprova orçamentos, cria cobranças, modifica estoque nem confirma uma contratação sozinho.

## 9. Backend, API e banco de dados

Crie um módulo próprio para rotas, recuperação de conteúdo, provedor e validação. Separe responsabilidades e reutilize autenticação e erros existentes.

Persistência mínima:

- `AssistantConversation`: proprietário, título, criação e atualização.
- `AssistantMessage`: conversa, papel, texto, horário, fontes, contexto e ações validadas; estado final ou interrompido quando necessário.
- Preferências: assistente habilitado, movimento, escrita progressiva e voz opcional.

Use Alembic, chaves estrangeiras e índices. Reutilize mecanismos de preferências existentes quando adequados. Preserve compatibilidade com SQLite e PostgreSQL.

Rotas sugeridas, adaptáveis ao padrão do repositório:

- `GET /api/assistant/status`: modo ativo e disponibilidade, sem segredos.
- `POST /api/assistant/conversations`: abrir conversa.
- `GET /api/assistant/conversations`: listar conversas próprias.
- `GET /api/assistant/conversations/{id}`: histórico próprio.
- `POST /api/assistant/conversations/{id}/messages`: enviar e receber resposta.
- `DELETE /api/assistant/conversations/{id}`: excluir conversa própria.
- Leitura e atualização das preferências do próprio usuário.

A resposta completa com animação no frontend é suficiente. Streaming pode ser adicionado se ajudar, mas não é condição para o texto progressivo. Envios concorrentes ou repetidos não devem duplicar respostas nem misturar conversas.

Use JWT e autorização nas rotas privadas. Cada cliente acessa apenas suas conversas e seus próprios orçamentos e projetos. Não forneça ao modelo dados administrativos, custos de fornecedores, informações de outros clientes ou um despejo do banco.

Mensagens e conteúdo recuperado são dados, não comandos que autorizam consultas ou alterações adicionais. Não permita SQL, comandos de sistema nem acesso irrestrito a ferramentas pelo modelo. Valide ações contra uma lista permitida, renderize mensagens sem HTML arbitrário e evite conteúdo integral das conversas em logs técnicos.

## 10. Administração e voz opcional

Acrescente uma seção compacta nas Configurações existentes: habilitar Rafinha, mensagem inicial, perguntas sugeridas, disponibilidade e teste do atendimento. Não crie outra barra lateral nem novos KPIs no dashboard.

Host do provedor e segredos ficam no ambiente do servidor. Textos de apresentação devem ser configuráveis sem editar código. Não crie uma tela administrativa de exposição de conversas privadas por padrão; atendimento humano exigiria um fluxo próprio.

Após finalizar o chat por texto, se for simples e compatível, ofereça “Ouvir resposta”, desligado por padrão. O texto deve continuar completo se a voz não estiver disponível. Não reproduza som automaticamente, não use os áudios pessoais como respostas e não solicite microfone para usar o chat por texto. Não faça clonagem de voz.

## 11. Execução e validação

Implemente em etapas utilizáveis: assets e widget; conversa com recuperação do catálogo; provedor local e fallback; histórico, preferências e integrações; testes e documentação.

Teste regras relevantes: isolamento entre dois clientes, persistência e exclusão do histórico, recuperação de espécies e guias, contexto autorizado de projeto, provedor ausente ou lento, ações inválidas e ausência de mutações comerciais durante o chat. Não crie testes que apenas repitam detalhes triviais de CSS.

Use Playwright para abrir/recolher, enviar/continuar, navegar entre abas, escolher sugestões, abrir links, interromper escrita e usar teclado. Confira zoom de 100% em **1852×964, 1366×768 e 390×844**. Personagem, balões e controles devem caber sem cortes nem sobrepor ações importantes. Verifique redução de movimento e acesso por leitor de tela.

Execute build TypeScript/Vite, verificações Python apropriadas, migrações e testes afetados. Capture telas e confira visualmente. Execute a verificação existente de consistência dos dados para confirmar preservação dos registros comerciais.

Documente arquitetura, configuração, modelo efetivamente testado, modo sem modelo, comandos e limitações verificadas. Atualize `.env.example` e README sem segredos.

## 12. Critérios de conclusão

1. Rafinha aparece inteiro, nítido e fiel às referências.
2. Cliente escreve uma dúvida e recebe orientação relacionada ao catálogo.
3. Expressões, balões e escrita progressiva funcionam com acessibilidade.
4. Integração local e modo de catálogo estão implementados; o modo realmente disponível está identificado.
5. Informações e links correspondem aos dados reais do sistema.
6. Conversas e preferências são persistidas e isoladas por cliente.
7. Integrações abrem telas existentes e preservam o fluxo comercial.
8. Computador e celular continuam utilizáveis, sem novos cortes ou sobreposições.
9. Dados anteriores permanecem preservados e verificações relevantes passam.

Ao terminar, informe entregas, modo de uso, validações e dependências ainda indisponíveis. Mostre um resultado concreto e avance autonomamente dentro do escopo autorizado; pergunte somente quando uma decisão for realmente indispensável.

## Referências técnicas

Confira a documentação oficial e compatibilidade com as versões do projeto antes de implementar:

- Inferência local e API: https://docs.ollama.com/api/introduction
- Reprodução de áudio e bloqueio de autoplay: https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/play

---

Nota: este prompt consolida os dez áudios e as três imagens. Especificações de API, persistência, acessibilidade e testes são propostas para transformar o briefing em uma funcionalidade integrada, não transcrições literais dos áudios.
