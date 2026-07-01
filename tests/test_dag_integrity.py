"""Integridade das DAGs: sem erro de import, sem ciclo, com tags.

Carrega o DagBag apontando para a pasta dags/ e falha se qualquer DAG nao parsear.
Nao depende de runtime (imports pesados estao dentro das tasks).
"""
from __future__ import annotations

from pathlib import Path

import pytest

DAGS_FOLDER = Path(__file__).resolve().parents[1] / "dags"


@pytest.fixture(scope="module")
def dagbag():
    from airflow.models import DagBag

    return DagBag(dag_folder=str(DAGS_FOLDER), include_examples=False)


def test_no_import_errors(dagbag):
    assert not dagbag.import_errors, f"Erros de import nas DAGs: {dagbag.import_errors}"


def test_dags_expected_present(dagbag):
    # Usa o dict em memoria (dagbag.dags), nao get_dag() — este ultimo consulta o
    # banco de metadata no Airflow 3, e o teste de integridade nao deve depender dele.
    for dag_id in ("bacen_ingestion", "bacen_transform"):
        assert dag_id in dagbag.dags, f"DAG ausente: {dag_id}"


def test_dags_have_tags(dagbag):
    for dag_id, dag in dagbag.dags.items():
        assert dag.tags, f"DAG sem tags: {dag_id}"
