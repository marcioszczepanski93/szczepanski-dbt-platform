-- Staging da expectativa Focus de IPCA para os proximos 12 meses (API Olinda).
-- Uma coleta por data util; a mediana e a estatistica de referencia do mercado.
with fonte as (
    select * from {{ source('bacen', 'focus_expectativas') }}
)
select
    indicador,
    horizonte,
    data_expectativa::date  as data_coleta,
    mediana::numeric        as expectativa
from fonte
where indicador = 'ipca'
  and horizonte = '12m'
  and mediana is not null
