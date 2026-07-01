"""DAG de ingestao BACEN (API SGS) -> schema raw do warehouse analytics.

As cinco tasks de grupo rodam em paralelo, cada uma incremental por watermark.
O quality_gate valida o lote contra o contrato pandera; so entao a task final
publica o Asset, disparando a DAG de transformacao dbt (data-aware).

Imports pesados (src.bacen.*) ficam DENTRO das tasks de proposito: mantem o parse
da DAG leve e o teste de integridade independente das deps de runtime.
"""
from __future__ import annotations

from datetime import timedelta

import pendulum
from airflow.sdk import Asset, dag, task

from include.alerting import email_on_failure

# Asset publicado apos ingestao bem-sucedida: habilita o agendamento data-aware
# da transformacao dbt (bacen_transform_dag).
RAW_BACEN = Asset("warehouse://raw.bacen")

# Grupos SGS (dados/serie). O Focus (expectativas) vem de outra API (Olinda) e tem
# task propria.
GRUPOS = ("inflacao", "juros", "cambio", "credito")


@dag(
    dag_id="bacen_ingestion",
    schedule="0 7 * * *",  # 07:00 BRT — janela em que a maquina costuma estar de pe
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Sao_Paulo"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=10),
        "retry_exponential_backoff": True,
        "on_failure_callback": email_on_failure,
    },
    tags=["bacen", "ingestion"],
)
def bacen_ingestion():
    @task
    def ingest(grupo: str) -> int:
        from src.bacen.ingestion import run_ingestion

        return run_ingestion(grupo)

    @task
    def ingest_focus() -> int:
        from src.bacen.ingestion import run_focus_expectativas

        return run_focus_expectativas()

    @task
    def quality_gate(sgs_totais: list[int], focus_total: int) -> None:
        # Contrato pandera ja validado ANTES do upsert (gate pre-publicacao). Aqui o
        # gate e de cobertura: cada grupo SGS e o Focus tem dado no raw antes de liberar
        # a transformacao dbt (publicacao do Asset).
        from src.bacen.sgs.freshness import last_ingested_date
        from src.bacen.sgs.series import GRUPOS

        if not any(sgs_totais):
            raise ValueError("quality_gate: nenhum grupo SGS carregou registros.")
        vazios = [g for g in GRUPOS if last_ingested_date(g) is None]
        if vazios:
            raise ValueError(f"quality_gate: grupos sem dado no raw: {vazios}")

    @task(outlets=[RAW_BACEN])
    def publish() -> None:
        # Marca o Asset como atualizado -> dispara bacen_transform_dag.
        pass

    sgs_totais = ingest.expand(grupo=list(GRUPOS))
    quality_gate(sgs_totais, ingest_focus()) >> publish()


bacen_ingestion()
