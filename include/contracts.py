"""Contratos de dados (pandera) — fronteira de qualidade da camada de ingestao.

Validamos o lote `raw` ANTES de liberar a transformacao dbt. Soma-se aos testes
dbt das marts (que cobrem o outro lado), nao os substitui: aqui garantimos que o
dado bruto que entra no warehouse tem forma minima confiavel.
"""
from __future__ import annotations

from typing import Any

import pandera.pandas as pa
from pandera.typing import Series


class SerieRawContract(pa.DataFrameModel):
    """Contrato de uma linha de raw.bacen_* (ponto, serie temporal BACEN)."""

    codigo_sgs: Series[int] = pa.Field(nullable=False, gt=0)
    indicador: Series[str] = pa.Field(nullable=False)
    data: Series[str] = pa.Field(nullable=False)  # ISO date (YYYY-MM-DD)
    valor: Series[float] = pa.Field(nullable=True)

    class Config:
        strict = False
        coerce = True



class FocusExpectativaContract(pa.DataFrameModel):
    """Contrato de uma linha de raw.focus_expectativas (expectativa Focus)."""

    indicador: Series[str] = pa.Field(nullable=False)
    horizonte: Series[str] = pa.Field(nullable=False)
    data_expectativa: Series[str] = pa.Field(nullable=False)  # ISO date
    mediana: Series[float] = pa.Field(nullable=False)
    media: Series[float] = pa.Field(nullable=True)

    class Config:
        strict = False
        coerce = True


def validate_series_raw(records: list[dict[str, Any]]) -> None:
    """Valida um lote de pontos de serie contra o contrato. Levanta em violacao.

    lazy=True acumula TODAS as violacoes numa unica excecao (em vez de parar na
    primeira) — o relatorio vira diagnostico util no log/alerta. pandas importado
    localmente para nao pesar o import deste modulo.
    """
    import pandas as pd

    SerieRawContract.validate(pd.DataFrame(records), lazy=True)


def validate_focus_expectativas(records: list[dict[str, Any]]) -> None:
    """Valida um lote de expectativas Focus contra o contrato. Levanta em violacao."""
    import pandas as pd

    FocusExpectativaContract.validate(pd.DataFrame(records), lazy=True)
