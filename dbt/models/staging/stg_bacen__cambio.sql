-- Staging de cambio: raw.bacen_cambio com USD/BRL (serie 1) e EUR/BRL (serie 21619),
-- ambas diarias, ja em formato longo (uma linha por moeda por data).
with fonte as (
    select * from {{ source('bacen', 'bacen_cambio') }}
)
select
    codigo_sgs,
    indicador,
    data::date          as data_referencia,
    valor::numeric      as valor
from fonte
where valor is not null
