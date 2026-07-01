"""DAG de transformacao dbt via Astronomer Cosmos.

Cada model/seed/test do dbt vira uma task NATIVA do Airflow: o grafo
seed -> stg_* -> int_* -> mart_* (com os testes) aparece na UI, com retry por node.
E a promocao do passo 1 (BashOperator unico) registrada no ADR 0003.

Disparada pelo Asset publicado pela ingestao (data-aware), nao por cron. O dbt roda
no venv ISOLADO (ADR 0001) via ExecutionMode.LOCAL + dbt_executable_path.
"""
from __future__ import annotations

import os

import pendulum
from airflow.sdk import Asset
from cosmos import DbtDag, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import ExecutionMode, InvocationMode, LoadMode

from include.alerting import email_on_failure

# Defaults do container; sobreponiveis por env (portabilidade CI / outra maquina).
DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt")
DBT_EXECUTABLE = os.environ.get("DBT_EXECUTABLE", "/opt/airflow/dbt-venv/bin/dbt")

# profiles.yml versionado, baseado em env_var (sem segredos); Cosmos so aponta para ele.
profile_config = ProfileConfig(
    profile_name="bacen",
    target_name="dev",
    profiles_yml_filepath=f"{DBT_PROJECT_DIR}/profiles.yml",
)

bacen_transform = DbtDag(
    dag_id="bacen_transform",
    project_config=ProjectConfig(DBT_PROJECT_DIR),
    profile_config=profile_config,
    # SUBPROCESS (nao DBT_RUNNER): o dbt vive num venv isolado, nao importavel no
    # ambiente do Airflow (ADR 0001). Cosmos entao invoca o binario do venv por subprocess.
    execution_config=ExecutionConfig(
        execution_mode=ExecutionMode.LOCAL,
        invocation_mode=InvocationMode.SUBPROCESS,
        dbt_executable_path=DBT_EXECUTABLE,
    ),
    # DBT_LS: Cosmos roda `dbt ls` (no venv) para montar o grafo no parse — sem tocar
    # o banco. Os packages (dbt-expectations) ja estao instalados em dbt/dbt_packages.
    render_config=RenderConfig(
        load_method=LoadMode.DBT_LS,
        invocation_mode=InvocationMode.SUBPROCESS,
        dbt_executable_path=DBT_EXECUTABLE,
    ),
    schedule=[Asset("warehouse://raw.bacen")],
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    default_args={"on_failure_callback": email_on_failure},
    tags=["bacen", "dbt", "transform"],
)
