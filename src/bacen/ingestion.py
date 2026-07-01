"""Orquestra a ingestao de um grupo de series: freshness -> fetch -> validate -> upsert.

Chamada pela task da DAG (import lazy). O contrato pandera e validado ANTES do upsert
(gate pre-publicacao): dado que quebra o contrato nunca chega ao schema raw, ao contrario
de um gate pos-publicacao. Em violacao, a funcao levanta -> a task falha -> alerta.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date

from include.observability import get_logger
from src.bacen.sgs.client import BacenSGSClient
from src.bacen.sgs.freshness import last_ingested_date
from src.bacen.sgs.series import series_do_grupo

log = get_logger("bacen.ingestion")

_INITIAL_LOOKBACK_YEARS = 10  # janela do backfill quando o raw esta vazio


def run_ingestion(grupo: str, client: BacenSGSClient | None = None) -> int:
    """Ingesta todas as series do grupo desde o watermark. Retorna o total carregado."""
    from include.contracts import validate_series_raw
    from src.bacen.loaders.postgres_loader import upsert_serie

    client = client or BacenSGSClient()
    data_final = date.today()
    ultimo = last_ingested_date(grupo)
    data_inicial = ultimo or date(data_final.year - _INITIAL_LOOKBACK_YEARS, 1, 1)
    ctx = {"grupo": grupo, "de": data_inicial.isoformat(), "ate": data_final.isoformat()}
    log.info("Ingestao iniciada.", extra={"context": ctx})

    registros = []
    for serie in series_do_grupo(grupo):
        registros.extend(
            client.fetch_serie(serie.codigo_sgs, serie.indicador, data_inicial, data_final)
        )

    if registros:
        # Gate pre-publicacao: valida a forma do lote antes de tocar o banco.
        validate_series_raw([asdict(r) for r in registros])

    total = upsert_serie(grupo, registros)
    log.info("Ingestao concluida.", extra={"context": {"grupo": grupo, "carregados": total}})
    return total


def _last_focus_date() -> date | None:
    from include.warehouse import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select max(data_expectativa) from raw.focus_expectativas")
        (maximo,) = cur.fetchone()
    return maximo


def run_focus_expectativas(client=None) -> int:
    """Ingesta as expectativas Focus (IPCA 12m) da API Olinda. Retorna o total carregado."""
    from dataclasses import asdict

    from include.contracts import validate_focus_expectativas
    from src.bacen.loaders.focus_loader import upsert_expectativas
    from src.bacen.olinda.client import OlindaExpectativasClient

    client = client or OlindaExpectativasClient()
    ultimo = _last_focus_date()
    data_inicial = ultimo or date(date.today().year - _INITIAL_LOOKBACK_YEARS, 1, 1)
    log.info("Ingestao Focus iniciada.", extra={"context": {"de": data_inicial.isoformat()}})

    registros = client.fetch_ipca_12m(data_inicial)
    if registros:
        validate_focus_expectativas([asdict(r) for r in registros])
    total = upsert_expectativas(registros)
    log.info("Ingestao Focus concluida.", extra={"context": {"carregados": total}})
    return total

