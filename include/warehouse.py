"""Acesso ao Postgres analytics (warehouse). Reusavel entre tasks de ingestao.

Conexao preguicosa (lazy) — nada de I/O no import, para nao pesar o parse das DAGs.
Le as credenciais de WAREHOUSE_* do ambiente; sem fallback de senha em codigo.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from psycopg2.extensions import connection as PgConnection


def _dsn() -> str:
    return (
        f"host={os.environ['WAREHOUSE_HOST']} "
        f"port={os.environ.get('WAREHOUSE_PORT', '5432')} "
        f"dbname={os.environ['WAREHOUSE_DB']} "
        f"user={os.environ['WAREHOUSE_USER']} "
        f"password={os.environ['WAREHOUSE_PASSWORD']}"
    )


@contextmanager
def get_connection() -> Iterator[PgConnection]:
    """Context manager de conexao psycopg2 com commit/rollback automatico."""
    import psycopg2

    conn = psycopg2.connect(_dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
