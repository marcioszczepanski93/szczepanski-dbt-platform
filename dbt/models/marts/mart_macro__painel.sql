-- Painel macroeconomico: indicadores mensais + variacoes MoM e YoY. Tabela central
-- consumida pelo Metabase.
--
-- Materializacao incremental por data_referencia. Cuidado (pitfall classico):
-- MoM/YoY usam lag(), que precisa das linhas anteriores. Num incremental ingenuo
-- (so linhas novas) o lag nao enxergaria o historico. Por isso, no modo incremental,
-- reprocessamos uma JANELA de lookback de 13 meses: garante contexto para lag(12) e
-- o unique_key sobrescreve as linhas recalculadas. Com volume pequeno o custo e trivial.
{{
    config(
        materialized="incremental",
        unique_key="data_referencia",
    )
}}

with base as (
    select * from {{ ref('int_indicadores__alinhados') }}

    {% if is_incremental() %}
    where data_referencia > (select max(data_referencia) from {{ this }}) - interval '13 months'
    {% endif %}
)

select
    data_referencia,
    ipca,
    ipca15,
    igpm,
    ipca_acum_12m,
    meta_selic,
    selic_efetiva_aa,
    usd_brl,
    eur_brl,
    inadimplencia_pf,
    spread_medio,
    {{ variacao_percentual('ipca', 'data_referencia', 1) }}     as ipca_mom,
    {{ variacao_percentual('ipca', 'data_referencia', 12) }}    as ipca_yoy,
    {{ variacao_percentual('usd_brl', 'data_referencia', 1) }}  as usd_brl_mom,
    {{ variacao_percentual('usd_brl', 'data_referencia', 12) }} as usd_brl_yoy,
    {{ variacao_percentual('meta_selic', 'data_referencia', 12) }} as meta_selic_yoy
from base
order by data_referencia
