# szczepanski-dbt-platform

Pipeline de dados macroeconomicos do Banco Central do Brasil com foco em **engenharia
analitica com dbt Core**: ingestao incremental de series publicas, transformacao em tres
camadas (staging -> intermediate -> marts) e orquestracao em Apache Airflow 3, tudo local
e sem custo. Projeto irmao da [szczepanski-data-platform](../szczepanski-data-platform);
a diferenca de foco e a camada dbt, que a plataforma de dados nao tem.

![CI](https://github.com/marcioszczepanski93/szczepanski-dbt-platform/actions/workflows/ci.yml/badge.svg)
![dbt docs](https://github.com/marcioszczepanski93/szczepanski-dbt-platform/actions/workflows/dbt_docs.yml/badge.svg)

## Arquitetura

```
  Fontes                    Plataforma (este repo)                     Consumo
  ┌──────────┐   ┌──────────────────────────────────────────────┐   ┌──────────┐
  │ BCB SGS  │   │  Airflow 3 (LocalExecutor)                    │   │ Metabase │
  │ (series) │──▶│  bacen_ingestion  →  Asset  →  bacen_transform│──▶│(dashboards│
  │ BCB Olinda│  │  (SGS + Olinda)              (dbt via Cosmos) │   │  nos marts│
  │ (Focus)  │   │        │                          │           │   └──────────┘
  └──────────┘   │        ▼                          ▼           │
                 │  raw.*  ─(dbt)─▶ staging ─▶ intermediate ─▶ marts
                 │  include/ reusavel: observability · alerting ·│
                 │  contracts (pandera) · warehouse (psycopg)    │
                 └──────────────────────────────────────────────┘
                              Postgres warehouse (analytics)
```

- **Ingestao** (`src/bacen/`): duas fontes reais e distintas — API SGS (`dados/serie`) para
  inflacao, juros, cambio e credito; API Olinda (`Expectativas de Mercado`) para o Focus.
  Incremental por watermark, idempotente (`ON CONFLICT DO NOTHING`), com gate de contrato
  pandera **antes** de publicar.
- **Transformacao** (`dbt/`): staging (limpeza 1:1) -> intermediate (alinhamento de
  frequencia, regra de negocio) -> marts (consumo). Testes genericos + dbt-expectations +
  testes singulares.
- **Orquestracao**: a ingestao publica um Asset; a DAG de transformacao dbt e disparada por
  ele (data-aware). Via Astronomer Cosmos, cada model dbt vira uma task nativa na UI.

## Indicadores cobertos

| Grupo | Indicadores | Fonte |
|---|---|---|
| Inflacao | IPCA, IPCA-15, IGP-M | SGS |
| Juros | SELIC diaria, Meta SELIC | SGS |
| Cambio | USD/BRL, EUR/BRL | SGS |
| Credito | Inadimplencia PF, Spread medio | SGS |
| Expectativas | Focus IPCA 12 meses | Olinda |

## Marts

- `mart_macro__painel` — painel mensal com IPCA/SELIC/cambio, variacoes MoM/YoY e IPCA 12m.
- `mart_macro__correlacoes` — medias moveis de 3/6/12 meses.
- `mart_focus__acuracia` — acuracia historica das projecoes Focus (expectativa vs realizado,
  com alinhamento de horizonte forward-12m).

## Como rodar

```bash
cp .env.example .env      # WAREHOUSE_*, SMTP_* (opcional)
make fernet               # gera AIRFLOW_FERNET_KEY -> colar no .env
make up                   # Airflow em :8080 (admin/admin), Metabase em :3000
make test                 # suite de testes (no container)
make lint                 # ruff + mypy
```

## Stack

Apache Airflow 3 (Task SDK, Asset) · dbt Core 1.9 + dbt-postgres · Astronomer Cosmos ·
PostgreSQL 15 (warehouse dedicado) · pandera (contrato de dados) · Metabase · Python 3.12 ·
docker-compose · GitHub Actions (CI + dbt docs no Pages).

## Decisoes de arquitetura (ADRs)

As decisoes nao triviais estao registradas em [`docs/adr/`](docs/adr/):

- [ADR 0001 — dbt em venv isolado do Airflow](docs/adr/0001-isolar-runtime-dbt-em-venv.md):
  por que o dbt roda num ambiente separado do core do Airflow (conflito de constraints).
- [ADR 0002 — Expectativas Focus via API Olinda, nao SGS](docs/adr/0002-focus-via-olinda-nao-sgs.md):
  como um desvio "bom demais" (zero) revelou que a fonte estava errada, e a correcao.
- [ADR 0003 — Transformacao dbt via Astronomer Cosmos](docs/adr/0003-transform-dag-via-cosmos.md):
  a promocao de um BashOperator unico para tasks nativas por model.

## Documentacao complementar

- Especificacao tecnica: [`bacen-macro-pipeline-spec.md`](bacen-macro-pipeline-spec.md)
- Plano didatico da camada dbt: [`.specs/features/dbt-implementation-plan.md`](.specs/features/dbt-implementation-plan.md)
- Contexto para desenvolvimento: [`.specs/features/CLAUDE.md`](.specs/features/CLAUDE.md)
