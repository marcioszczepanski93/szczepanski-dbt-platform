"""Watermark da ingestao: ultima data ja carregada por grupo no schema raw.

Determina a data_inicial da proxima busca, tornando a ingestao incremental em vez
de re-baixar a janela inteira a cada execucao.
"""
from __future__ import annotations

from datetime import date

from src.bacen.sgs.series import GRUPOS


def last_ingested_date(grupo: str) -> date | None:
    """select max(data) from raw.bacen_<grupo>. None se a tabela estiver vazia.

    `grupo` e validado contra a allowlist GRUPOS antes de entrar no SQL — o nome da
    tabela e interpolado, entao a validacao fecha a porta para injecao.
    """
    if grupo not in GRUPOS:
        raise ValueError(f"Grupo desconhecido: {grupo!r}. Validos: {GRUPOS}")

    from include.warehouse import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT max(data) FROM raw.bacen_{grupo}")  # noqa: S608 — grupo na allowlist
        (maximo,) = cur.fetchone()
    return maximo
