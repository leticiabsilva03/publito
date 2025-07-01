import logging
from typing import List, Dict, Optional
from sqlalchemy import select, update, or_, insert
from datetime import date
from asyncpg.exceptions import UniqueViolationError
# Importa os modelos e a instância de conexão corretos
from .db_manager import database
from .models import municipios, administracoes, municipios_administracoes, credenciais

logger = logging.getLogger(__name__)

async def fetch_municipio_autocomplete(search_term: str) -> List[Dict]:
    """
    Busca municípios no banco de dados para a função de autocomplete.
    Usa ILIKE na coluna nom_municipio.
    """
    try:
        query = (
            select(municipios.c.cod_municipio, municipios.c.nom_municipio)
            .where(municipios.c.nom_municipio.ilike(f"%{search_term}%"))
            .limit(25)
            .order_by(municipios.c.nom_municipio)
        )
        return await database.fetch_all(query)
    except Exception as e:
        logger.error(f"Erro ao buscar municípios para autocomplete: {e}", exc_info=True)
        return []

async def fetch_credenciais_por_id(municipio_id: int) -> List[Dict]:
    """
    Busca todas as credenciais de um município específico pelo seu ID,
    juntando todas as tabelas necessárias.
    """
    try:
        # Define a junção complexa entre as quatro tabelas
        j = credenciais.join(
            municipios_administracoes,
            credenciais.c.cod_entidade == municipios_administracoes.c.cod_entidade
        ).join(
            municipios,
            municipios_administracoes.c.cod_municipio == municipios.c.cod_municipio
        ).join(
            administracoes,
            municipios_administracoes.c.cod_administracao == administracoes.c.cod_administracao
        )

        # Seleciona as colunas desejadas, usando labels para clareza
        query = (
            select(
                municipios.c.nom_municipio.label("municipio_nome"),
                administracoes.c.sigla_administracao.label("adm_sigla"),
                administracoes.c.des_administracao.label("adm_descricao"),
                credenciais.c.cpf_usuario,
                credenciais.c.senha,
                credenciais.c.status_validade
            )
            .select_from(j)
            .where(municipios.c.cod_municipio == municipio_id) # Filtra pelo ID do município
            .order_by(administracoes.c.sigla_administracao)
        )
        return await database.fetch_all(query)
    except Exception as e:
        logger.error(f"Erro ao buscar credenciais para o município ID {municipio_id}: {e}", exc_info=True)
        return []
    
async def fetch_administracao_autocomplete(search_term: str) -> List[Dict]:
    """Busca administrações para a função de autocomplete, pesquisando na sigla e na descrição."""
    try:
        query = (
            select(
                administracoes.c.cod_administracao, 
                administracoes.c.sigla_administracao,
                administracoes.c.des_administracao  # Seleciona a descrição para exibir ao usuário
            )
            .where(
                or_( # Usa OR para buscar em qualquer uma das colunas
                    administracoes.c.sigla_administracao.ilike(f"%{search_term}%"),
                    administracoes.c.des_administracao.ilike(f"%{search_term}%")
                )
            )
            .limit(25)
            .order_by(administracoes.c.sigla_administracao)
        )
        return await database.fetch_all(query)
    except Exception as e:
        logger.error(f"Erro ao buscar administrações para autocomplete: {e}", exc_info=True)
        return []

async def busca_entidade_id(municipio_id: int, administracao_id: int) -> Optional[int]:
    """Encontra o cod_entidade na tabela de junção com base nos IDs do município e da administração."""
    try:
        query = select(municipios_administracoes.c.cod_entidade).where(
            municipios_administracoes.c.cod_municipio == municipio_id,
            municipios_administracoes.c.cod_administracao == administracao_id
        )
        result = await database.fetch_one(query)
        return result["cod_entidade"] if result else None
    except Exception as e:
        logger.error(f"Erro ao buscar cod_entidade: {e}", exc_info=True)
        return None

async def update_credenciais(entity_id: int, updates: Dict) -> bool:
    """
    Atualiza as credenciais de uma entidade específica.
    'updates' é um dicionário contendo os campos a serem atualizados.
    """
    if not updates:
        return False  # Nada para atualizar
        
    # Adiciona automaticamente a data de atualização em qualquer operação de UPDATE
    updates["data_atualizacao"] = date.today()
    
    try:
        query = (
            update(credenciais)
            .where(credenciais.c.cod_entidade == entity_id)
            .values(**updates) # O operador ** desempacota o dicionário
        )
        await database.execute(query)
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar credenciais para entidade ID {entity_id}: {e}", exc_info=True)
        return False
    
async def insert_municipio(nome: str, cnpj: str) -> Dict[str, any]:
    """Tenta inserir um novo município na tabela sicom.municipios."""
    try:
        query = insert(municipios).values(nom_municipio=nome, cnpj_municipio=cnpj)
        await database.execute(query)
        return {"success": True, "message": "Município registrado com sucesso!"}

    # Captura a exceção específica de violação de unicidade
    except UniqueViolationError as e:
        error_message = str(e).lower()
        if "nom_municipio" in error_message:
            logger.warning(f"Tentativa de inserir município duplicado pelo nome: {nome}")
            return {"success": False, "message": f"❌ O município '{nome}' já existe no banco de dados."}
        if "cnpj_municipio" in error_message:
            logger.warning(f"Tentativa de inserir município duplicado pelo CNPJ: {cnpj}")
            return {"success": False, "message": f"❌ O CNPJ '{cnpj}' já pertence a outro município."}
        
        # Fallback para outras violações de unicidade
        logger.error(f"Erro de violação de unicidade não esperado: {e}", exc_info=True)
        return {"success": False, "message": "Ocorreu um erro de duplicidade não esperado."}
        
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir município {nome}: {e}", exc_info=True)
        return {"success": False, "message": "Ocorreu um erro inesperado no servidor."}
        
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir município {nome}: {e}", exc_info=True)
        return {"success": False, "message": "Ocorreu um erro inesperado no servidor."}

async def create_municipio_administracao_link(municipio_id: int, administracao_id: int) -> Optional[int]:
    """
    Cria um novo vínculo na tabela municipios_administracoes e retorna o ID da nova entidade.
    """
    try:
        query = (
            insert(municipios_administracoes)
            .values(cod_municipio=municipio_id, cod_administracao=administracao_id)
            .returning(municipios_administracoes.c.cod_entidade) # Retorna o ID recém-criado
        )
        # fetch_one() é usado para obter o resultado do 'returning'
        result = await database.fetch_one(query)
        return result["cod_entidade"] if result else None
    except Exception as e:
        logger.error(f"Erro ao criar link para município {municipio_id} e adm {administracao_id}: {e}", exc_info=True)
        return None

async def check_credencial(entity_id: int) -> bool:
    """Verifica se já existe uma credencial para uma determinada entidade."""
    try:
        query = select(credenciais.c.cod_credencial).where(credenciais.c.cod_entidade == entity_id)
        result = await database.fetch_one(query)
        return result is not None # Retorna True se encontrou algo, False caso contrário
    except Exception as e:
        logger.error(f"Erro ao verificar existência de credencial para entidade {entity_id}: {e}", exc_info=True)
        return True # Assume que existe em caso de erro para evitar duplicação

async def insert_credencial(entity_id: int, cpf_usuario: str, senha: str, status_validade: bool) -> bool:
    """Insere uma nova credencial na tabela."""
    try:
        query = insert(credenciais).values(
            cod_entidade=entity_id,
            cpf_usuario=cpf_usuario,
            senha=senha,
            data_atualizacao=date.today(),
            status_validade=status_validade
        )
        await database.execute(query)
        return True
    except Exception as e:
        logger.error(f"Erro ao inserir credencial para entidade {entity_id}: {e}", exc_info=True)
        return False