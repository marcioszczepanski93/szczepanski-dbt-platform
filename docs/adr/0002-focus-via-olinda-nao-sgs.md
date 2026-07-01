# 0002 — Expectativas Focus vem da API Olinda, nao do SGS

Status: aceito
Data: 2026-07-01

## Contexto

A especificacao inicial mapeou as expectativas do Focus para as series SGS 13521
(SELIC) e 13522 (IPCA), consumidas pelo mesmo endpoint `dados/serie` das demais
series. Ao construir o mart de acuracia do Focus, o desvio entre "expectativa" e
"realizado" deu exatamente 0.00 em todos os meses.

A investigacao mostrou que a serie 13522 NAO e uma expectativa: ela reproduz
exatamente o IPCA acumulado em 12 meses (realizado), que o proprio pipeline ja
calcula a partir da serie 433. Ou seja, comparavamos um numero com ele mesmo. As
expectativas de mercado (Focus) sao publicadas por outra API do BCB — a Olinda
"Expectativas de Mercado" (OData) — com endpoint, formato e granularidade proprios,
distinta do SGS.

## Decisao

Ingerir o Focus da API Olinda, nao do SGS.

- Novo cliente `src/bacen/olinda/client.py` consumindo
  `ExpectativasMercadoInflacao12Meses` (expectativa de IPCA para os proximos 12
  meses), filtrando `Suavizada eq 'N'` e `baseCalculo eq 0` (base canonica; sem esse
  filtro a API retorna duas linhas por data). Paginacao via `$skip`.
- Nova tabela `raw.focus_expectativas` (migration 002), com formato proprio
  (indicador, horizonte, data_expectativa, mediana, ...), separada das tabelas SGS.
- As series SGS 13521/13522 foram removidas do catalogo; a tabela `raw.bacen_focus`
  foi descartada.
- O modelo de acuracia passou a alinhar o HORIZONTE corretamente: expectativa feita
  no mes M versus IPCA realizado acumulado nos 12 meses seguintes (forward), com
  `ipca_acum_12m_fwd` em `int_indicadores__alinhados`. Meses de horizonte ainda aberto
  ficam sem realizado e nao entram na acuracia.

## Consequencias

Positivas:
- A acuracia do Focus passou a refletir a realidade (ex.: erro grande em 2020-2021,
  quando o mercado subestimou a inflacao pos-pandemia; erro pequeno em periodos calmos).
- O pipeline passa a ter duas fontes reais e distintas (SGS + Olinda), o que e mais
  proximo de um cenario de producao e reforca a narrativa do projeto.

Negativas / trade-offs:
- Uma segunda integracao HTTP para manter (formato OData, diferente do SGS). Ha alguma
  duplicacao de logica de retry entre os dois clients — candidata a extracao futura
  para um helper compartilhado quando um terceiro consumidor aparecer.
- A analise ficou restrita ao IPCA 12m (a mais canonica). Expectativas de SELIC (via
  `ExpectativasMercadoAnuais`) ficam como evolucao, por exigirem alinhamento por ano
  de referencia.

## Licao

O sintoma "metrica boa demais" (desvio exatamente zero) foi o que revelou o erro de
fonte. Vale desconfiar de resultado perfeito antes de comemorar.
