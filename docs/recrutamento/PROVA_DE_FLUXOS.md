# Como verificar os fluxos comerciais do Ateliê Verde

Esta página serve para a entrevista e para reproduzir testes seguros. **Não é uma declaração de prontidão de produção.**

## Fluxo A — compra

Dado produto de teste Lavanda com estoque 5 e preço em centavos 2490:

| Estado | Pedido | Estoque | Ledger | Movimentações |
| --- | --- | ---: | --- | --- |
| Inicial | Nenhum | 5 | Nenhum | 0 |
| POST /api/orders, quantidade 2 | Confirmado, 4980 centavos | 3 | Receita/Loja pendente | -2 |
| Repetir mesma chave+payload | Mesmo ID | 3 | Mesmo lançamento | Sem nova saída |
| Cancelamento autorizado e não pago | Cancelado | 5 | Cancelado | +2 de reposição |
| Repetir cancelamento | HTTP 409 | 5 | Cancelado | Nenhuma terceira movimentação |

**Exceção:** após conta paga, o endpoint de cancelamento retorna 409 e exige reembolso específico; não há reembolso bancário implementado neste teste.

## Fluxo B — orçamento

| Ação | Papel | Resultado esperado |
| --- | --- | --- |
| POST /api/quotes | Cliente autenticado | Novo orçamento |
| PATCH /api/quotes/{id}/price | Cliente | HTTP 403 |
| PATCH /api/quotes/{id}/price | Administrador | Enviado com preço fictício de 180000 centavos |
| POST /api/quotes/{id}/approve | Outro cliente | HTTP 404 |
| POST /api/quotes/{id}/approve | Cliente titular | Projeto e ProjectEvent criados |
| Repetir aprovação | Titular | HTTP 409, sem segundo projeto |

## Protocolo seguro

1. Conferir [conftest.py](../../backend/tests/conftest.py): cria DB efêmero e perfis sintéticos, desligando provedor externo.
2. Rodar [test_recruiting_case.py](../../backend/tests/test_recruiting_case.py).
3. Ler [logs do Actions #42531033867](https://github.com/LeandroAugFerreira/atelie-verde/actions/runs/42531033867).
4. Se necessário, observar [tour estático](https://leandroaugferreira.github.io/atelie-verde-demo.html) e identificar explicitamente que seus dados não são persistidos.
5. Durante entrevista, abrir o código [checkout.py](../../backend/app/checkout.py) e [main.py](../../backend/app/main.py) para explicar locks/rollback/autorização.

**Não usar contas reais ou clientes reais** para reproduzir; não enviar dados pessoais ao tour, que não tem formulário de cadastro.
