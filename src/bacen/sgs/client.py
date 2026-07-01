"""Client HTTP da API SGS do BACEN.

Mesmo padrao do client SGS da szczepanski-data-platform (src/qdp/bcb): httpx +
retry com backoff exponencial, excecao especifica em falha persistente,
dependencia (httpx.Client) injetada via construtor para permitir mock nos testes.

A API SGS limita series diarias a ~10 anos por requisicao; por isso a janela de
busca e fatiada em pedacos de no maximo _MAX_WINDOW_DAYS dias.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from include.observability import get_logger

log = get_logger("bacen.sgs.client")

_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 2  # espera 2, 4, 8s entre tentativas
_TIMEOUT_SECONDS = 30
_MAX_WINDOW_DAYS = 3650  # limite pratico da API SGS para series diarias (~10 anos)


class BacenAPIError(Exception):
    """Falha persistente ao consultar a API SGS (apos esgotar os retries)."""


@dataclass(frozen=True)
class SerieRecord:
    codigo_sgs: int
    indicador: str
    data: str  # ISO date (YYYY-MM-DD)
    valor: float | None


def _janelas(
    inicio: date, fim: date, max_dias: int = _MAX_WINDOW_DAYS
) -> Iterator[tuple[date, date]]:
    """Fatia o intervalo [inicio, fim] em janelas de no maximo max_dias dias."""
    atual = inicio
    while atual <= fim:
        prox = min(atual + timedelta(days=max_dias), fim)
        yield atual, prox
        atual = prox + timedelta(days=1)


def _parse(codigo: int, indicador: str, payload: list[dict[str, Any]]) -> list[SerieRecord]:
    """Converte o JSON da SGS ({data: DD/MM/YYYY, valor: str}) em SerieRecord."""
    registros: list[SerieRecord] = []
    for item in payload:
        data_iso = datetime.strptime(item["data"], "%d/%m/%Y").date().isoformat()
        valor_raw = item.get("valor")
        valor = None if valor_raw is None or valor_raw == "" else float(valor_raw)
        registros.append(SerieRecord(codigo, indicador, data_iso, valor))
    return registros


class BacenSGSClient:
    def __init__(self, client: httpx.Client | None = None) -> None:
        # Dependencia injetada (SOLID + testabilidade): nos testes passamos um
        # httpx.Client com transport mockado, sem rede.
        self._client = client or httpx.Client(timeout=_TIMEOUT_SECONDS)

    def fetch_serie(
        self, codigo: int, indicador: str, data_inicial: date, data_final: date
    ) -> list[SerieRecord]:
        """Busca todos os pontos da serie no intervalo, fatiando em janelas."""
        registros: list[SerieRecord] = []
        for ini, fim in _janelas(data_inicial, data_final):
            registros.extend(_parse(codigo, indicador, self._get(codigo, ini, fim)))
        return registros

    def _get(self, codigo: int, inicio: date, fim: date) -> list[dict[str, Any]]:
        url = _BASE_URL.format(codigo=codigo)
        params = {
            "formato": "json",
            "dataInicial": inicio.strftime("%d/%m/%Y"),
            "dataFinal": fim.strftime("%d/%m/%Y"),
        }
        last_exc: Exception | None = None
        for tentativa in range(1, _MAX_RETRIES + 1):
            try:
                resp = self._client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, ValueError) as exc:  # ValueError cobre JSON invalido
                last_exc = exc
                espera = _BACKOFF_BASE_SECONDS**tentativa
                ctx = {"codigo": codigo, "tentativa": tentativa, "espera_s": espera}
                log.warning("Falha ao consultar SGS; novo retry.", extra={"context": ctx})
                if tentativa < _MAX_RETRIES:
                    time.sleep(espera)
        raise BacenAPIError(f"SGS {codigo}: falha apos {_MAX_RETRIES} tentativas") from last_exc
