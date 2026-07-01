"""DAG de transformacao dbt, disparada pelo Asset publicado pela ingestao.

Passo 1 (esta versao): roda `dbt build` via BashOperator — destrava o pipeline
end-to-end com o minimo de setup. Passo 2 (Fase 3): promover para Astronomer
Cosmos, que renderiza cada modelo dbt como uma task nativa na UI. A promocao
sera registrada em ADR.

schedule = [Asset(...)] -> agendamento data-aware: roda apos cada ingestao
bem-sucedida, nao por cron.
"""
from __future__ import annotations

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import Asset, dag

from include.alerting import email_on_failure

RAW_BACEN = Asset("warehouse://raw.bacen")

DBT_DIR = "/opt/airflow/dbt"
# dbt vive num venv isolado (ver Dockerfile / ADR 0001) — invocar o binario de la,
# nao o do ambiente do Airflow.
DBT_BIN = "/opt/airflow/dbt-venv/bin/dbt"
DBT_FLAGS = f"--project-dir {DBT_DIR} --profiles-dir {DBT_DIR}"


@dag(
    dag_id="bacen_transform",
    schedule=[RAW_BACEN],
    catchup=False,
    max_active_runs=1,
    default_args={"on_failure_callback": email_on_failure},
    tags=["bacen", "dbt", "transform"],
)
def bacen_transform():
    deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"{DBT_BIN} deps {DBT_FLAGS}",
    )
    seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"{DBT_BIN} seed {DBT_FLAGS}",
    )
    build = BashOperator(
        task_id="dbt_build",
        bash_command=f"{DBT_BIN} build {DBT_FLAGS}",
    )
    deps >> seed >> build


bacen_transform()
