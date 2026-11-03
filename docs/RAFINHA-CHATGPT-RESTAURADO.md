# Rafinha com ChatGPT — 9 de outubro de 2026

O modo ativo é `RAFINHA_MODE=chatgpt`. A conversa volta à conta ChatGPT autorizada, com contexto e histórico, usando o endpoint público Responses API. O fluxo não tenta Ollama, Tavily ou uma chave API paga quando a conta falha. O catálogo é a alternativa limitada quando não há conexão disponível.

## Conexão

No portal administrativo, abra Configurações → Inteligência Artificial → Continuar com ChatGPT. A autorização ocorre no navegador oficial, com PKCE, validação de identidade e escopo para usar o plano. Elegibilidade e limites são determinados pela OpenAI. [Documentação oficial](https://developers.openai.com/siwc/token-sharing-open-source/sign-in).

O modelo salvo da conta é preservado. Preferências de limite diário, prazo e pesquisa são opcionais e persistem no cofre; nenhuma chave precisa ser colocada no frontend. A conta selecionada atende às conversas locais da instalação, enquanto dados comerciais privados continuam respeitando as permissões de cada usuário.

As respostas usam `store=false` e streaming até o evento de conclusão. [Contrato oficial de inferência](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).

## Pesquisa

Dúvidas gerais podem ser respondidas pelo modelo sem pesquisa. Identificação por pistas, informações recentes e questões que exigem verificação podem solicitar a ferramenta web, conforme as preferências da conta. Falhas temporárias da ferramenta permitem uma tentativa de conversa sem pesquisa, dentro do mesmo prazo e limite de consultas. Não é acionada uma API paga alternativa.

## Executável público

- Nenhum token, `.env`, banco do desenvolvimento ou cofre é copiado para o pacote.
- O executável ignora as configurações de desenvolvimento e usa `%LOCALAPPDATA%\AtelieVerde\RafinhaPublic`, separado da conexão local de desenvolvimento.
- Sem autorização própria, a instalação começa em modo catálogo, sem consumir a conta do desenvolvedor.
- Uma seleção protegida associa o perfil à geração atual da credencial. Desconectar ou substituir a conexão invalida a seleção anterior.
- Configuração de conta exige administrador e acesso local. Pedidos de origens externas não consomem a conexão.

Tokens ficam no armazenamento local protegido, e a renovação é serializada para evitar concorrência com tokens rotativos. [Proteção de contas e sessões](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions).

## Gerar e testar

```powershell
cd C:\Projetos\GreenScape
.\scripts\gerar_exe_seguro.ps1
```

O script verifica os arquivos públicos, gera uma saída nova, examina o pacote e executa um teste em uma instalação sem credenciais. O teste confirma que ChatGPT está bloqueado até login próprio. Mantenha a pasta `_internal` ao extrair o ZIP. Não publique uma saída que falhe na verificação.

Os módulos do fluxo híbrido anterior continuam no código para diagnóstico e testes históricos, mas estão fora do modo ativo. A interface do personagem, suas expressões e o balão foram preservados.

## Validação desta entrega

- 517 testes de backend e distribuição aprovados; 13 testes da interface do Rafinha e quatro testes de configuração ChatGPT aprovados.
- Duas respostas reais pela conta local, com contexto da roseira preservado, em 11,31 e 9,33 segundos. As conversas temporárias de teste foram removidas.
- Executável: `release/windows/20261009-021440/AtelieVerde/AtelieVerde.exe`.
- ZIP: `release/windows/20261009-021440/AtelieVerde-Windows.zip`, comparado com os 972 arquivos da pasta.
- Scanner sem achados: 970 arquivos e 1.927 entradas compiladas examinadas, com comparação de três segredos locais sem exibi-los.
- Teste de instalação pública: 13 verificações, incluindo ChatGPT bloqueado até login próprio, com zero chamadas externas.
- SHA256 ZIP: `6a3b174c710f8dfab3c8e88cbf5ef9867ae1cea98151e4a857352fdf25a9f571`.

No teste real, a ferramenta de pesquisa retornou `server_error`; a conversa comum pelo ChatGPT funcionou. A pesquisa permanece dependente da disponibilidade da ferramenta na conta/modelo. Nenhuma publicação no GitHub foi realizada.
