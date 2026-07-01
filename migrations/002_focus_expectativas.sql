-- Focus de verdade: expectativas de mercado vem da API Olinda "Expectativas de
-- Mercado" do BCB, NAO do endpoint SGS. As series SGS 13521/13522 mapeadas antes
-- eram realizados (a 13522 e o proprio IPCA acumulado 12m), nao expectativas.
--
-- Esta migration remove a tabela SGS de focus e cria a tabela de expectativas.

DROP TABLE IF EXISTS raw.bacen_focus;

CREATE TABLE IF NOT EXISTS raw.focus_expectativas (
    id               SERIAL PRIMARY KEY,
    indicador        VARCHAR(50) NOT NULL,   -- 'ipca'
    horizonte        VARCHAR(20) NOT NULL,   -- '12m' (proximos 12 meses)
    data_expectativa DATE NOT NULL,          -- data da coleta Focus
    mediana          NUMERIC(12, 4),
    media            NUMERIC(12, 4),
    n_respondentes   INTEGER,
    ingested_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (indicador, horizonte, data_expectativa)
);
