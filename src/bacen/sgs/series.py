"""Catalogo de series BACEN (API SGS) — fonte unica da verdade do mapeamento.

Usado pela ingestao (quais codigos buscar por grupo) e espelhado no seed dbt
`dim_indicadores.csv`. Manter os dois em sincronia: alteracao aqui implica
atualizar o seed (ou vice-versa).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Serie:
    codigo_sgs: int
    indicador: str
    grupo: str
    frequencia: str  # 'diaria', 'mensal', 'reuniao', 'semanal'


SERIES: tuple[Serie, ...] = (
    # Inflacao
    Serie(433, "ipca", "inflacao", "mensal"),
    Serie(7478, "ipca15", "inflacao", "mensal"),
    Serie(189, "igpm", "inflacao", "mensal"),
    # Juros
    Serie(11, "selic_diaria", "juros", "diaria"),
    Serie(432, "meta_selic", "juros", "reuniao"),
    # Cambio
    Serie(1, "usd_brl", "cambio", "diaria"),
    Serie(21619, "eur_brl", "cambio", "diaria"),
    # Credito
    Serie(21082, "inadimplencia_pf", "credito", "mensal"),
    Serie(20783, "spread_medio", "credito", "mensal"),
    # Nota: expectativas Focus NAO vem do SGS. Vem da API Olinda "Expectativas de
    # Mercado" (ver src/bacen/olinda/). As series SGS 13521/13522 eram realizados.
)

GRUPOS: tuple[str, ...] = ("inflacao", "juros", "cambio", "credito")


def series_do_grupo(grupo: str) -> tuple[Serie, ...]:
    """Series pertencentes a um grupo. Levanta se o grupo for desconhecido."""
    if grupo not in GRUPOS:
        raise ValueError(f"Grupo desconhecido: {grupo!r}. Validos: {GRUPOS}")
    return tuple(s for s in SERIES if s.grupo == grupo)
