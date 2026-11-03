# Ampliação da empresa demonstrativa — 05/10/2026

Foram adicionados **15 produtos**: três em cada categoria de Vasos, Substratos, Fertilizantes, Ferramentas e Acessórios. O catálogo passou de 46 para 61 itens. Todos possuem SKU, código de barras de teste, marca e variação demonstrativas, localização, fornecedor, custo, margem e preço calculado pelo mecanismo existente. A carga efetiva de 6% é uma hipótese fictícia do cadastro, não uma orientação tributária.

A expansão registra **15 compras com entrada de estoque e conta a pagar** e **cinco vendas com 15 saídas de itens, pedidos e contas a receber pagas**. Cada pedido contém três itens, somando seis unidades; são 30 unidades vendidas adicionais. Assim, estoque, compras, fornecedores, vendas, recebimentos e gráficos usam os mesmos registros.

Os novos itens usam imagens ilustrativas de suas categorias e trazem essa indicação na descrição; não são fotografias específicas dos produtos. Especificações comerciais, preços e contatos são dados fictícios de demonstração.

O módulo `backend/app/expanded_demo.py` reutiliza as regras comerciais de criação de produtos, cálculo de preço, movimentação e checkout. As adições são gravadas em uma transação e protegidas por `CatalogVersion`: reiniciar não duplica produtos, compras ou vendas. O upgrade não recria cadastros anteriores nem altera as quantidades dos produtos antigos.

As contas de demonstração permanecem com os mesmos e-mails e senhas. Os nomes exibidos agora são **Leandro** no administrador e **Rafael** no cliente. Os vínculos continuam usando os mesmos IDs. Registros demonstrativos relacionados com nomes antigos foram atualizados; contas pessoais e clientes cadastrados fora desses perfis não foram renomeados.

O backup anterior à ampliação está indicado em `.local/latest-catalog-expansion-backup.txt`. Os testes verificam idempotência, fornecedores, saldos, contas a pagar vinculadas às entradas, recebimentos vinculados aos pedidos e preservação de contas externas à demonstração. A verificação de consistência do banco em execução retornou zero erros e zero avisos.
