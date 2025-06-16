import logging
from typing import List, Dict
from sqlalchemy import select

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