# Vídeo de apresentação — prévia para avaliação

A apresentação mostra o Ateliê Verde em uso: loja, filtros do catálogo, imagens ampliadas das plantas, acessórios individuais, serviços, projetos com planta 2D, Rafinha, dashboard, estoque e financeiro.

A narração em português brasileiro usa a mesma voz neural do vídeo do NexoLog: `pt-BR-FranciscaNeural`, com ritmo de `-3%`. O texto público do roteiro é enviado ao serviço de voz da Microsoft. As ferramentas ficam em `.local/video-tools`, separadas das dependências da aplicação.

O roteiro bilíngue está em `docs/roteiro-video.json`. Os tempos das legendas são calculados a partir da duração de cada trecho de voz. Há duas faixas no MP4, além de WebVTT e SRT em português BR e inglês.

As cenas são gravações do navegador, com interações reais e dados demonstrativos. A gravação utiliza 1440 × 810 e a montagem gera 1920 × 1080, proporção 16:9, pixels quadrados, H.264 e áudio AAC. Um indicador de cursor é adicionado somente na gravação. O contexto do navegador é temporário; as conversas criadas para o vídeo são encerradas ao fim da cena do Rafinha.

## Arquivos para avaliar

Pasta: `release/video/previa-v1/`.

- `avaliacao.html`: player local com escolha de idioma e capítulos.
- `atelie-verde-apresentacao.mp4`: vídeo, narração e legendas internas.
- `atelie-verde-pt.vtt` / `atelie-verde-en.vtt`: legendas para o navegador.
- `atelie-verde-pt.srt` / `atelie-verde-en.srt`: legendas para outros players.
- `capitulos.json`: tempos dos dez capítulos.
- `validacao.json`: verificação da exportação e do áudio.

Para abrir a prévia com navegação pelo tempo:

```powershell
.\.venv\Scripts\python.exe scripts\preview_video.py
```

Acesse `http://127.0.0.1:18818/avaliacao.html`.

## Reproduzir a produção

```powershell
.\.venv\Scripts\python.exe scripts\narrar_video.py
node .local\video-apresentacao-v1\gravar.mjs
.\.venv\Scripts\python.exe scripts\montar_video.py
.\.venv\Scripts\python.exe scripts\validar_video.py
```

O montador aproveita os capítulos já renderizados quando a gravação e a narração permanecem iguais. Para refazer somente uma cena, passe seu identificador ao gravador; por exemplo, `gravar.mjs projetos`.

## Publicação pendente

O usuário pediu avaliação e autorização antes de colocar o vídeo na capa, seguindo o player do NexoLog. Nenhuma alteração do player nem upload do vídeo ao portfólio foi realizado nesta etapa. Depois da aprovação, integrar o MP4 e as duas faixas WebVTT ao card do Ateliê Verde e à apresentação da página do projeto, mantendo o tamanho e o padrão dos demais cards.

## Resultado da conferência

Prévia de 2min33s, Full HD, 24 quadros por segundo, com dez capítulos e vinte legendas em cada idioma. O MP4 possui 26.535.500 bytes. Vídeo e áudio foram decodificados por completo sem erros. Volume integrado: -17,9 LUFS; pico verdadeiro: -2,0 dBFS.

O player foi conferido com reprodução, pausa, salto de capítulo, legendas Português BR / English / desativadas e largura mobile de 390 px. As capturas com os dois idiomas foram inspecionadas.

SHA-256: `0de7e3c03c20b3cacc680d7849de5ed0f095db758e1d3b8742074034e5629464`.
