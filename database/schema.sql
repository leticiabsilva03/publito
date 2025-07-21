-- Script SQL para criação das tabelas

-- Tabela para armazenar os municípios
CREATE TABLE IF NOT EXISTS sicom.municipios (
    cod_municipio SERIAL PRIMARY KEY,
    nom_municipio VARCHAR(255) UNIQUE NOT NULL,
    cnpj_municipio VARCHAR(14) UNIQUE NOT NULL
);


-- Tabela para armazenar os tipos de administração (PM, CM, SAAE, etc.)
CREATE TABLE IF NOT EXISTS sicom.administracoes (
    cod_administracao SERIAL PRIMARY KEY,
    sigla_administracao VARCHAR(10) UNIQUE NOT NULL,
    des_administracao TEXT
);

CREATE TABLE IF NOT EXISTS sicom.municipios_administracoes (
    cod_entidade SERIAL PRIMARY KEY,
    cod_municipio INTEGER NOT NULL,
    cod_administracao INTEGER NOT NULL,
    CONSTRAINT fk_municipio
        FOREIGN KEY(cod_municipio)
        REFERENCES sicom.municipios(cod_municipio)
        ON DELETE CASCADE,
    CONSTRAINT fk_administracao
        FOREIGN KEY(cod_administracao)
        REFERENCES sicom.administracoes(cod_administracao)
        ON DELETE RESTRICT,
    CONSTRAINT uq_municipio_adm UNIQUE (cod_municipio, cod_administracao)
);

-- Tabela para armazenar as credenciais, ligando um município a uma administração
CREATE TABLE IF NOT EXISTS sicom.credenciais (
    cod_credencial SERIAL PRIMARY KEY,
    cod_entidade INTEGER NOT NULL,
    cpf_usuario VARCHAR(11),
    senha VARCHAR(255),
    data_atualizacao date NOT NULL,
    status_validade boolean NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_entidade
        FOREIGN KEY(cod_entidade)
        REFERENCES sicom.municipios_administracoes(cod_entidade)
        ON DELETE CASCADE
);

-- Adiciona constraints de formato para garantir a integridade dos dados
ALTER TABLE sicom.municipios
ADD CONSTRAINT check_cnpj_format CHECK (cnpj_municipio ~ '^\d{14}$');

ALTER TABLE sicom.credenciais
ADD CONSTRAINT check_cpf_usuario_format CHECK (cpf_usuario ~ '^\d{11}$');

-- Adiciona índices para otimizar as buscas por nome
CREATE INDEX IF NOT EXISTS idx_municipio_nome ON sicom.municipios (nom_municipio);
CREATE INDEX IF NOT EXISTS idx_adm_sigla ON sicom.administracoes (sigla_administracao);
CREATE INDEX IF NOT EXISTS idx_adm_descricao ON sicom.administracoes (des_administracao);


CREATE TABLE sicom.comunicados (
    id SERIAL PRIMARY KEY,
    url VARCHAR(255) NOT NULL UNIQUE,
    titulo_comunicado VARCHAR(255),
    data_postagem VARCHAR(15),
    data_postagem_discord TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);