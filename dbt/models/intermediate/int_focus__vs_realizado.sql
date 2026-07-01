-- Acuracia do Focus: confronta a expectativa de IPCA para os proximos 12 meses (feita
-- no mes M) com o IPCA que de fato se realizou nesses 12 meses (forward). E a metrica
-- canonica de acuracia do Focus, com alinhamento de HORIZONTE correto.
--
-- expectativa(M) -> mediana da ultima coleta Focus do mes M
-- realizado(M)   -> IPCA acumulado nos 12 meses apos M (nulo enquanto o horizonte
--                   nao fecha; por isso os meses mais recentes nao entram)
with expectativa_mensal as (
    select
        date_trunc('month', data_coleta)::date              as mes,
        (array_agg(expectativa order by data_coleta desc))[1] as expectativa
    from {{ ref('stg_focus__ipca_12m') }}
    group by 1
),

realizado as (
    select data_referencia as mes, ipca_acum_12m_fwd as realizado
    from {{ ref('int_indicadores__alinhados') }}
)

select
    e.mes                                                                        as data_referencia,
    'ipca_12m'                                                                   as indicador,
    e.expectativa,
    r.realizado,
    round((r.realizado - e.expectativa)::numeric, 2)                             as desvio_abs,
    round(((r.realizado - e.expectativa) / nullif(e.expectativa, 0) * 100)::numeric, 2) as desvio_pct
from expectativa_mensal e
left join realizado r on r.mes = e.mes
order by data_referencia
