# szczepanski-dbt-platform — Especificação Técnica

> Documento de referência para desenvolvimento. Leia inteiro antes de escrever qualquer código.
> Projeto irmão de `szczepanski-data-platform`: mesmos padrões de Airflow 3, `include/`
> reusável, ADRs e convenções. A diferença é o foco: aqui o núcleo é a **camada dbt**
> (transformação analítica), que a data-platform não tem.

---

## Visão Geral

Plataforma de dados macroeconômicos públicos do Banco Central do Brasil (BACEN). Ingestão
incremental via API SGS, **transformação com dbt Core (staging → intermediate → marts)**,
orquestração com **Airflow 3** e dashboard via Metabase. Tudo local, custo zero.

Projeto de portfólio cujo objetivo declarado é **demonstrar domínio de dbt em produção** —
modelos em camadas, materializações, testes, incremental, docs e integração dbt + Airflow.

> Régua de toda decisão (igual à data-platform): "isto sinaliza senioridade?" — julgamento,
> profundidade e comunicação de trade-offs, não contagem de ferramentas.

---

## Objetivos do Projeto

- dbt Core com três camadas (staging, intermediate, marts) e convenção de nomes consistente
- Modelos incrementais com lógica de watermark
- Integração dbt + Airflow 3 via **Astronomer Cosmos** (cada modelo dbt = task nativa na UI)
- Quality gate em duas frentes: **contrato pandera** no lote ingerido + **testes dbt** nas marts
- CI funcional com dbt state (`state:modified+`) no GitHub Actions
- Documentação dbt publicada via GitHub Pages
- Dashboards analíticos com Metabase

---

## Decisões de arquitetura (fechadas)

Registrar como ADRs em `docs/adr/`. As três primeiras nasceram da revisão da spec original
contra os padrões da `szczepanski-data-platform`:

1. **Airflow 3.x, não 2.9.** Task SDK (`from airflow.sdk import dag, task, Asset`),
   `api-server` (não `webserver`), providers `apache-airflow-providers-standard`. Mesma base
   da data-platform — o projeto lê como obra do mesmo engenheiro.
2. **Orquestração in-process + Asset-triggered, não DockerOperator.** Ingestão roda como
   `@task` (imports pesados lazy dentro da task). A ingestão publica um `Asset`; a DAG de
   transformação dbt é disparada por esse Asset (data-aware), não por fan-in manual nem cron.
3. **dbt via Cosmos (ExecutionMode.LOCAL), não DockerOperator.** Cosmos mapeia cada modelo
   dbt para uma task Airflow — visibilidade modelo-a-modelo na UI (o print que vende dbt no
   portfólio) sem socket Docker. Roda in-process, coerente com a decisão 2.
4. **Warehouse: Postgres 15 dedicado de analytics.** Banco próprio com schemas
   `raw/staging/intermediate/marts`. Isolado do Postgres de metadata do Airflow.
5. **Watermark/freshness por estado.** Antes de buscar na API, consultar o último registro
   no `raw` para determinar a `data_inicial`. Idempotência via `ON CONFLICT DO NOTHING`.
6. **Client SGS é padrão compartilhado.** O `BacenSGSClient` aqui é o mesmo padrão de client
   SGS que a `szczepanski-data-platform` usa em `src/qdp/bcb/`. Registrar a relação em ADR
   (candidato a virar pacote comum se um terceiro projeto usar). Gotcha herdado: **séries
   anuais convertidas para mensal** — nunca usar taxa anual direto onde se espera mensal.

> Construção em dois passos (vira registro de evolução no portfólio): a DAG de transformação
> começa com um `@task.bash` rodando `dbt build` end-to-end (destrava rápido), e só então é
> promovida para Cosmos. ADR documenta o porquê da promoção.

---

## Stack Tecnológica

| Componente | Tecnologia | Versão |
|---|---|---|
| Linguagem | Python | 3.12 |
| Orquestração | Apache Airflow | 3.x · LocalExecutor |
| dbt no Airflow | astronomer-cosmos | latest |
| Warehouse (analytics) | PostgreSQL | 15 |
| Transformação | dbt Core | 1.8 |
| Adapter dbt | dbt-postgres | 1.8 |
| Qualidade dbt | dbt-expectations | 0.10 |
| Contrato de dados | pandera | latest |
| Extração | httpx | >=0.28 |
| Containerização | Docker + Docker Compose | — |
| CI | GitHub Actions (só CI, nunca orquestrador) | — |
| Dashboard | Metabase | latest |
| Gerenciador de deps | uv | latest |

---

## Séries BACEN (API SGS)

Base URL: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`

Parâmetros: `?formato=json&dataInicial=DD/MM/YYYY&dataFinal=DD/MM/YYYY`

| Grupo | Indicador | Código SGS | Frequência |
|---|---|---|---|
| Inflação | IPCA | 433 | Mensal |
| Inflação | IPCA-15 | 7478 | Mensal |
| Inflação | IGP-M | 189 | Mensal |
| Juros | SELIC diária | 11 | Diária |
| Juros | Meta SELIC | 432 | Por reunião COPOM |
| Câmbio | USD/BRL | 1 | Diária |
| Câmbio | EUR/BRL | 21619 | Diária |
| Crédito | Inadimplência PF | 21082 | Mensal |
| Crédito | Spread médio geral | 20783 | Mensal |
| Expectativas | Focus IPCA | 13522 | Semanal |
| Expectativas | Focus SELIC | 13521 | Semanal |

---

## Estrutura do Repositório

Espelha as convenções da `szczepanski-data-platform`: `dags/<projeto>/`, `src/<projeto>/`,
`include/` reusável. O `dbt/` no topo é a camada nova que justifica este repo.

```
szczepanski-dbt-platform/
├── dags/
│   └── bacen/
│       ├── bacen_ingestion_dag.py     # @task de ingestão (paralelo) → publica Asset
│       └── bacen_transform_dag.py     # Cosmos: dbt build, Asset-triggered
├── src/
│   └── bacen/
│       ├── __init__.py
│       ├── sgs/
│       │   ├── __init__.py
│       │   ├── client.py              # BacenSGSClient: httpx + retry/backoff
│       │   ├── series.py              # catálogo de séries (código, grupo, freq)
│       │   └── freshness.py           # watermark: última data por grupo no raw
│       ├── loaders/
│       │   └── postgres_loader.py     # upsert ON CONFLICT DO NOTHING
│       └── ingestion.py               # orquestra client → loader por grupo
├── include/                            # REUSÁVEL (mesmo padrão da data-platform)
│   ├── __init__.py
│   ├── observability.py               # logging JSON estruturado
│   ├── alerting.py                    # email_on_failure (on_failure_callback)
│   ├── contracts.py                   # schemas pandera do lote raw
│   └── warehouse.py                   # engine psycopg do Postgres analytics (lazy)
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   │   ├── _staging__sources.yml
│   │   │   ├── _staging__models.yml
│   │   │   ├── stg_bacen__inflacao.sql
│   │   │   ├── stg_bacen__juros.sql
│   │   │   ├── stg_bacen__cambio.sql
│   │   │   ├── stg_bacen__credito.sql
│   │   │   └── stg_bacen__focus.sql
│   │   ├── intermediate/
│   │   │   ├── _intermediate__models.yml
│   │   │   ├── int_indicadores__alinhados.sql
│   │   │   └── int_focus__vs_realizado.sql
│   │   └── marts/
│   │       ├── _marts__models.yml
│   │       ├── mart_macro__painel.sql
│   │       ├── mart_macro__correlacoes.sql
│   │       └── mart_focus__acuracia.sql
│   ├── macros/
│   │   ├── generate_schema_name.sql
│   │   ├── variacao_percentual.sql
│   │   └── anualizar_taxa_diaria.sql
│   ├── tests/
│   │   └── assert_selic_positiva.sql
│   ├── seeds/
│   │   └── dim_indicadores.csv
│   ├── analyses/
│   ├── snapshots/
│   ├── dbt_project.yml
│   ├── packages.yml                   # dbt-expectations
│   └── profiles.yml.example
├── migrations/
│   └── 001_raw_schema.sql             # schema raw + tabelas por grupo
├── docker/
│   ├── airflow/
│   │   └── Dockerfile                 # apache/airflow + dbt-postgres + cosmos
│   └── ingestion/                     # (opcional) só se precisar isolar runtime
├── docs/
│   └── adr/                           # ADRs numerados (parte do valor de portfólio)
├── .github/
│   └── workflows/
│       ├── ci.yml                     # lint + mypy + dag-integrity + dbt build state
│       └── dbt_docs.yml              # deploy dbt docs no GitHub Pages
├── tests/
│   ├── test_dag_integrity.py
│   ├── test_contracts.py
│   └── extraction/
│       └── test_sgs_parse.py
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── requirements.txt                   # deps extras sobre a imagem do Airflow
├── .env.example
├── .pre-commit-config.yaml
├── CLAUDE.md
└── README.md
```

---

## Warehouse — Schemas PostgreSQL (Postgres analytics dedicado)

Um Postgres 15 dedicado a analytics, separado do Postgres de metadata do Airflow.

```
raw/          -- dados brutos da API, sem transformação (escrito pela ingestão)
staging/      -- modelos dbt staging (view)
intermediate/ -- modelos dbt intermediate (view)
marts/        -- modelos dbt marts (table; consumido pelo Metabase)
```

### Tabela raw por grupo de séries

`migrations/001_raw_schema.sql`. Cada grupo tem sua tabela no schema `raw`:

```sql
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE raw.bacen_inflacao (
    id          SERIAL PRIMARY KEY,
    codigo_sgs  INTEGER NOT NULL,
    indicador   VARCHAR(50) NOT NULL,   -- 'ipca', 'ipca15', 'igpm'
    data        DATE NOT NULL,
    valor       NUMERIC(12, 4),
    ingested_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo_sgs, data)
);

-- Mesma estrutura para: raw.bacen_juros, raw.bacen_cambio,
-- raw.bacen_credito, raw.bacen_focus
```

A constraint `UNIQUE (codigo_sgs, data)` é o que torna a ingestão idempotente.

---

## Camada de Ingestão (`src/bacen/`)

Imports pesados ficam **dentro** das tasks da DAG (padrão da data-platform): mantém o parse
da DAG leve e o teste de integridade independente das deps de runtime.

### `src/bacen/sgs/client.py`

- `BacenSGSClient` encapsula chamadas à API SGS com httpx
- Retry com backoff exponencial (máx. 3 tentativas)
- Lança `BacenAPIError` em falha persistente
- Dependências injetadas via construtor (SOLID)

```python
class BacenSGSClient:
    def fetch_serie(
        self, codigo: int, data_inicial: date, data_final: date
    ) -> list[SerieRecord]: ...
```

### `src/bacen/sgs/series.py`

- Catálogo de séries (código SGS → grupo, indicador, frequência). Fonte única da verdade
  do mapeamento usado pela ingestão e espelhado no seed `dim_indicadores.csv`.

### `src/bacen/sgs/freshness.py`

- `last_ingested_date(grupo) -> date | None`: `select max(data) from raw.bacen_<grupo>`
- Determina a `data_inicial` da próxima busca (watermark). Sem registro → janela inicial
  (ex.: 10 anos atrás).

### `src/bacen/loaders/postgres_loader.py`

- Recebe lista de registros + tabela destino
- Upsert via `INSERT ... ON CONFLICT (codigo_sgs, data) DO NOTHING`
- Loga quantidade inserida (logging estruturado, nunca `print`)
- Conexão via context manager (usa `include/warehouse.py`)

### `src/bacen/ingestion.py`

- `run_ingestion(grupo: str) -> int`: orquestra freshness → client → loader; retorna total
- Loga início, fim e total processado

---

## Camada dbt (`dbt/`)

### Convenções (mesmas da spec original, mantidas)

- Materialização staging: `view`; intermediate: `view`; marts: `table` (incremental onde aplicável)
- Nome de modelo: `<camada>_<fonte>__<entidade>.sql`
- Todo modelo descrito no `.yml` correspondente
- Testes obrigatórios em colunas-chave: `not_null`, `unique` onde aplicável

### Staging

- `stg_bacen__inflacao.sql` — de `raw.bacen_inflacao`; snake_case, tipos (DATE/NUMERIC),
  coluna `indicador`, filtra `valor IS NULL`.
- `stg_bacen__juros.sql` — de `raw.bacen_juros`; separa SELIC diária de meta SELIC; converte
  taxa diária para anualizada via macro `anualizar_taxa_diaria`.
- `stg_bacen__cambio.sql` — de `raw.bacen_cambio`; USD e EUR em formato longo (uma linha por
  moeda por data).
- `stg_bacen__credito.sql` — de `raw.bacen_credito`; inadimplência e spread em formato longo.
- `stg_bacen__focus.sql` — de `raw.bacen_focus`; expectativas IPCA e SELIC em formato longo.

### Intermediate

- `int_indicadores__alinhados.sql` — une os staging; alinha granularidade para mensal (média
  para séries diárias, último valor para séries por reunião); uma linha por mês com todos os
  indicadores como colunas; janela: últimos 10 anos.
- `int_focus__vs_realizado.sql` — join entre `stg_bacen__focus` e valores realizados; desvio
  absoluto e percentual entre expectativa e realizado; granularidade mensal.

### Marts

- `mart_macro__painel.sql` — de `int_indicadores__alinhados`; variações MoM e YoY por
  indicador (macro `variacao_percentual`); **`table` incremental por `data_referencia`**.
  Tabela principal do Metabase.
- `mart_macro__correlacoes.sql` — de `int_indicadores__alinhados`; janelas móveis de 3, 6 e
  12 meses; médias móveis de SELIC, IPCA e câmbio.
- `mart_focus__acuracia.sql` — de `int_focus__vs_realizado`; desvio médio por indicador por
  ano; análise de acurácia histórica das projeções Focus.

### Macro `variacao_percentual`

```sql
-- macros/variacao_percentual.sql
{% macro variacao_percentual(coluna, particao, ordem) %}
  round(
    ({{ coluna }} - lag({{ coluna }}) over (partition by {{ particao }} order by {{ ordem }}))
    / nullif(lag({{ coluna }}) over (partition by {{ particao }} order by {{ ordem }}), 0) * 100,
    2
  )
{% endmacro %}
```

### Macro `anualizar_taxa_diaria`

Converte taxa diária (% a.d.) para anualizada: `(1 + r/100)^252 - 1` (252 dias úteis).
Espelha o gotcha "anual → mensal" da data-platform na direção inversa — nunca misturar
frequências sem conversão explícita.

### Seed `dim_indicadores.csv`

```
codigo_sgs,indicador,nome_completo,unidade,frequencia,fonte
433,ipca,IPCA,% a.m.,Mensal,IBGE/BACEN
7478,ipca15,IPCA-15,% a.m.,Mensal,IBGE/BACEN
189,igpm,IGP-M,% a.m.,Mensal,FGV/BACEN
11,selic_diaria,SELIC Diária,% a.d.,Diária,BACEN
432,meta_selic,Meta SELIC,% a.a.,Por reunião,BACEN
1,usd_brl,Dólar americano (USD/BRL),R$,Diária,BACEN
21619,eur_brl,Euro (EUR/BRL),R$,Diária,BACEN
21082,inadimplencia_pf,Inadimplência PF,% carteira,Mensal,BACEN
20783,spread_medio,Spread Médio Geral,p.p.,Mensal,BACEN
13522,focus_ipca,Expectativa IPCA (Focus),% a.a.,Semanal,BACEN
13521,focus_selic,Expectativa SELIC (Focus),% a.a.,Semanal,BACEN
```

---

## Contrato de dados (`include/contracts.py`)

Mesmo padrão pandera da data-platform, aplicado ao **lote `raw`** antes de liberar a
transformação. Soma-se aos testes dbt (que cobrem as marts), não os substitui.

```python
class SerieRawContract(pa.DataFrameModel):
    codigo_sgs: Series[int]   = pa.Field(nullable=False)
    indicador:  Series[str]   = pa.Field(nullable=False)
    data:       Series[str]   = pa.Field(nullable=False)   # ISO date
    valor:      Series[float] = pa.Field(nullable=True)
    class Config:
        strict = False
        coerce = True
```

A task de ingestão valida o lote com `lazy=True` (acumula todas as violações num só erro) e
falha — disparando o alerta — antes de qualquer transformação rodar.

---

## DAGs Airflow 3

### `dags/bacen/bacen_ingestion_dag.py`

- `dag_id="bacen_ingestion"`, Task SDK (`from airflow.sdk import dag, task, Asset`)
- `schedule`: janelas em que a máquina costuma estar de pé (ex.: `"0 7 * * *"` BRT);
  `catchup=False`, `max_active_runs=1`
- `default_args`: `retries=3`, `retry_delay=timedelta(minutes=10)`,
  `retry_exponential_backoff=True`, `on_failure_callback=email_on_failure`
- Tags: `["bacen", "ingestion"]`
- Cinco `@task` de ingestão (inflacao, juros, cambio, credito, focus) **em paralelo**, cada
  uma com import lazy de `src.bacen.ingestion`. Watermark por grupo via freshness.
- Uma `@task` de quality gate valida o lote contra `SerieRawContract`.
- A task final publica o `Asset` `warehouse://raw.bacen` (`outlets=[...]`), habilitando o
  disparo data-aware da transformação.

```
ingest_inflacao ─┐
ingest_juros    ─┤
ingest_cambio   ─┼─► quality_gate ─► publish (outlet: Asset raw.bacen)
ingest_credito  ─┤
ingest_focus    ─┘
```

### `dags/bacen/bacen_transform_dag.py`

- `schedule=[Asset("warehouse://raw.bacen")]` — roda após cada ingestão bem-sucedida
  (data-aware), não por cron.
- Cosmos `DbtTaskGroup` / `DbtDag` com `ExecutionMode.LOCAL`, apontando para `dbt/` e o
  `profiles.yml` do Postgres analytics. Renderiza `dbt seed` + `stg_* → int_* → mart_*` +
  `dbt test` como tasks nativas.
- `on_failure_callback=email_on_failure`.
- **Passo 1 (destravar):** antes do Cosmos, uma versão com `@task.bash` rodando
  `dbt build --project-dir dbt --profiles-dir dbt`. ADR registra a promoção para Cosmos.

---

## Docker Compose

Serviços (tudo local, custo zero):

```yaml
services:
  postgres-airflow:     # metadata do Airflow 3
  postgres-warehouse:   # Postgres 15 analytics (schemas raw/staging/intermediate/marts)
  airflow-init:         # db migrate + cria admin
  airflow-apiserver:    # UI 127.0.0.1:8080 (admin/admin)
  airflow-scheduler:
  airflow-dag-processor:
  airflow-triggerer:
  metabase:             # dashboard, aponta para postgres-warehouse
```

A imagem do Airflow (`docker/airflow/Dockerfile`) estende `apache/airflow` e instala, com o
constraints file da versão: `astronomer-cosmos`, `httpx`, `pandera`, `psycopg2-binary`.
O **dbt fica num venv isolado** (`/opt/airflow/dbt-venv`), instalado de `dbt-requirements.txt`
sem o constraints do Airflow, para evitar conflito de dependências (ver ADR 0001). O Cosmos
(no ambiente do Airflow) invoca o binário do dbt do venv via `dbt_executable_path`.

Volumes: `airflow-db`, `warehouse-db`, `metabase-data`, e `./dags`, `./include`, `./src`,
`./dbt`, `./logs` montados. Rede bridge compartilhada.

---

## CI — GitHub Actions (só CI, nunca orquestrador)

### `ci.yml` — em todo PR

1. Checkout, setup Python 3.12, deps via `uv`
2. `ruff check` + `mypy include src`
3. `pytest` — integridade das DAGs + contratos + parse
4. Sobe Postgres via `services`, aplica `migrations/001_raw_schema.sql`
5. `dbt deps`, `dbt seed`, `dbt build --select state:modified+` com `--defer` contra o
   manifest de produção (artefato versionado)
6. Comenta o resultado no PR

### `dbt_docs.yml` — em merge na `main`

1. Checkout, setup Python e dbt
2. `dbt docs generate`
3. Deploy de `target/` no GitHub Pages via `actions/deploy-pages`

---

## Variáveis de Ambiente (`.env.example`)

```env
# Postgres analytics (warehouse dbt)
WAREHOUSE_HOST=postgres-warehouse
WAREHOUSE_PORT=5432
WAREHOUSE_DB=bacen_analytics
WAREHOUSE_USER=bacen
WAREHOUSE_PASSWORD=changeme

# Airflow 3
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__AUTH_MANAGER=airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager
AIRFLOW__API_AUTH__JWT_SECRET=troque-em-producao
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres-airflow/airflow
AIRFLOW_FERNET_KEY=          # make fernet

# Alerta de falha (on_failure_callback)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
ALERT_EMAIL_TO=
ALERT_EMAIL_FROM=

# Metabase
MB_DB_TYPE=postgres
MB_DB_DBNAME=metabase
MB_DB_HOST=postgres-warehouse
MB_DB_PORT=5432
MB_DB_USER=metabase
MB_DB_PASS=changeme
```

---

## Metabase — Dashboards a Construir

1. **Painel Macroeconômico** — IPCA, SELIC e câmbio nos últimos 24 meses; cards com valor
   atual e variação MoM; tabela de inflação acumulada no ano.
2. **Análise de Crédito** — inadimplência PF vs spread bancário; correlação SELIC × spread.
3. **Acurácia do Focus** — desvio médio das projeções por indicador por ano; expectativa vs
   realizado dos últimos 12 meses.

---

## Princípios de Desenvolvimento (alinhados à data-platform)

- **Sem emojis** em nenhuma saída (prosa, tabelas, commits, comentários).
- SOLID na ingestão: responsabilidade única, dependências injetadas via construtor.
- Type hints em todo Python. Logging estruturado JSON (`include/observability.py`), nunca `print`.
- Sem credenciais no código — sempre via env.
- Sem lógica de negócio nos marts além de agregação/variação; nada de regra de consumidor.
- Comentários explicam o "por quê", não o "o quê". Sem abstração não pedida (`include/` só
  cresce quando 2+ usos reais).
- **ADR para toda decisão de arquitetura.** Commits semânticos: `feat:`, `fix:`, `refactor:`,
  `docs:`, `test:`. Mensagem em português.

---

## README.md — Estrutura Esperada

1. Badges: CI, link dbt docs, Python, license
2. Descrição em dois parágrafos (foco: camada dbt como diferencial)
3. Diagrama de arquitetura (Mermaid): API SGS → ingestão (Airflow) → raw → dbt → marts → Metabase
4. Tabela de indicadores cobertos
5. Setup local (`make up`)
6. Link para dbt docs publicado
7. Screenshots: grafo dbt no Airflow (Cosmos) + dashboards Metabase
8. Decisões de design (resumo dos ADRs)

---

## CLAUDE.md — Contexto (criar na raiz)

- Stack e versões; estrutura de diretórios
- Gotchas: Airflow 3 (Task SDK/Asset/api-server), imports lazy nas tasks, conversão de
  frequências de séries, Cosmos ExecutionMode.LOCAL
- Convenções dbt e de commits
- Comandos frequentes (`make up`, `make test`, `make lint`, `dbt build`, `dbt docs serve`)
- O que NÃO fazer: lógica de negócio nos marts, credenciais em código, DockerOperator,
  Airflow 2.x, emojis

---

## Ordem de Implementação Sugerida

**Fase 0 — Scaffold (fumaça sobe):**
1. `docker-compose.yml` (Airflow 3 + 2 Postgres + Metabase), `docker/airflow/Dockerfile`, `Makefile`
2. `migrations/001_raw_schema.sql`; `include/` (observability, alerting, contracts, warehouse)
3. `pyproject.toml`, `requirements.txt`, `.pre-commit-config.yaml`, `.env.example`, CLAUDE.md
4. `test_dag_integrity.py` passando; `make up` como teste de fumaça real

**Fase 1 — Ingestão end-to-end:**
5. `src/bacen/sgs/{client,series,freshness}.py` + `loaders/postgres_loader.py` + `ingestion.py`
6. `dags/bacen/bacen_ingestion_dag.py` (paralelo → quality_gate → Asset)
7. Testes: `test_sgs_parse.py`, `test_contracts.py`. Smoke real: rodar a DAG, conferir `raw`

**Fase 2 — dbt:**
8. `dbt_project.yml`, `profiles.yml.example`, `packages.yml`, seed `dim_indicadores`
9. Staging → intermediate → marts; macros; testes dbt + dbt-expectations
10. `bacen_transform_dag.py` passo 1 (`@task.bash dbt build`), Asset-triggered

**Fase 3 — Cosmos + CI + docs:**
11. Promover a DAG de transformação para Cosmos (ADR da promoção)
12. CI (`ci.yml` com dbt state) + dbt docs no GitHub Pages

**Fase 4 — Portfólio:**
13. Dashboards Metabase; README final com screenshots; ADRs revisados; seção "o que faria diferente"
