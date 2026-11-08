# Ateliê Verde — arquitetura baseada no código-fonte

## Componentes

~~~mermaid
flowchart LR
    V[Cliente de demonstração] --> UI[React + TypeScript]
    A[Administrador] --> UI
    UI --> C[api.ts + token de sessão]
    C --> F[FastAPI /api]
    F --> AUTH[JWT + autorização por perfil/owner]
    F --> CHECK[checkout.py / transações]
    F --> QUOTE[main.py / orçamento e projeto]
    F --> OPS[operations.py / financeiro]
    CHECK --> DB[(SQLAlchemy: SQLite local ou PostgreSQL)]
    QUOTE --> DB
    OPS --> DB
    F --> BOT[Rafinha: catálogo local]
    BOT -.-> EXT[Adaptadores externos opcionais, exigem configuração]
    DB --> MIG[Alembic / migrações explícitas]
~~~

**Atenção:** o diagrama representa responsabilidades lógicas; não há serviço público, gateway de pagamento nem provedores externos ativos obrigatórios. As migrations existem, mas o startup também chama create_all, o que exige revisão para produção.

## Fluxo 1 — Pedido e cancelamento

~~~mermaid
sequenceDiagram
    autonumber
    actor C as Cliente autenticado
    participant API as FastAPI /api/orders
    participant X as checkout
    participant DB as Banco transacional
    C->>API: POST /api/orders (items, request_key)
    API->>X: Valida papel customer e quantidades
    X->>DB: Busca replay / bloqueia produto
    alt Mesma chave e mesmo payload
      DB-->>C: Pedido existente, sem nova baixa
    else Estoque insuficiente
      DB-->>C: 409, sem pedido parcial
    else Estoque disponível
      X->>DB: Order + Ledger pendente + StockMove
      DB-->>C: Pedido Confirmado / total do servidor
    end
    C->>API: POST /api/orders/{id}/cancel
    API->>DB: Confere proprietário, status, pagamento
    alt Conta já paga
      DB-->>C: 409, exige reembolso
    else Conta pendente
      API->>DB: Cancela Order/Ledger e repõe estoque
      DB-->>C: Cancelado
    end
~~~

## Fluxo 2 — Orçamento e projeto

~~~mermaid
sequenceDiagram
    autonumber
    actor C as Cliente titular
    actor A as Administrador
    participant API as FastAPI /api/quotes
    participant DB as PostgreSQL/SQLite
    C->>API: POST /api/quotes
    API->>DB: Salva Quote solicitado
    A->>API: PATCH /api/quotes/{id}/price
    API->>DB: Marca Enviado + preço
    C->>API: POST /api/quotes/{id}/approve
    API->>DB: Compara status e proprietário
    API->>DB: Cria Project + ProjectEvent
    DB-->>C: Projeto Aprovado
~~~

## Código e responsabilidades

| Área | Arquivos |
| --- | --- |
| Rotas, autenticação, pedido e orçamento | [main.py](../../backend/app/main.py) |
| Regra de compra, estoque e conta | [checkout.py](../../backend/app/checkout.py) |
| Locks para transações comerciais | [transactions.py](../../backend/app/transactions.py) |
| Auditoria, precificação e movimentação | [business.py](../../backend/app/business.py) |
| Financeiro, agenda, documentos, relatórios | [operations.py](../../backend/app/operations.py) |
| Entidades SQLAlchemy | [models.py](../../backend/app/models.py) |
| JWT, hash de senha e roles | [security.py](../../backend/app/security.py) |
| Migrações de banco | [migrations/versions](../../backend/migrations/versions) |
| Interface | [frontend/src](../../frontend/src) |
| Testes de integração deste caso | [test_recruiting_case.py](../../backend/tests/test_recruiting_case.py) |

## Limites de arquitetura

O backend não garante sozinho proteção de uma instalação pública: deve-se revisar cookies/tokens, HTTPS, CSP, RBAC, rotas administrativas, migrações, observabilidade, backups, dados pessoais, serviços externos e autenticação de provedores. Os testes de CI validam casos específicos, não certificam segurança de produção.

[Auditoria](AUDITORIA.md) · [Estudo de caso](ESTUDO_DE_CASO.md).
