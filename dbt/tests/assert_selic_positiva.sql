-- Teste singular: a Meta SELIC nunca deve ser negativa. Retorna as linhas que
-- violam a regra; zero linhas = teste passa.
select
    data_referencia,
    meta_selic
from {{ ref('mart_macro__painel') }}
where meta_selic < 0
