-- Schema raw: dados brutos da API SGS, sem transformacao. Fonte dos modelos dbt staging.
-- Executado automaticamente no primeiro boot do postgres-warehouse
-- (montado em /docker-entrypoint-initdb.d).
--
-- A constraint UNIQUE (codigo_sgs, data) e o que torna a ingestao idempotente:
-- INSERT ... ON CONFLICT DO NOTHING. Uma tabela por grupo de series.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.bacen_inflacao (
    id          SERIAL PRIMARY KEY,
    codigo_sgs  INTEGER NOT NULL,
    indicador   VARCHAR(50) NOT NULL,
    data        DATE NOT NULL,
    valor       NUMERIC(12, 4),
    ingested_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo_sgs, data)
);

CREATE TABLE IF NOT EXISTS raw.bacen_juros (
    id          SERIAL PRIMARY KEY,
    codigo_sgs  INTEGER NOT NULL,
    indicador   VARCHAR(50) NOT NULL,
    data        DATE NOT NULL,
    valor       NUMERIC(12, 4),
    ingested_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo_sgs, data)
);

CREATE TABLE IF NOT EXISTS raw.bacen_cambio (
    id          SERIAL PRIMARY KEY,
    codigo_sgs  INTEGER NOT NULL,
    indicador   VARCHAR(50) NOT NULL,
    data        DATE NOT NULL,
    valor       NUMERIC(12, 4),
    ingested_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo_sgs, data)
);

CREATE TABLE IF NOT EXISTS raw.bacen_credito (
    id          SERIAL PRIMARY KEY,
    codigo_sgs  INTEGER NOT NULL,
    indicador   VARCHAR(50) NOT NULL,
    data        DATE NOT NULL,
    valor       NUMERIC(12, 4),
    ingested_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo_sgs, data)
);

CREATE TABLE IF NOT EXISTS raw.bacen_focus (
    id          SERIAL PRIMARY KEY,
    codigo_sgs  INTEGER NOT NULL,
    indicador   VARCHAR(50) NOT NULL,
    data        DATE NOT NULL,
    valor       NUMERIC(12, 4),
    ingested_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo_sgs, data)
);
