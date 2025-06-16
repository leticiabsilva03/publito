WITH
-- 1. Dados de entrada (sem alteração)
cleaned_data AS (
    SELECT
        nom_m,
        regexp_replace(cnpj_m, '[^0-9]', '', 'g') AS cnpj_m_cleaned,
        sigla_a,
        des_a,
        regexp_replace(cpf_u, '[^0-9]', '', 'g') AS cpf_u_cleaned,
        senha_u,
        to_date(data_att_str, 'DD/MM/YYYY') AS data_att_cleaned,
        status_v_str::BOOLEAN AS status_v_cleaned
    FROM (
        VALUES
            ('Araxa',      '18.140.756/0001-00', 'PM',   'Prefeitura Municipal',      '002.725.196-93', 'NASX6369ASJ89A2027', '13/06/2025', 'True'),
            ('Araxa',      '18.140.756/0001-00', 'CM',   'Câmara Municipal',          '002.323.196-93', 'NAT5X63920219UJ7',  '13/06/2025', 'True'),
            ('Araxa',      '18.140.756/0001-00', 'Prev', 'Instituto de Previdência',  '002.742.196-93', 'NASA87SYHA92027',   '13/06/2025', 'True'),
            ('Araxa',      '18.140.756/0001-00', 'DMAE', 'Departamento de Água e Esgoto','002.523.196-93', 'NASA87SYHA027',     '13/06/2025', 'True'),
            ('Centralina', '18.445.756/0001-00', 'PM',   'Prefeitura Municipal',      '002.725.985-93', 'NASAUNSHA2027',     '13/06/2025', 'False'),
            ('Centralina', '18.445.756/0001-00', 'CM',   'Câmara Municipal',          '002.095.985-93', 'NASS8SD8D7',        '13/06/2025', 'True')
    ) AS t (nom_m, cnpj_m, sigla_a, des_a, cpf_u, senha_u, data_att_str, status_v_str)
),
-- 2. Inserir municípios e RETORNAR os IDs (existentes ou novos)
ins_municipios AS (
    INSERT INTO sicom.municipios (nom_municipio, cnpj_municipio)
    SELECT DISTINCT nom_m, cnpj_m_cleaned FROM cleaned_data
    ON CONFLICT (nom_municipio) DO UPDATE SET cnpj_municipio = EXCLUDED.cnpj_municipio -- Ação dummy para garantir que RETURNING sempre funcione
    RETURNING cod_municipio, nom_municipio
),
-- 3. Inserir administrações e RETORNAR os IDs (existentes ou novos)
ins_admins AS (
    INSERT INTO sicom.administracoes (sigla_administracao, des_administracao)
    SELECT DISTINCT sigla_a, des_a FROM cleaned_data
    ON CONFLICT (sigla_administracao) DO UPDATE SET des_administracao = EXCLUDED.des_administracao
    RETURNING cod_administracao, sigla_administracao
),
-- 4. Inserir os vínculos, usando os IDs RETORNADOS pelos CTEs anteriores
ins_entidades AS (
    INSERT INTO sicom.municipios_administracoes (cod_municipio, cod_administracao)
    SELECT DISTINCT im.cod_municipio, ia.cod_administracao
    FROM cleaned_data cd
    JOIN ins_municipios im ON cd.nom_m = im.nom_municipio
    JOIN ins_admins ia ON cd.sigla_a = ia.sigla_administracao
    ON CONFLICT (cod_municipio, cod_administracao) DO UPDATE SET cod_municipio = EXCLUDED.cod_municipio
    RETURNING cod_entidade, cod_municipio, cod_administracao
)
-- 5. Inserir as credenciais, utilizando os dados limpos e os IDs dos vínculos.
INSERT INTO sicom.credenciais (cod_entidade, cpf_usuario, senha, data_atualizacao, status_validade)
SELECT
    ie.cod_entidade,
    cd.cpf_u_cleaned,
    cd.senha_u,
    cd.data_att_cleaned,
    cd.status_v_cleaned
FROM cleaned_data cd
JOIN ins_municipios im ON cd.nom_m = im.nom_municipio
JOIN ins_admins ia ON cd.sigla_a = ia.sigla_administracao
JOIN ins_entidades ie ON ie.cod_municipio = im.cod_municipio AND ie.cod_administracao = ia.cod_administracao;