# szczepanski-dbt-platform — CLAUDE.md

Pipeline de dados macroeconomicos do BACEN (API SGS) cujo nucleo e a **camada dbt**
(staging -> intermediate -> marts). Projeto irmao de `../szczepanski-data-platform`:
mesmos padroes de Airflow 3, `include/` reusavel, ADRs e convencoes. A diferenca de
foco e a transformacao analitica com dbt, que a data-platform nao tem.

Este repo e **peca de portfolio**: a regua de toda decisao e "isto sinaliza senioridade?".
Ver `bacen-macro-pipeline-spec.md` (especificacao completa) e `docs/adr/`.

## Stack

| Camada | Tecnologia |
|---|---|
| Orquestracao | Apache Airflow 3.x · LocalExecutor · docker-compose |
| dbt no Airflow | Astronomer Cosmos (ExecutionMode.LOCAL) |
| Transformacao | dbt Core 1.8 · dbt-postgres · dbt-expectations |
| Warehouse | PostgreSQL 15 dedicado (schemas raw/staging/intermediate/marts) |
| Extracao | Python 3.12 · httpx |
| Contrato de dados | pandera (`include/contracts.py`) |
| Observabilidade | logging JSON (`include/observability.py`) · alerta de falha por email (`include/alerting.py`) |
| Qualidade | ruff · mypy · pytest · pre-commit · CI (GitHub Actions, so CI) |

## Rodar localmente

```bash
cp .env.example .env      # preencher WAREHOUSE_*, SMTP_* (opcional)
make fernet               # gerar AIRFLOW_FERNET_KEY -> colar no .env
make up                   # UI em http://localhost:8080 (admin/admin); Metabase em :3000
make test                 # integridade das DAGs
make lint                 # ruff + mypy
```

## Estrutura

```
dags/bacen/      DAGs: bacen_ingestion (SGS + Olinda -> raw) e bacen_transform (dbt, Asset-triggered)
src/bacen/       Ingestao: sgs/ (dados/serie) + olinda/ (Focus) + loaders/ + ingestion
include/         REUSAVEL: observability · alerting · contracts (pandera) · warehouse (psycopg)
dbt/             Projeto dbt: models/{staging,intermediate,marts} · macros · seeds · tests
migrations/      Schema raw (aplicado no boot do postgres-warehouse)
docs/adr/        Architecture Decision Records numerados
```

Convencao multi-projeto herdada da data-platform: novo projeto = `dags/<proj>/` +
`src/<proj>/`, reusando `include/`.

## Gotchas criticos — ler antes de mexer

- **Airflow 3, nao 2.x.** Dataset -> **Asset**. Operators padrao vem de
  `apache-airflow-providers-standard`. UI servida por `api-server` (nao `webserver`).
  Task SDK: `from airflow.sdk import dag, task, Asset`.
- **Imports pesados ficam DENTRO das tasks** (lazy), nunca no topo da DAG. Mantem o parse
  leve e o teste de integridade independente das deps de runtime.
- **Dois Postgres separados**: `postgres-airflow` (metadata) e `postgres-warehouse`
  (analytics — destino da ingestao, do dbt e do Metabase). Nao confundir.
- **Conversao de frequencia de series e obrigatoria.** Nunca misturar taxa diaria,
  mensal e anual sem conversao explicita (macro `anualizar_taxa_diaria`). Mesmo gotcha
  da data-platform (serie 20714 anual -> mensal).
- **Ingestao idempotente**: `ON CONFLICT ... DO NOTHING`. Watermark por grupo
  (`src/bacen/sgs/freshness.py`) determina a `data_inicial` — incremental, nao full.
- **Focus vem da API Olinda, NAO do SGS** (ADR 0002). `src/bacen/olinda/` consome
  `ExpectativasMercadoInflacao12Meses` com `Suavizada eq 'N'` e `baseCalculo eq 0` (sem
  esse filtro, 2 linhas por data). As series SGS 13521/13522 NAO sao expectativas (a
  13522 e o IPCA acumulado 12m realizado). Acuracia alinha horizonte forward-12m.
- **dbt vive num venv ISOLADO** (`/opt/airflow/dbt-venv`), separado do ambiente do
  Airflow, para evitar conflito de constraints (ADR 0001). Invocar sempre
  `/opt/airflow/dbt-venv/bin/dbt`. `dbt-expectations` vai em `dbt/packages.yml` (dbt deps),
  nao no pip.
- **dbt via Cosmos roda in-process** (ExecutionMode.LOCAL, apontando `dbt_executable_path`
  para o venv) — sem socket Docker, sem DockerOperator. Hoje a transform_dag ainda usa
  BashOperator (passo 1); a promocao para Cosmos e Fase 3 (com ADR).
- **Maquina nao fica 24/7.** Toda DAG: `catchup=False`. Ingestao agendada em janela diurna;
  transformacao e Asset-triggered (roda apos a ingestao, nao por horario exato).

## Fronteiras de qualidade (duas, complementares)

1. **Contrato pandera** (`include/contracts.py`) valida o lote `raw` ANTES da transformacao.
2. **Testes dbt** (`not_null`, `unique`, dbt-expectations) cobrem staging -> marts.

Uma nao substitui a outra: pandera garante a forma do dado bruto que entra; dbt garante as
regras das transformacoes.

## Convencoes dbt

- Materializacao: staging `view`, intermediate `view`, marts `table` (incremental onde aplicavel).
- Nome de modelo: `<camada>_<fonte>__<entidade>.sql` (ex.: `stg_bacen__inflacao`).
- Todo modelo descrito no `.yml`. Testes obrigatorios em colunas-chave.
- Sem logica de negocio nos marts alem de agregacao/variacao.

## Regras de trabalho

- **Sem emojis** em nenhuma saida (prosa, tabelas, commits, comentarios).
- Comentarios explicam o "por que", nao o "o que".
- Sem abstracao nao pedida. `include/` so cresce quando 2+ usos reais.
- **ADR para toda decisao de arquitetura.** Commits semanticos (`feat:`, `fix:`, `refactor:`,
  `docs:`, `test:`), em portugues.
- Sem credenciais em codigo — sempre via env.
- Ao terminar: 1-2 frases do que mudou e o proximo passo.

## Testes

- `tests/test_dag_integrity.py` (sem erro de import, DAGs esperadas presentes, tags) — sempre passando.
- Toda funcao de parse/transformacao (preco, conversao de taxa, freshness) com I/O externo mockado.
- Validar lote contra o contrato pandera.

## Estado atual

- **Fase 0 (scaffold)** — OK. Stack sobe com `make up` (Airflow 3 + 2 Postgres + Metabase),
  boot reproduzivel via `AIRFLOW_UID` (sem chmod manual). `make test` roda no container.
- **Fase 1 (ingestao)** — OK end-to-end. SGS (inflacao/juros/cambio/credito) + Focus (Olinda)
  populando o `raw`, com watermark incremental, gate pandera pre-publicacao e idempotencia.
- **Fase 1.5 (Focus via Olinda)** — OK. Ver ADR 0002. Acuracia com desvios realistas.
- **Fase 2 (dbt)** — OK. `dbt build` verde (PASS=56): 5 staging + 2 intermediate + 3 marts +
  seed + 45 testes. Schemas limpos (raw/staging/intermediate/marts). dbt-core 1.9 / postgres 1.9.
- **Proximas**: Fase 3 (promover transform_dag para Cosmos + CI + dbt docs no GitHub Pages),
  Fase 4 (dashboards Metabase + README). Ver `bacen-macro-pipeline-spec.md`.
