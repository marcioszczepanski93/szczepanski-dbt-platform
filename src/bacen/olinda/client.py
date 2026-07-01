"""Client da API Olinda "Expectativas de Mercado" (Focus) do BCB.

Fonte correta das expectativas do mercado (diferente do SGS). Endpoint OData; aqui
consumimos ExpectativasMercadoInflacao12Meses (expectativa de IPCA para os proximos
12 meses, uma coleta por dia util). Paginacao via $skip.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from include.observability import get_logger

log = get_logger("bacen.olinda.client")

_BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"
_PAGE_SIZE = 1000
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 2
_TIMEOUT_SECONDS = 30


class OlindaAPIError(Exception):
    """Falha persistente ao consultar a API Olinda (apos esgotar os retries)."""


@dataclass(frozen=True)
class ExpectativaRecord:
    indicador: str
    horizonte: str
    data_expectativa: str  # ISO date
    mediana: float | None
    media: float | None
    n_respondentes: int | None


class OlindaExpectativasClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=_TIMEOUT_SECONDS)

    def fetch_ipca_12m(self, data_inicial: date) -> list[ExpectativaRecord]:
        """Expectativa de IPCA acumulado nos proximos 12 meses (nao suavizada).

        baseCalculo eq 0 = base canonica (ultimos 30 dias). Sem esse filtro, a API
        retorna tambem baseCalculo 1 (outra janela), duplicando as linhas por data.
        """
        filtro = (
            "Indicador eq 'IPCA' and Suavizada eq 'N' and baseCalculo eq 0 "
            f"and Data ge '{data_inicial.isoformat()}'"
        )
        registros: list[ExpectativaRecord] = []
        for item in self._fetch("ExpectativasMercadoInflacao12Meses", filtro):
            registros.append(
                ExpectativaRecord(
                    indicador="ipca",
                    horizonte="12m",
                    data_expectativa=item["Data"],
                    mediana=item.get("Mediana"),
                    media=item.get("Media"),
                    n_respondentes=item.get("numeroRespondentes"),
                )
            )
        return registros

    def _fetch(self, recurso: str, filtro: str) -> list[dict[str, Any]]:
        resultados: list[dict[str, Any]] = []
        skip = 0
        while True:
            pagina = self._get(
                recurso,
                {
                    "$format": "json",
                    "$filter": filtro,
                    "$orderby": "Data",
                    "$top": _PAGE_SIZE,
                    "$skip": skip,
                },
            )
            resultados.extend(pagina)
            if len(pagina) < _PAGE_SIZE:
                break
            skip += _PAGE_SIZE
        return resultados

    def _get(self, recurso: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"{_BASE_URL}/{recurso}"
        last_exc: Exception | None = None
        for tentativa in range(1, _MAX_RETRIES + 1):
            try:
                resp = self._client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()["value"]
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last_exc = exc
                espera = _BACKOFF_BASE_SECONDS**tentativa
                ctx = {"recurso": recurso, "tentativa": tentativa, "espera_s": espera}
                log.warning("Falha ao consultar Olinda; novo retry.", extra={"context": ctx})
                if tentativa < _MAX_RETRIES:
                    time.sleep(espera)
        msg = f"Olinda {recurso}: falha apos {_MAX_RETRIES} tentativas"
        raise OlindaAPIError(msg) from last_exc
