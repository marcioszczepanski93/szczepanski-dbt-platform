# 0001 — dbt em venv isolado do ambiente do Airflow

Status: aceito
Data: 2026-06-30

## Contexto

O Airflow orquestra a transformacao dbt, e tanto o Airflow quanto o dbt-core sao
instalados via pip na mesma imagem. Os dois compartilham dependencias transitivas
(jinja2, click, protobuf, typing-extensions, entre outras) com faixas de versao
diferentes. O Airflow precisa ser instalado sob seu constraints file oficial para o
core nao quebrar; o dbt, instalado no mesmo ambiente, ou e forcado a versoes que ele
nao suporta, ou quebra o constraints. Esse conflito e uma fonte conhecida de builds
frageis e dificeis de reproduzir.

A execucao do dbt acontece em dois lugares: orquestrada (dentro do container do
Airflow) e, eventualmente, em desenvolvimento local. A decisao aqui trata do ambiente
de runtime dentro da imagem.

## Decisao

Instalar o dbt num **virtualenv dedicado** na imagem (`/opt/airflow/dbt-venv`),
separado do ambiente do Airflow, **sem** aplicar o constraints file do Airflow.

- `requirements.txt` (ambiente do Airflow): apenas providers, `astronomer-cosmos`,
  e deps de ingestao (httpx, psycopg2, pandera, pandas). Cosmos e provider do Airflow
  e fica aqui.
- `dbt-requirements.txt` (venv isolado): `dbt-postgres` e suas deps, resolvidas
  livremente.
- A invocacao do dbt usa o binario do venv: `/opt/airflow/dbt-venv/bin/dbt`
  (BashOperator hoje; via `dbt_executable_path` do Cosmos na promocao da Fase 3).
- Pacotes dbt (ex.: dbt-expectations) sao declarados em `dbt/packages.yml` e
  instalados com `dbt deps`, nunca via pip.

## Consequencias

Positivas:
- Elimina o conflito de dependencias entre dbt e Airflow; cada um resolve suas versoes.
- Atualizar dbt nao arrisca o core do Airflow, e vice-versa.
- Coerente com o padrao recomendado pelo Cosmos (executar dbt num interpretador proprio).

Negativas / trade-offs:
- Dois conjuntos de dependencias na imagem (build um pouco maior e mais lento).
- O caminho do binario do dbt vira detalhe de infra que as DAGs/Makefile precisam
  conhecer (`/opt/airflow/dbt-venv/bin/dbt`).
- Em modo Cosmos LOCAL apontando para o venv, e preciso garantir que o
  `dbt_executable_path` esteja configurado; do contrario o Cosmos tentaria o dbt do
  ambiente do Airflow (que nao existe mais ali).

## Alternativas consideradas

- **dbt no mesmo ambiente do Airflow**: mais simples, menos arquivos, mas reintroduz
  o conflito de constraints — o motivo original desta decisao.
- **Container dbt separado (DockerOperator)**: isola o runtime de forma ainda mais
  forte, mas contraria a decisao de orquestracao in-process (sem socket Docker) e
  some com a visibilidade modelo-a-modelo que o Cosmos da na UI.
