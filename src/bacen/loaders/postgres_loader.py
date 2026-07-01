"""Loader idempotente no schema raw.

Upsert via INSERT ... ON CONFLICT (codigo_sgs, data) DO NOTHING: re-executar a
ingestao nunca duplica nem altera o que ja existe. Trade-off consciente do
DO NOTHING: revisoes de valor de uma data ja carregada sao ignoradas. Para series
macro do BACEN isso e aceitavel no escopo deste projeto; migrar para DO UPDATE
(capturando revisoes) fica como evolucao candidata a ADR.
"""
from __future__ import annotations

from collections.abc import Sequence

from include.observability import get_logger
from src.bacen.sgs.client import SerieRecord
from src.bacen.sgs.series import GRUPOS

log = get_logger("bacen.loader")


def upsert_serie(grupo: str, registros: Sequence[SerieRecord]) -> int:
    """Insere os registros em raw.bacen_<grupo> ignorando conflitos. Retorna o total enviado.

    `grupo` validado contra GRUPOS antes de compor o nome da tabela (anti-injecao).
    """
    if grupo not in GRUPOS:
        raise ValueError(f"Grupo desconhecido: {grupo!r}. Validos: {GRUPOS}")
    if not registros:
        log.info("Nada a carregar.", extra={"context": {"grupo": grupo}})
        return 0

    from psycopg2.extras import execute_values

    from include.warehouse import get_connection

    linhas = [(r.codigo_sgs, r.indicador, r.data, r.valor) for r in registros]
    sql = (
        f"INSERT INTO raw.bacen_{grupo} (codigo_sgs, indicador, data, valor) "  # noqa: S608 — allowlist
        "VALUES %s ON CONFLICT (codigo_sgs, data) DO NOTHING"
    )
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(cur, sql, linhas, page_size=1000)
    log.info("Lote carregado.", extra={"context": {"grupo": grupo, "registros": len(linhas)}})
    return len(linhas)
