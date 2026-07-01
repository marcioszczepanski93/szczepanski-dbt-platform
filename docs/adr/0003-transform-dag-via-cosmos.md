# 0003 — Transformacao dbt orquestrada via Astronomer Cosmos

Status: aceito
Data: 2026-07-01

## Contexto

A DAG `bacen_transform` comecou (passo 1, deliberadamente simples) como um unico
`BashOperator` rodando `dbt build`. Isso destravou o fluxo end-to-end, mas trata o dbt
como caixa preta: na UI do Airflow a transformacao inteira e uma so task, sem
visibilidade por model, sem retry granular e sem lineage.

## Decisao

Promover a `bacen_transform` para **Astronomer Cosmos** (`DbtDag`), que le o projeto dbt
e gera uma task nativa do Airflow por node (seed, cada model em `.run` + `.test`).

- `ExecutionMode.LOCAL` com `InvocationMode.SUBPROCESS` e
  `dbt_executable_path=/opt/airflow/dbt-venv/bin/dbt`: o Cosmos vive no ambiente do
  Airflow, mas invoca o dbt do venv isolado (ADR 0001) por subprocess. DBT_RUNNER
  (import in-process) nao serve, pois o dbt nao esta no ambiente do Airflow.
- `RenderConfig(load_method=DBT_LS, invocation_mode=SUBPROCESS)`: o grafo e montado no
  parse rodando `dbt ls` no venv (nao toca o banco). Reflete sempre os models atuais,
  sem depender de um manifest versionado.
- Disparo por Asset (`warehouse://raw.bacen`), mantido da versao anterior: data-aware,
  roda apos a ingestao.

Resultado verificado: 22 nodes renderizados; `airflow dags test bacen_transform` conclui
com `state=success`, cada model chamando o dbt do venv por subprocess.

## Consequencias

Positivas:
- Visibilidade model-a-model na UI (grafo seed -> stg_* -> int_* -> mart_* com testes) —
  o print que evidencia dominio de dbt+Airflow no portfolio.
- Retry por node; uma falha isolada nao re-roda o projeto inteiro.
- Cosmos emite Assets por model (lineage no data-aware scheduling).

Negativas / trade-offs:
- O parse da DAG passa a rodar `dbt ls` (mais pesado que uma DAG trivial). E o preco de
  ter o grafo dbt na UI; mitigado por rodar via subprocess no venv, sem tocar o banco.
- Depende do `dbt/dbt_packages` instalado (dbt-expectations) para o `dbt ls` resolver os
  testes no parse. Garantido por `dbt deps` (imagem/CI).

## Alternativas consideradas

- **Manter o BashOperator**: mais simples, parse trivial, mas sem a visibilidade que
  justifica usar dbt num portfolio.
- **LoadMode.DBT_MANIFEST**: parse ainda mais leve (le manifest.json), mas exige manter o
  manifest atualizado e versionado — escolhemos DBT_LS para o grafo nunca ficar defasado.
