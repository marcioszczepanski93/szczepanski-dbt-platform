-- Staging de credito: raw.bacen_credito com inadimplencia PF (serie 21082) e
-- spread medio geral (serie 20783), ambas mensais, em formato longo.
with fonte as (
    select * from {{ source('bacen', 'bacen_credito') }}
)
select
    codigo_sgs,
    indicador,
    data::date          as data_referencia,
    valor::numeric      as valor
from fonte
where valor is not null
