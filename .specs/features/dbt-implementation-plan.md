# Plano de Implementação — Camada dbt (didático)

> Documento de estudo e referência. Cobre a camada dbt do projeto de ponta a ponta:
> os conceitos, a ordem de construção, e o que cada arquivo faz e por quê.
> Para a visão geral do projeto, ver `../../bacen-macro-pipeline-spec.md` e `../../CLAUDE.md`.

---

## 1. O que é dbt e onde ele entra aqui

dbt (data build tool) é a ferramenta que transforma dados que **já estão** no banco. Ele
não extrai e não carrega — isso é o "EL" (Extract/Load), feito pela nossa camada de
ingestão. dbt é o "T" (Transform) de um fluxo **ELT**:

```
API SGS  ──(ingestão Python)──►  raw.*  ──(dbt)──►  staging ─► intermediate ─► marts ─► Metabase
   E + L (extrai e carrega cru)            T (transforma com SQL versionado e testado)
```

Ideia central do dbt: **cada modelo é um `SELECT`**. Você escreve só a query; o dbt cria a
view/table no banco, resolve a ordem de execução (quem depende de quem) e roda os testes.
Você nunca escreve `CREATE TABLE` na mão — declara a intenção, o dbt materializa.

Por que isso importa para o portfólio: dbt traz para dados as práticas de engenharia de
software — versionamento, testes, modularidade, documentação e CI. É o diferencial deste repo.

---

## 2. Conceitos-chave (glossário rápido)

| Conceito | O que é |
|---|---|
| **Model** | Um arquivo `.sql` com um `SELECT`. Vira uma view ou table no banco. |
| **Source** | Declaração de uma tabela que já existe no banco e o dbt não criou (aqui: `raw.*`). Referenciada com `{{ source(...) }}`. |
| **ref()** | `{{ ref('outro_modelo') }}` referencia outro model. É o que o dbt usa para montar o grafo de dependências (DAG). |
| **Materialization** | Como o model vira objeto no banco: `view`, `table`, `incremental`, `ephemeral`. |
| **Incremental** | Materialização que processa só linhas novas/alteradas em vez de reconstruir tudo. |
| **Seed** | Um CSV versionado no repo que o dbt carrega como tabela (`dbt seed`). Bom para dados pequenos e estáticos (ex.: catálogo de indicadores). |
| **Test** | Asserção sobre os dados. Genéricos (`not_null`, `unique`, `accepted_values`) ou singulares (um `.sql` que retorna linhas "ruins"). |
| **Macro** | Função em Jinja+SQL reutilizável entre models (DRY para SQL). |
| **Snapshot** | Captura mudanças de uma tabela ao longo do tempo (SCD type 2). Não usamos na Fase 2. |
| **Package** | Biblioteca dbt de terceiros (ex.: `dbt-expectations`), instalada com `dbt deps`. |

---

## 3. As três camadas (staging → intermediate → marts)

Esta separação é convenção consolidada da comunidade dbt. Cada camada tem um propósito e
o dado flui numa direção só. Nunca pule camadas (um mart não lê `raw` direto).

```
   raw.bacen_*            staging                 intermediate                marts
  (dado cru,        ┌──────────────┐        ┌────────────────────┐     ┌──────────────────┐
   1 fonte)         │ limpa, tipa, │        │ junta fontes,      │     │ pronto p/ consumo│
                    │ renomeia.    │   ─►   │ aplica regra de    │  ─► │ (Metabase).      │
                    │ 1:1 c/ fonte │        │ negócio entre elas │     │ agregado/largo   │
                    │ materializa  │        │ materializa: view  │     │ materializa:     │
                    │ view         │        │                    │     │ table/incremental│
                    └──────────────┘        └────────────────────┘     └──────────────────┘
```

- **Staging** (`stg_<fonte>__<entidade>`): uma "porta de entrada" por tabela bruta.
  Renomeia colunas para snake_case semântico, converte tipos, filtra lixo óbvio
  (ex.: `valor IS NULL`). Regra de ouro: **um staging por tabela source, relação 1:1**,
  sem JOIN entre fontes aqui. Materialização `view` (barato, sempre fresco).
- **Intermediate** (`int_<assunto>__<descrição>`): onde a lógica de negócio mora. Junta
  staging, alinha granularidades (ex.: diário → mensal), calcula relações entre indicadores.
  Não é consumido diretamente pelo dashboard — é um passo de montagem. Materialização `view`.
- **Marts** (`mart_<área>__<entidade>`): o produto final, modelado para análise. É o que o
  Metabase lê. Materialização `table` (rápido de consultar), `incremental` onde o volume
  justifica reprocessar só o novo.

Por que três e não uma query gigante: testabilidade (você testa cada pedaço),
reaproveitamento (vários marts podem usar o mesmo intermediate) e legibilidade.

---

## 4. O que vamos construir (mapa dos models)

```
dbt/models/
├── staging/                         materialização: view
│   ├── _staging__sources.yml        declara as tabelas raw.* como sources + testes de fonte
│   ├── _staging__models.yml         descrição + testes dos modelos staging
│   ├── stg_bacen__inflacao.sql      raw.bacen_inflacao  -> limpo (ipca, ipca15, igpm)
│   ├── stg_bacen__juros.sql         raw.bacen_juros     -> selic diária vs meta selic
│   ├── stg_bacen__cambio.sql        raw.bacen_cambio    -> usd, eur (formato longo)
│   ├── stg_bacen__credito.sql       raw.bacen_credito   -> inadimplência, spread (longo)
│   └── stg_bacen__focus.sql         raw.bacen_focus     -> expectativas ipca, selic (longo)
├── intermediate/                    materialização: view
│   ├── _intermediate__models.yml
│   ├── int_indicadores__alinhados.sql    une os staging, alinha tudo p/ granularidade mensal
│   └── int_focus__vs_realizado.sql       expectativa Focus vs valor realizado (desvio)
└── marts/                           materialização: table / incremental
    ├── _marts__models.yml
    ├── mart_macro__painel.sql       painel principal: indicadores + variações MoM/YoY
    ├── mart_macro__correlacoes.sql  médias e janelas móveis 3/6/12 meses
    └── mart_focus__acuracia.sql     acurácia histórica das projeções Focus por ano
```

Mais: `macros/` (funções SQL reutilizáveis), `seeds/dim_indicadores.csv` (catálogo),
`tests/` (testes singulares), `packages.yml` (dbt-expectations).

---

## 5. Etapas de implementação (Fase 2 do projeto)

Cada etapa é incremental e verificável. A régra: ao fim de cada etapa, `dbt build` roda
verde até o ponto construído. Não avance com etapa anterior quebrada.

### Etapa 2.0 — Configuração base do projeto dbt

Objetivo: o dbt enxerga o warehouse e roda `dbt debug` com sucesso.

Arquivos:
- `dbt/dbt_project.yml` — nome do projeto, caminhos, e materialização padrão por camada:
  ```yaml
  models:
    bacen:
      staging:      { +materialized: view,  +schema: staging }
      intermediate: { +materialized: view,  +schema: intermediate }
      marts:        { +materialized: table, +schema: marts }
  ```
- `dbt/profiles.yml.example` — como conectar no Postgres warehouse (host, porta, user,
  senha, dbname, schema). No container, lê de variáveis de ambiente `WAREHOUSE_*`.
- `dbt/packages.yml` — já existe (dbt-expectations). Rodar `dbt deps`.

Conceito de estudo: o `generate_schema_name.sql` (macro) controla como o dbt nomeia os
schemas. Por padrão o dbt **prefixa** o schema do profile (ex.: `analytics_staging`).
Vamos sobrescrever a macro para usar o schema "limpo" (`staging`, `marts`) — comportamento
mais previsível e o que combinamos nos schemas do warehouse.

Verificação: `dbt debug` conecta; `dbt deps` baixa o pacote.

### Etapa 2.1 — Seed do catálogo de indicadores

Objetivo: ter a dimensão `dim_indicadores` no banco.

- `dbt/seeds/dim_indicadores.csv` — metadados das 11 séries (código SGS, indicador, nome,
  unidade, frequência, fonte). É a versão "tabela" do catálogo que vive em
  `src/bacen/sgs/series.py`. Manter os dois em sincronia.
- `dbt seed` carrega o CSV como tabela. Os marts fazem JOIN nela para enriquecer (nome
  bonito, unidade) sem hard-code de strings nos SQLs.

Conceito de estudo: por que seed e não um model? Seed é para dado **pequeno, estático e
de origem manual**. Catálogo de 11 linhas que muda raramente é o caso clássico.

### Etapa 2.2 — Sources (declarar o raw)

Objetivo: o dbt conhece as tabelas `raw.bacen_*` como fontes.

- `dbt/models/staging/_staging__sources.yml` — declara o source `bacen` apontando para o
  schema `raw` e suas 5 tabelas. Aqui já adicionamos **testes de fonte** (freshness e
  not_null em colunas-chave) — falham se a ingestão parar de atualizar.

Conceito de estudo: a diferença entre `source()` e `ref()`. `source()` aponta para dado
que entrou por fora do dbt (nossa ingestão); `ref()` aponta para outro model dbt. Usar
`source()` no staging deixa explícita a fronteira "aqui começa o território do dbt" e
permite o dbt rastrear a linhagem desde a origem.

### Etapa 2.3 — Camada staging (5 models)

Objetivo: cada tabela raw vira um staging limpo.

Para cada um (`stg_bacen__inflacao`, `..._juros`, `..._cambio`, `..._credito`, `..._focus`):
- `SELECT` de `{{ source('bacen', 'bacen_<grupo>') }}`
- renomeia/tipa colunas, filtra `valor IS NULL`
- normaliza para **formato longo** onde o grupo tem vários indicadores (uma linha por
  indicador por data) — facilita unir tudo depois
- caso especial `juros`: separar SELIC diária de Meta SELIC; converter taxa diária para
  anualizada com a macro `anualizar_taxa_diaria` (nunca misturar frequências sem converter)
- `_staging__models.yml`: descrição de cada model e coluna + testes `not_null`/`unique`
  nas chaves (`data`, `indicador`)

Verificação: `dbt build --select staging` cria as 5 views e passa nos testes.

### Etapa 2.4 — Camada intermediate (2 models)

Objetivo: alinhar e cruzar os indicadores.

- `int_indicadores__alinhados.sql` — une os 5 staging e alinha tudo para **granularidade
  mensal**: média do mês para séries diárias (câmbio, SELIC diária), último valor para
  séries por reunião (Meta SELIC), valor do mês para mensais. Resultado: uma linha por mês
  com cada indicador numa coluna. Janela: últimos 10 anos.
- `int_focus__vs_realizado.sql` — junta a expectativa Focus (ex.: Focus IPCA) com o valor
  realizado correspondente (IPCA) e calcula desvio absoluto e percentual.

Conceito de estudo: **alinhamento de granularidade** é o coração da modelagem de séries
temporais. Você não pode comparar uma taxa diária com uma mensal sem decidir como agregar
(média? fim de período? acumulado?). Cada escolha é uma decisão de negócio — documente.

### Etapa 2.5 — Camada marts (3 models)

Objetivo: tabelas finais para o dashboard.

- `mart_macro__painel.sql` — de `int_indicadores__alinhados`, adiciona variações MoM e YoY
  por indicador usando a macro `variacao_percentual`. **Materialização incremental** por
  `data_referencia` (só processa meses novos). É a tabela central do Metabase.
- `mart_macro__correlacoes.sql` — médias móveis e janelas de 3/6/12 meses (SELIC, IPCA, câmbio).
- `mart_focus__acuracia.sql` — agrega o desvio médio do Focus por indicador por ano.

Conceito de estudo — **materialização incremental**: a primeira execução cria a tabela
inteira; as seguintes inserem só o que é novo. O dbt fornece o bloco
`{% if is_incremental() %} where data_referencia > (select max(data_referencia) from {{ this }}) {% endif %}`.
`{{ this }}` é o próprio model. Você define a chave única (`unique_key`) para o dbt saber
o que atualizar vs inserir. Aqui o volume é pequeno, então o incremental é mais
demonstração de domínio do que necessidade — e isso é honesto registrar.

### Etapa 2.6 — Macros

- `variacao_percentual(coluna, particao, ordem)` — variação % vs período anterior via `lag()`.
- `anualizar_taxa_diaria(coluna)` — `(1 + r/100)^252 - 1`, dias úteis.
- `generate_schema_name` — sobrescreve o naming de schema (etapa 2.0).

Conceito de estudo: macro é função. Onde você repetiria o mesmo trecho de SQL em 3 models,
extraia para uma macro. Jinja (`{% macro %}`) roda em tempo de compilação e gera SQL puro.

### Etapa 2.7 — Testes (a parte que sinaliza maturidade)

Duas frentes:
- **Genéricos** (no `.yml`): `not_null`, `unique`, `accepted_values`, `relationships`
  (ex.: todo `indicador` no painel existe em `dim_indicadores`).
- **dbt-expectations** (pacote): `expect_column_values_to_be_between` (ex.: SELIC entre 0 e 100),
  `expect_column_values_to_not_be_null`, etc. — mais expressivo que os nativos.
- **Singulares** (`tests/*.sql`): uma query que retorna as linhas que **violam** a regra; se
  retornar zero linhas, passa. Ex.: `assert_selic_positiva.sql`.

Conceito de estudo: teste em dbt não testa código, testa **dados**. Roda a cada `dbt build`,
e numa pipeline com quality gate (a nossa) ele bloqueia dado ruim de chegar ao consumidor.

### Etapa 2.8 — Documentação dbt

- Preencher `description:` em todo model e coluna nos `.yml`.
- `dbt docs generate` produz um site navegável com o **grafo de linhagem** (de raw até mart)
  e o dicionário de dados. Publicado no GitHub Pages na Fase 3.

Conceito de estudo: a linhagem (lineage graph) é gerada automaticamente a partir dos `ref()`
e `source()`. É documentação que não desatualiza, porque nasce do próprio código.

---

## 6. Integração com o Airflow (ponte para a Fase 3)

A camada dbt não roda sozinha em produção — quem dispara é o Airflow, na DAG
`bacen_transform`, que é acionada pelo Asset publicado após a ingestão (data-aware).

Dois passos planejados:
1. **Hoje (passo 1):** `BashOperator` roda `dbt deps` → `dbt seed` → `dbt build`. Simples,
   destrava o fluxo end-to-end. O dbt vive num venv isolado (`/opt/airflow/dbt-venv`, ADR 0001).
2. **Fase 3 (passo 2):** promover para **Astronomer Cosmos**, que lê o `manifest.json` do dbt
   e renderiza **cada model como uma task nativa** do Airflow. Ganho: visibilidade
   model-a-model na UI (o grafo `stg_* → int_* → mart_*` aparece no Airflow), retry por
   model, e o print que vende dbt no portfólio.

Conceito de estudo: o `manifest.json` (gerado em `dbt/target/`) é o "mapa" que o dbt produz
do projeto — todos os models, testes e dependências. Cosmos consome esse mapa para traduzir
o DAG do dbt no DAG do Airflow.

---

## 7. Ordem de trabalho resumida (checklist)

- [ ] 2.0 `dbt_project.yml` + `profiles.yml.example` + `dbt deps` + `dbt debug` verde
- [ ] 2.1 seed `dim_indicadores.csv` + `dbt seed`
- [ ] 2.2 `_staging__sources.yml` (sources + testes de fonte)
- [ ] 2.3 5 models staging + `_staging__models.yml` + testes — `dbt build --select staging`
- [ ] 2.4 2 models intermediate + `.yml`
- [ ] 2.5 3 models marts (incremental no painel) + `.yml`
- [ ] 2.6 macros (`variacao_percentual`, `anualizar_taxa_diaria`, `generate_schema_name`)
- [ ] 2.7 testes (genéricos + dbt-expectations + singulares)
- [ ] 2.8 descrições + `dbt docs generate`
- [ ] Ponte Airflow: `dbt build` verde via `make dbt-build`, depois Asset-triggered

Pré-requisito desta fase: Fase 1 (ingestão) populando `raw.*`. Sem dado no raw, o staging
roda mas devolve vazio — dá para desenvolver com um seed de amostra no raw se quiser
adiantar o dbt antes da ingestão estar pronta.

---

## 8. Comandos dbt que você vai usar (referência de estudo)

| Comando | O que faz |
|---|---|
| `dbt debug` | Testa a conexão e a config. Primeiro comando sempre. |
| `dbt deps` | Instala os packages do `packages.yml`. |
| `dbt seed` | Carrega os CSVs de `seeds/` como tabelas. |
| `dbt run` | Materializa os models (views/tables). Não roda testes. |
| `dbt test` | Roda só os testes sobre o que já está materializado. |
| `dbt build` | `seed` + `run` + `test` + `snapshot` na ordem do grafo. O comando do dia a dia. |
| `dbt run --select staging` | Roda só uma pasta/seleção. `+modelo` inclui dependências. |
| `dbt run --select state:modified+` | Só o que mudou vs um estado anterior (base do CI). |
| `dbt docs generate` / `dbt docs serve` | Gera e serve a documentação navegável. |

No nosso setup, prefixe com o binário do venv: `/opt/airflow/dbt-venv/bin/dbt ...`, ou use
os atalhos `make dbt-build` / `make dbt-docs`.
