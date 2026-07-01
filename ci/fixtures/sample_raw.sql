-- Amostra sintetica para o CI: popula o schema raw o suficiente para o `dbt build`
-- materializar todos os models e os testes passarem, sem depender das APIs externas.
-- Aplicado apos migrations/001 e migrations/002.

-- Inflacao: 18 meses de cada indicador (garante IPCA acumulado 12m nao nulo).
insert into raw.bacen_inflacao (codigo_sgs, indicador, data, valor)
select 433, 'ipca', d::date, 0.50 from generate_series('2023-01-01', '2024-06-01', interval '1 month') d
union all
select 7478, 'ipca15', d::date, 0.45 from generate_series('2023-01-01', '2024-06-01', interval '1 month') d
union all
select 189, 'igpm', d::date, 0.30 from generate_series('2023-01-01', '2024-06-01', interval '1 month') d;

-- Juros: Meta SELIC mensal + SELIC diaria (amostra).
insert into raw.bacen_juros (codigo_sgs, indicador, data, valor)
select 432, 'meta_selic', d::date, 10.75 from generate_series('2023-01-01', '2024-06-01', interval '1 month') d
union all
select 11, 'selic_diaria', d::date, 0.04 from generate_series('2023-01-01', '2024-06-01', interval '5 day') d;

-- Cambio: USD e EUR (amostra diaria).
insert into raw.bacen_cambio (codigo_sgs, indicador, data, valor)
select 1, 'usd_brl', d::date, 5.00 from generate_series('2023-01-01', '2024-06-01', interval '5 day') d
union all
select 21619, 'eur_brl', d::date, 5.50 from generate_series('2023-01-01', '2024-06-01', interval '5 day') d;

-- Credito: inadimplencia e spread (mensal).
insert into raw.bacen_credito (codigo_sgs, indicador, data, valor)
select 21082, 'inadimplencia_pf', d::date, 3.20 from generate_series('2023-01-01', '2024-06-01', interval '1 month') d
union all
select 20783, 'spread_medio', d::date, 20.00 from generate_series('2023-01-01', '2024-06-01', interval '1 month') d;

-- Focus (Olinda): expectativa de IPCA 12m (uma por mes na amostra).
insert into raw.focus_expectativas (indicador, horizonte, data_expectativa, mediana, media, n_respondentes)
select 'ipca', '12m', d::date, 4.50, 4.52, 50 from generate_series('2023-01-05', '2024-06-05', interval '1 month') d;
