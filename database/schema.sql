-- Script SQL para criação das tabelas

-- Tabela para armazenar os municípios
CREATE TABLE IF NOT EXISTS municipio (
    codmunicipio SERIAL PRIMARY KEY,
    nome VARCHAR(255) UNIQUE NOT NULL
);

-- Tabela para armazenar os tipos de administração (PM, CM, SAAE, etc.)
CREATE TABLE IF NOT EXISTS adm (
    codadm SERIAL PRIMARY KEY,
    nome VARCHAR(255) UNIQUE NOT NULL
);

-- Tabela para armazenar as credenciais, ligando um município a uma administração
CREATE TABLE IF NOT EXISTS credenciais (
    codcredencial SERIAL PRIMARY KEY,
    codmunicipio INTEGER NOT NULL REFERENCES municipio(codmunicipio) ON DELETE CASCADE,
    codadm INTEGER NOT NULL REFERENCES adm(codadm) ON DELETE CASCADE,
    usuario VARCHAR(255),
    senha VARCHAR(255),
    loginatualizado INT NOT NULL, 
    UNIQUE (codmunicipio, codadm)
);

-- Adiciona índices para otimizar as buscas por nome
CREATE INDEX IF NOT EXISTS idx_municipio_nome ON municipio (nome);
CREATE INDEX IF NOT EXISTS idx_adm_nome ON adm (nome);
