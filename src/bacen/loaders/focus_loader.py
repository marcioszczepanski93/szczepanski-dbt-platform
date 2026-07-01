"""Loader idempotente das expectativas Focus em raw.focus_expectativas."""
from __future__ import annotations

from collections.abc import Sequence

from include.observability import get_logger
from src.bacen.olinda.client import ExpectativaRecord

log = get_logger("bacen.focus_loader")


def upsert_expectativas(registros: Sequence[ExpectativaRecord]) -> int:
    """Upsert ON CONFLICT (indicador, horizonte, data_expectativa) DO NOTHING."""
    if not registros:
        log.info("Nada a carregar (focus).")
        return 0

    from psycopg2.extras import execute_values

    from include.warehouse import get_connection

    linhas = [
        (r.indicador, r.horizonte, r.data_expectativa, r.mediana, r.media, r.n_respondentes)
        for r in registros
    ]
    sql = (
        "INSERT INTO raw.focus_expectativas "
        "(indicador, horizonte, data_expectativa, mediana, media, n_respondentes) "
        "VALUES %s ON CONFLICT (indicador, horizonte, data_expectativa) DO NOTHING"
    )
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(cur, sql, linhas, page_size=1000)
    log.info("Expectativas carregadas.", extra={"context": {"registros": len(linhas)}})
    return len(linhas)
