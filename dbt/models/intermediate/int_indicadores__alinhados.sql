-- Alinha todos os indicadores (exceto Focus) para granularidade MENSAL, uma linha
-- por mes com cada indicador numa coluna (formato largo). E o coracao da modelagem
-- de series temporais: series de frequencias diferentes so podem ser comparadas apos
-- uma regra explicita de agregacao.
--
-- Regra por frequencia:
--   diarias (cambio, selic diaria) -> media do mes (valor_medio)
--   por reuniao (Meta SELIC)        -> ultimo valor do mes (valor_ultimo)
--   mensais (inflacao, credito)     -> o unico valor do mes (media = ultimo)
--
-- Janela: ultimos 10 anos.
with unificado as (
    select data_referencia, indicador, valor from {{ ref('stg_bacen__inflacao') }}
    union all
    select data_referencia, indicador, valor from {{ ref('stg_bacen__juros') }}
    union all
    select data_referencia, indicador, valor from {{ ref('stg_bacen__cambio') }}
    union all
    select data_referencia, indicador, valor from {{ ref('stg_bacen__credito') }}
),

mensal as (
    select
        date_trunc('month', data_referencia)::date          as mes,
        indicador,
        avg(valor)                                          as valor_medio,
        (array_agg(valor order by data_referencia desc))[1] as valor_ultimo
    from unificado
    group by 1, 2
),

pivotado as (
    select
        mes                                                            as data_referencia,
        max(valor_medio)  filter (where indicador = 'ipca')            as ipca,
        max(valor_medio)  filter (where indicador = 'ipca15')          as ipca15,
        max(valor_medio)  filter (where indicador = 'igpm')            as igpm,
        max(valor_ultimo) filter (where indicador = 'meta_selic')      as meta_selic,
        max(valor_medio)  filter (where indicador = 'selic_diaria')    as selic_diaria,
        max(valor_medio)  filter (where indicador = 'usd_brl')         as usd_brl,
        max(valor_medio)  filter (where indicador = 'eur_brl')         as eur_brl,
        max(valor_ultimo) filter (where indicador = 'inadimplencia_pf') as inadimplencia_pf,
        max(valor_ultimo) filter (where indicador = 'spread_medio')    as spread_medio
    from mensal
    group by 1
),

com_acumulado as (
    -- IPCA acumulado em 12 meses, via composicao: 100 * (prod(1 + ipca/100) - 1),
    -- calculado com exp(sum(ln(...))). Nulo quando nao ha 12 meses completos na janela.
    --   trailing (ate o mes M): o "IPCA 12m" manchete, exibido no painel.
    --   forward (os 12 meses apos M): o realizado que se confronta com a expectativa
    --     Focus feita em M (que e para os proximos 12 meses). Fica nulo nos meses mais
    --     recentes cujo horizonte ainda nao fechou — nao da para pontuar horizonte aberto.
    select
        pivotado.*,
        case
            when count(ipca) over w_trailing = 12
            then round((100 * (exp(sum(ln(1 + ipca / 100)) over w_trailing) - 1))::numeric, 2)
        end as ipca_acum_12m,
        case
            when count(ipca) over w_forward = 12
            then round((100 * (exp(sum(ln(1 + ipca / 100)) over w_forward) - 1))::numeric, 2)
        end as ipca_acum_12m_fwd
    from pivotado
    window
        w_trailing as (order by data_referencia rows between 11 preceding and current row),
        w_forward as (order by data_referencia rows between 1 following and 12 following)
)

select
    data_referencia,
    ipca,
    ipca15,
    igpm,
    ipca_acum_12m,
    ipca_acum_12m_fwd,
    meta_selic,
    selic_diaria,
    -- SELIC diaria (% a.d.) tornada comparavel a Meta SELIC (% a.a.) via composicao.
    {{ anualizar_taxa_diaria('selic_diaria') }} as selic_efetiva_aa,
    usd_brl,
    eur_brl,
    inadimplencia_pf,
    spread_medio
from com_acumulado
where data_referencia >= (current_date - interval '10 years')
order by data_referencia
