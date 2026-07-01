-- Staging de juros: raw.bacen_juros contem SELIC diaria (serie 11, % a.d.) e
-- Meta SELIC (serie 432, % a.a.), ja distinguidas pela coluna indicador. Mantemos
-- ambas em formato longo; a conversao de frequencia (diaria -> anualizada) acontece
-- no intermediate, onde a granularidade e alinhada.
with fonte as (
    select * from {{ source('bacen', 'bacen_juros') }}
)
select
    codigo_sgs,
    indicador,
    data::date          as data_referencia,
    valor::numeric      as valor
from fonte
where valor is not null
