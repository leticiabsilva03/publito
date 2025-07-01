# tests/test_integration/test_db_queries.py
import pytest
import pytest_asyncio
import os
from datetime import date
from sqlalchemy import insert, select

# Importa a instância de conexão e todas as funções e modelos necessários
from database.db_manager import database
from database.queries import (
    insert_municipio, fetch_municipio_autocomplete,
    busca_entidade_id, create_municipio_administracao_link,
    check_credencial, insert_credencial, update_credenciais,
    fetch_credenciais_por_id # Adicionada para o novo teste
)
from database.models import municipios, administracoes, municipios_administracoes, credenciais

# --- Fixture de Conexão e Limpeza ---
@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_connection():
    """
    Fixture que estabelece a conexão com o banco de TESTES para cada teste.
    Limpa todas as tabelas na ordem correta antes de cada execução para garantir isolamento.
    """
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.fail("A variável de ambiente TEST_DATABASE_URL não está configurada.")

    database._url = test_db_url
    await database.connect()

    # Limpa as tabelas na ordem inversa das dependências para evitar erros de chave estrangeira
    await database.execute(credenciais.delete())
    await database.execute(municipios_administracoes.delete())
    await database.execute(administracoes.delete())
    await database.execute(municipios.delete())

    yield # Permite que o teste seja executado

    await database.disconnect()

# --- Fixture de Dados de Teste ---
@pytest_asyncio.fixture(scope="function")
async def setup_data():
    """
    Fixture que insere dados básicos (um município e uma administração)
    para serem usados pelos testes de credenciais.
    """
    # Insere um município
    mun_query = insert(municipios).values(nom_municipio="Cidade Teste", cnpj_municipio="11111111111111")
    cod_municipio = await database.execute(mun_query)

    # Insere uma administração
    adm_query = insert(administracoes).values(sigla_administracao="PM", des_administracao="Prefeitura Municipal")
    cod_administracao = await database.execute(adm_query)

    return {"cod_municipio": cod_municipio, "cod_administracao": cod_administracao}

# --- Testes para Municípios (Seus testes existentes, mantidos) ---
@pytest.mark.asyncio
async def test_inserir_municipio_com_sucesso():
    """Verifica se um município é inserido corretamente."""
    nome, cnpj = "Teste Sucesso", "12345678901234"
    resultado = await insert_municipio(nome, cnpj)
    assert resultado["success"] is True

    fetch_res = await fetch_municipio_autocomplete(nome)
    assert len(fetch_res) == 1
    assert fetch_res[0]["nom_municipio"] == nome

@pytest.mark.asyncio
async def test_inserir_municipio_duplicado_falha():
    """Verifica se a inserção de um município duplicado falha graciosamente."""
    nome, cnpj = "Cidade Duplicada", "98765432109876"
    await insert_municipio(nome, cnpj)
    resultado = await insert_municipio(nome, "00000000000000")
    assert resultado["success"] is False
    assert "já existe" in resultado["message"]

# --- Novos Testes para o Fluxo Completo ---

@pytest.mark.asyncio
async def test_criar_vinculo_entidade(setup_data):
    """Verifica se o vínculo entre município e administração é criado corretamente."""
    cod_mun = setup_data["cod_municipio"]
    cod_adm = setup_data["cod_administracao"]

    # Ação: Cria o vínculo
    entity_id = await create_municipio_administracao_link(cod_mun, cod_adm)
    assert entity_id is not None

    # Verificação: Busca o vínculo para confirmar
    found_entity_id = await busca_entidade_id(cod_mun, cod_adm)
    assert found_entity_id == entity_id

@pytest.mark.asyncio
async def test_inserir_e_verificar_credencial(setup_data):
    """Testa a inserção de uma nova credencial e a verificação de sua existência."""
    cod_mun = setup_data["cod_municipio"]
    cod_adm = setup_data["cod_administracao"]

    # Cria o vínculo primeiro
    entity_id = await create_municipio_administracao_link(cod_mun, cod_adm)

    # Verificação 1: Confirma que a credencial ainda não existe
    credencial_existe_antes = await check_credencial(entity_id)
    assert credencial_existe_antes is False

    # Ação: Insere a credencial
    success_insert = await insert_credencial(entity_id, "11122233344", "senha123", True)
    assert success_insert is True

    # Verificação 2: Confirma que a credencial agora existe
    credencial_existe_depois = await check_credencial(entity_id)
    assert credencial_existe_depois is True

@pytest.mark.asyncio
async def test_atualizar_credencial(setup_data):
    """Testa a função de atualização de credenciais."""
    cod_mun = setup_data["cod_municipio"]
    cod_adm = setup_data["cod_administracao"]
    entity_id = await create_municipio_administracao_link(cod_mun, cod_adm)
    await insert_credencial(entity_id, "11122233344", "senha_antiga", True)

    # Ação: Atualiza a senha
    updates = {"senha": "senha_nova"}
    success_update = await update_credenciais(entity_id, updates)
    assert success_update is True

    # Verificação: Busca os dados completos para confirmar a alteração
    query = select(credenciais.c.senha).where(credenciais.c.cod_entidade == entity_id)
    result = await database.fetch_one(query)
    assert result["senha"] == "senha_nova"

@pytest.mark.asyncio
async def test_fetch_credenciais_retorna_dados_corretos(setup_data):
    """Verifica se a função de busca principal retorna os dados esperados."""
    cod_mun = setup_data["cod_municipio"]
    cod_adm = setup_data["cod_administracao"]
    entity_id = await create_municipio_administracao_link(cod_mun, cod_adm)
    await insert_credencial(entity_id, "12345678901", "senha_secreta", True)

    # Ação: Busca as credenciais pelo ID do município
    resultados = await fetch_credenciais_por_id(cod_mun)

    # Verificação
    assert len(resultados) == 1
    credencial_encontrada = resultados[0]
    assert credencial_encontrada["municipio_nome"] == "Cidade Teste"
    assert credencial_encontrada["adm_sigla"] == "PM"
    assert credencial_encontrada["cpf_usuario"] == "12345678901"
    assert credencial_encontrada["senha"] == "senha_secreta"
    assert credencial_encontrada["status_validade"] is True

@pytest.mark.asyncio
async def test_busca_entidade_inexistente_retorna_none(setup_data):
    """Verifica se a busca por uma entidade com um ID de administração inválido retorna None."""
    cod_mun = setup_data["cod_municipio"]
    cod_adm_invalido = 999 # Um ID que não existe

    # Ação e Verificação
    entity_id = await busca_entidade_id(cod_mun, cod_adm_invalido)
    assert entity_id is None
