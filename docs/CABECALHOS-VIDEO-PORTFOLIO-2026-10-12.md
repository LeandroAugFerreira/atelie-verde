# Cabeçalhos, narração e portfólio — 12/10/2026

## Administração

Todas as dez abas administrativas usam um container claro no título e subtítulo, com opacidade de 97%, borda suave, cantos de 16 px e texto verde escuro. A regra está em `frontend/src/admin.css`, aplicada ao componente compartilhado `PageTitle`. Os controles do cabeçalho continuam na mesma região e se reorganizam no celular.

Conferidos: Dashboard, Estoque, Fornecedores, Clientes, Serviços, Orçamentos, Projetos, Financeiro, Relatórios e Configurações. A conferência mobile usou 390 px. Evidências: `.local/admin-cabecalhos/`.

## Apresentação revisada

O vídeo foi regravado com as telas atualizadas. A nova narração usa Kokoro-82M / ONNX, voz brasileira `pf_dora`, velocidade 0,94, capítulos sintetizados de forma contínua e pausas de frase de 0,22 s. As legendas usam o alinhamento fonético emitido pelo modelo, preservando os dois idiomas.

A tentativa de voz Microsoft Thalita foi recusada pelo serviço com HTTP 403. A alternativa local evita essa dependência. Nenhuma API paga ou credencial pessoal foi usada para gerar a nova voz.

Arquivos finais: `release/video/final-v2/`. A prévia anterior em `previa-v1/` foi preservada.

- Duração: 128,434 s (2min08s).
- Vídeo: H.264, 1920 × 1080, pixels quadrados, 24 fps.
- Áudio: AAC, 48 kHz; -19,6 LUFS; pico verdadeiro -1,9 dBFS.
- Dez capítulos e vinte legendas em cada idioma, Português BR e English.
- Tamanho: 25.528.111 bytes.
- SHA-256: `2f7348070eb70654f5e9b2ef6de140824cb714976494b504ea0bdc160eba27e9`.
- Decodificação completa sem erros, volume e sincronização conferidos.

Para reproduzir:

```powershell
.\.venv\Scripts\python.exe scripts\narrar_video_suave.py
node .local\video-apresentacao-v2\gravar.mjs
.\.venv\Scripts\python.exe scripts\montar_video.py --version v2
.\.venv\Scripts\python.exe scripts\validar_video.py --version v2
```

As ferramentas e modelos ficam em `.local/`, fora da aplicação e do executável. Modelo: https://huggingface.co/hexgrad/Kokoro-82M. Integração: https://github.com/thewh1teagle/kokoro-onnx. O modelo possui licença Apache 2.0 e a integração possui licença MIT.

## Distribuição Windows

Pasta: `release/windows/20261012-000006/`.

- ZIP: 231.721.462 bytes.
- SHA-256: `d79532e3eaacf0f3d9545d9f91268def89f092229f6189aaf7d005f0424ab5c2`.
- Build TypeScript/Vite aprovado; pacote verificado com zero achados de segredos.
- Treze verificações de instalação isolada passaram, com zero chamadas externas.
- Cofre público vazio e separado do desenvolvimento; ChatGPT exige a própria autorização da instalação.

Release: https://github.com/LeandroAugFerreira/leandroaugferreira.github.io/releases/tag/atelie-verde-2026.10.12

## Portfólio

O vídeo foi integrado ao card e à página completa, no tamanho padrão do player do NexoLog. Inclui reprodução/pausa, Português BR, English e opção sem legendas. Os três espaços reservados foram preservados. A captura administrativa e o download foram atualizados.

Quinze conferências locais do player e layout passaram, incluindo a navegação por tempo e os layouts mobile. Evidências: `.local/portfolio-20261012/`.

- PR integrado: https://github.com/LeandroAugFerreira/leandroaugferreira.github.io/pull/5
- Commit integrado: `293f3e588fdc23e3ebcd52ecf3163cac9f4c1170`.
- Página: https://leandroaugferreira.github.io/atelie-verde.html#apresentacao
- Card: https://leandroaugferreira.github.io/index.html#atelie-verde

GitHub Pages: workflow `38200310802`, concluído com sucesso. O download público respondeu HTTP 200, com o mesmo tamanho do pacote local. As quinze verificações do player foram repetidas na publicação e passaram sem erros, incluindo os dois idiomas, navegação por tempo, layout mobile e preservação dos três espaços reservados.
