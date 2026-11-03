# Fotos e interface — 10 de outubro de 2026

As fotos privadas anexadas ao Rafinha agora são enviadas como conteúdo visual à conta ChatGPT autorizada, junto do histórico da conversa. Até três imagens estáticas JPEG, PNG, WebP ou GIF são aceitas, com os limites existentes de 5 MB e 16 milhões de pixels por arquivo. A orientação é corrigida e os metadados EXIF são retirados da cópia enviada; os pixels são preparados em memória até 2048 × 2048. O upload não fica público, os dados não são incorporados às mensagens salvas e somente o dono da conversa pode acessá-los. Sem conexão disponível, o Rafinha informa que a análise visual não ocorreu.

O botão **Minimizar Rafinha** mantém conversa, fotos e rascunho. O botão **Fechar conversa do Rafinha** continua encerrando e limpando a conversa. Fechar durante um upload invalida sua continuação e impede uma resposta tardia de recriar o diálogo. As preferências carregam antes de abrir a janela para evitar que os valores iniciais substituam opções já salvas.

O fundo usa `#e4c8a3`, com camadas suaves e cartões claros. Nove imagens ilustrativas novas, de 1536 × 1024, substituem os pequenos recortes de serviços e categorias. As fotografias de projetos existentes também são usadas nos serviços relacionados. Vinte e uma fotos botânicas recebem versões de maior resolução de fontes com licença aberta. Os originais são preservados, e os novos créditos acompanham cada foto no catálogo. A atualização versionada altera somente fotos previamente incluídas no catálogo; mantém uploads próprios, descrições, preços, estoque e movimentações.

Na aba **Descrição**, os textos do produto e da espécie são comparados ignorando diferenças de caixa e espaçamento. Textos equivalentes aparecem uma vez; descrições diferentes continuam disponíveis.

O fluxo permanece somente ChatGPT, com a conta autorizada desta instalação. A distribuição pública continua usando o cofre separado `RafinhaPublic` e exige autorização própria para analisar fotos ou usar o modelo. Não usa a conta do desenvolvedor, Ollama, Tavily ou API paga alternativa.

## Verificação

- 522 testes de backend e distribuição aprovados; teste adicional do transporte após o ajuste das instruções de pesquisa aprovado.
- Interface conferida no desktop e em 390 × 844, com fotografias decodificadas antes das capturas.
- 21 cenários distintos de navegador aprovados, incluindo minimização, histórico, preferências, fechamento durante o upload, descrições iguais e diferentes, fotos e layout administrativo. Os cenários afetados pelas últimas alterações também foram repetidos.
- Análise real de uma foto pública de hibisco pela conta autorizada: características visíveis e hipótese de identificação, em 8,66 segundos. A conversa e o anexo temporários foram apagados.
- Registro local do teste real: `.local/vision-live-result.json`, sem credenciais nem dados da imagem.

Contrato visual: [documentação oficial de imagens na Responses API](https://developers.openai.com/api/docs/guides/images-vision).

## Distribuição atualizada

- ZIP: `release/windows/20261010-160254/AtelieVerde-Windows.zip` (177.451.828 bytes).
- SHA256: `a3d71af188f8c88fd91c4f01df6dceedfe88b01fb3b3d6abb3aa7d01cab69d9b`.
- Os 1.003 arquivos do ZIP foram comparados com os da pasta verificada.
- Scanner: 1.001 arquivos, 1.929 entradas compiladas e 242 recursos públicos, sem achados. Comparação de três segredos locais sem expor seus valores.
- Teste da instalação pública: 13 verificações aprovadas, incluindo conta ChatGPT bloqueada até login próprio; zero chamadas externas.
- Portal final reiniciado em `http://127.0.0.1:5173`; API saudável, ChatGPT conectado e 21 fotos atualizadas confirmadas no catálogo.
