"""Testes das funcoes puras do client SGS: parse do payload e fatiamento de janelas.

Nao tocam a rede — exercitam so a logica de transformacao (parse) e de particionamento
do intervalo (janelas), que sao as partes com risco de bug.
"""
from __future__ import annotations

from datetime import date
from itertools import pairwise

from src.bacen.sgs.client import SerieRecord, _janelas, _parse


def test_parse_converte_data_e_valor():
    payload = [
        {"data": "01/02/2020", "valor": "4.31"},
        {"data": "01/03/2020", "valor": "0.07"},
    ]
    registros = _parse(433, "ipca", payload)
    assert registros == [
        SerieRecord(433, "ipca", "2020-02-01", 4.31),
        SerieRecord(433, "ipca", "2020-03-01", 0.07),
    ]


def test_parse_valor_vazio_vira_none():
    registros = _parse(11, "selic_diaria", [{"data": "31/12/2021", "valor": ""}])
    assert registros[0].valor is None
    assert registros[0].data == "2021-12-31"


def test_parse_payload_vazio():
    assert _parse(1, "usd_brl", []) == []


def test_janelas_intervalo_curto_e_uma_so():
    janelas = list(_janelas(date(2024, 1, 1), date(2024, 6, 1), max_dias=3650))
    assert janelas == [(date(2024, 1, 1), date(2024, 6, 1))]


def test_janelas_fatiamento_sem_sobreposicao_nem_buraco():
    inicio, fim = date(2000, 1, 1), date(2024, 1, 1)
    janelas = list(_janelas(inicio, fim, max_dias=3650))
    assert len(janelas) > 1
    assert janelas[0][0] == inicio
    assert janelas[-1][1] == fim
    # cada janela comeca exatamente um dia apos o fim da anterior (cobertura continua)
    for (_, fim_anterior), (ini_seguinte, _) in pairwise(janelas):
        assert (ini_seguinte - fim_anterior).days == 1
