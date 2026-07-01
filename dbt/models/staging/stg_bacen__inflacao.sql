-- Staging de inflacao: limpa e tipa raw.bacen_inflacao (ipca, ipca15, igpm).
-- Ja chega em formato longo (um indicador por linha); aqui so renomeamos, tipamos
-- e removemos pontos sem valor. Sem logica de negocio (fica no intermediate).
with fonte as (
    select * from {{ source('bacen', 'bacen_inflacao') }}
)
select
    codigo_sgs,
    indicador,
    data::date          as data_referencia,
    valor::numeric      as valor
from fonte
where valor is not null
