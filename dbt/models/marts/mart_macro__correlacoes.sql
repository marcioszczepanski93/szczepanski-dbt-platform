-- Medias moveis de 3, 6 e 12 meses dos principais indicadores (SELIC, IPCA, cambio).
-- Suaviza a serie e da base para leitura de tendencia no dashboard.
select
    data_referencia,
    round(avg(meta_selic) over w3, 2)  as meta_selic_ma3,
    round(avg(meta_selic) over w6, 2)  as meta_selic_ma6,
    round(avg(meta_selic) over w12, 2) as meta_selic_ma12,
    round(avg(ipca) over w3, 2)        as ipca_ma3,
    round(avg(ipca) over w6, 2)        as ipca_ma6,
    round(avg(ipca) over w12, 2)       as ipca_ma12,
    round(avg(usd_brl) over w3, 4)     as usd_brl_ma3,
    round(avg(usd_brl) over w6, 4)     as usd_brl_ma6,
    round(avg(usd_brl) over w12, 4)    as usd_brl_ma12
from {{ ref('int_indicadores__alinhados') }}
window
    w3 as (order by data_referencia rows between 2 preceding and current row),
    w6 as (order by data_referencia rows between 5 preceding and current row),
    w12 as (order by data_referencia rows between 11 preceding and current row)
order by data_referencia
