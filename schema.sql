-- Execute conectado ao banco de dados que será usado pela aplicação.
-- Se o banco ainda não existir, crie-o separadamente:
-- CREATE DATABASE coleta_produtos;

BEGIN;

CREATE TABLE IF NOT EXISTS dados (
    codigo_interno VARCHAR(80) PRIMARY KEY,
    descricao TEXT NOT NULL,
    validade_atual DATE,
    fabricacao_atual DATE,
    validade_coletada DATE,
    fabricacao_coletada DATE
);

CREATE TABLE IF NOT EXISTS gtins (
    codigo_interno VARCHAR(80) NOT NULL,
    codigo_barras VARCHAR(80) NOT NULL,
    CONSTRAINT fk_gtins_dados
        FOREIGN KEY (codigo_interno)
        REFERENCES dados (codigo_interno)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gtins_codigo_barras
    ON gtins (codigo_barras);

CREATE INDEX IF NOT EXISTS idx_dados_pendentes
    ON dados (codigo_interno)
    WHERE validade_coletada IS NULL
      AND fabricacao_coletada IS NULL;

COMMIT;
