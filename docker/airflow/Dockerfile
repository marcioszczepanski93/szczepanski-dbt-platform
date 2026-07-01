# Imagem do Airflow 3 estendida com Cosmos + deps de ingestao, e um venv ISOLADO para o dbt.
#
# Por que o venv separado (ADR 0001): dbt-core e Airflow compartilham dependencias
# (jinja2, click, protobuf...) que colidem com o constraints file do Airflow. Manter o
# dbt num venv proprio elimina o conflito. O Cosmos (no ambiente do Airflow) invoca o
# binario do dbt em /opt/airflow/dbt-venv via dbt_executable_path.
ARG AIRFLOW_VERSION=3.0.3
FROM apache/airflow:${AIRFLOW_VERSION}

ARG AIRFLOW_VERSION
USER airflow

# 1) Deps do ambiente do Airflow, sob o constraints file da versao (nao quebra o core).
COPY requirements.txt /tmp/requirements.txt
RUN PYTHON_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" && \
    pip install --no-cache-dir -r /tmp/requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

# 2) Deps de desenvolvimento/teste (pytest) no ambiente do Airflow, sob constraints.
#    Permitem `make test` dentro do container. Imagem de uso local.
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN PYTHON_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" && \
    pip install --no-cache-dir -r /tmp/requirements-dev.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

# 3) dbt num venv isolado, SEM o constraints do Airflow.
COPY dbt-requirements.txt /tmp/dbt-requirements.txt
RUN python -m venv /opt/airflow/dbt-venv && \
    /opt/airflow/dbt-venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/airflow/dbt-venv/bin/pip install --no-cache-dir -r /tmp/dbt-requirements.txt

ENV DBT_VENV=/opt/airflow/dbt-venv
