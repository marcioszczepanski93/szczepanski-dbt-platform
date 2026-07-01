"""Testes do contrato pandera do lote raw (include.contracts.validate_series_raw)."""
from __future__ import annotations

import pytest
from pandera.errors import SchemaErrors

from include.contracts import validate_series_raw


def test_lote_valido_passa():
    lote = [
        {"codigo_sgs": 433, "indicador": "ipca", "data": "2020-02-01", "valor": 4.31},
        {"codigo_sgs": 11, "indicador": "selic_diaria", "data": "2021-12-31", "valor": None},
    ]
    validate_series_raw(lote)  # nao deve levantar


def test_codigo_sgs_invalido_quebra():
    lote = [{"codigo_sgs": 0, "indicador": "ipca", "data": "2020-02-01", "valor": 4.31}]
    with pytest.raises(SchemaErrors):
        validate_series_raw(lote)


def test_indicador_nulo_quebra():
    lote = [{"codigo_sgs": 433, "indicador": None, "data": "2020-02-01", "valor": 4.31}]
    with pytest.raises(SchemaErrors):
        validate_series_raw(lote)
