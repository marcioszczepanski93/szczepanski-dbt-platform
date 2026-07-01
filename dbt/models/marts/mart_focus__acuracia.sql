-- Acuracia historica das projecoes Focus: desvio medio (absoluto e percentual) por
-- indicador por ano. Permite avaliar o quanto o mercado erra as expectativas.
select
    extract(year from data_referencia)::int as ano,
    indicador,
    count(*)                                as meses_avaliados,
    round(avg(abs(desvio_abs)), 2)          as desvio_abs_medio,
    round(avg(abs(desvio_pct)), 2)          as desvio_pct_medio
from {{ ref('int_focus__vs_realizado') }}
where realizado is not null
group by 1, 2
order by 1, 2
