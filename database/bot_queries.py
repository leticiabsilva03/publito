# database/bot_queries.py
import logging
from typing import Dict, List, Optional
from datetime import datetime, date
from sqlalchemy import select, insert, delete, update, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Importa a conexão principal com o banco de dados do bot
from .db_manager import database
# Importa a definição das novas tabelas
from .models import responsaveis_equipes, solicitacoes_horas_extras, colaboradores

logger = logging.getLogger(__name__)

async def definir_responsavel(equipe_id: int, responsavel_discord_id: int) -> bool:
    """Cria ou atualiza o responsável por uma equipe (UPSERT)."""
    try:
        stmt = pg_insert(responsaveis_equipes).values(
            equipe_id=equipe_id,
            responsavel_discord_id=responsavel_discord_id,
            data_atualizacao=datetime.now()
        ).on_conflict_do_update(
            index_elements=['equipe_id'],
            set_={'responsavel_discord_id': responsavel_discord_id, 'data_atualizacao': datetime.now()}
        )
        await database.execute(stmt)
        return True
    except Exception as e:
        logger.error(f"Erro ao definir responsável para equipe_id {equipe_id}: {e}", exc_info=True)
        return False

async def remover_responsavel(equipe_id: int) -> bool:
    """Remove o responsável de uma equipe."""
    try:
        query = delete(responsaveis_equipes).where(responsaveis_equipes.c.equipe_id == equipe_id)
        await database.execute(query)
        return True
    except Exception as e:
        logger.error(f"Erro ao remover responsável da equipe_id {equipe_id}: {e}", exc_info=True)
        return False

async def listar_todos_responsaveis() -> List[Dict]:
    """Lista todos os mapeamentos de equipe x responsável."""
    query = select(responsaveis_equipes)
    return await database.fetch_all(query)

# --- Funções para Mapeamento de Usuários (tabela public.colaboradores) ---

async def buscar_colaborador_mapeado(discord_id: int) -> Optional[Dict]:
    """Busca um mapeamento de colaborador pelo ID do Discord na tabela do bot."""
    query = select(colaboradores).where(colaboradores.c.discord_id == discord_id)
    row = await database.fetch_one(query)
    try:
        if row:
            return {
                "discord_id": row.discord_id,
                "colaborador_id": row.colaborador_id,
                "nome": row.nome,
                "matricula": row.matricula
                #"id_equipe": row.id_equipe,
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar colaborador mapeado {discord_id}: {e}", exc_info=True)
        return None

async def salvar_mapeamento(discord_id: int, colaborador_id: int, matricula: str, nome: str) -> bool:
    """Cria ou ignora um mapeamento de usuário (INSERT ... ON CONFLICT)."""
    try:
        stmt = pg_insert(colaboradores).values(
            discord_id=discord_id,
            colaborador_id=colaborador_id,
            matricula=str(matricula),
            nome = nome
        ).on_conflict_do_nothing(index_elements=['discord_id'])
        await database.execute(stmt)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar mapeamento para discord_id {discord_id}: {e}", exc_info=True)
        return False

# --- Funções para Gerenciamento de Responsáveis (tabela public.responsaveis_equipes) ---

async def buscar_responsavel_por_equipe(equipe_id: int) -> Optional[Dict]:
    """Busca o responsável de uma equipe na tabela de mapeamento do bot."""
    query = select(responsaveis_equipes).where(responsaveis_equipes.c.equipe_id == equipe_id)
    return await database.fetch_one(query)

async def definir_responsavel(equipe_id: int, responsavel_discord_id: int) -> bool:
    """Cria ou atualiza o responsável por uma equipe (UPSERT)."""
    try:
        stmt = pg_insert(responsaveis_equipes).values(
            equipe_id=equipe_id,
            responsavel_discord_id=responsavel_discord_id,
            data_atualizacao=datetime.now()
        ).on_conflict_do_update(
            index_elements=['equipe_id'],
            set_={'responsavel_discord_id': responsavel_discord_id, 'data_atualizacao': datetime.now()}
        )
        await database.execute(stmt)
        return True
    except Exception as e:
        logger.error(f"Erro ao definir responsável para equipe_id {equipe_id}: {e}", exc_info=True)
        return False

async def remover_responsavel(equipe_id: int) -> bool:
    """Remove o responsável de uma equipe."""
    try:
        query = delete(responsaveis_equipes).where(responsaveis_equipes.c.equipe_id == equipe_id)
        await database.execute(query)
        return True
    except Exception as e:
        logger.error(f"Erro ao remover responsável da equipe_id {equipe_id}: {e}", exc_info=True)
        return False

async def listar_todos_responsaveis() -> List[Dict]:
    """Lista todos os mapeamentos de equipe x responsável."""
    query = select(responsaveis_equipes)
    return await database.fetch_all(query)


# --- Funções para Solicitações de Horas Extras (tabela public.solicitacoes_horas_extras) ---

async def criar_solicitacao(solicitante_id: int, dados_formulario: Dict) -> Optional[int]:
    """Cria um novo registro de solicitação e retorna o ID."""
    try:
        query = insert(solicitacoes_horas_extras).values(
            solicitante_discord_id=solicitante_id,
            status='PENDENTE_APROVACAO_RESPONSAVEL',
            dados_formulario=dados_formulario
        ).returning(solicitacoes_horas_extras.c.id)
        result = await database.execute(query)
        return result
    except Exception as e:
        logger.error(f"Erro ao criar solicitação para {solicitante_id}: {e}", exc_info=True)
        return None

async def atualizar_status_solicitacao(solicitacao_id: int, status: str, responsavel_id: int):
    """Atualiza o status de uma solicitação existente."""
    try:
        query = update(solicitacoes_horas_extras).where(solicitacoes_horas_extras.c.id == solicitacao_id).values(
            status=status,
            responsavel_discord_id=responsavel_id,
            data_decisao=datetime.now()
        )
        await database.execute(query)
        return True
    except Exception:
        return False

async def buscar_datas_bloqueadas(discord_id: int) -> List[date]:
    """
    Busca todas as datas de horas extras que estão pendentes ou já foram aprovadas.
    Extrai a data de um array de objetos JSONB.
    """
    query = """
    SELECT
        (dia ->> 'data')::date -- 3. Extrai o valor da chave 'data' como texto e converte para data
    FROM
        public.solicitacoes_horas_extras s,
        -- 1. Pega o campo 'detalhes_selecionados', que é um array JSONB
        -- 2. Transforma cada objeto do array em uma linha separada chamada 'dia'
        jsonb_array_elements(s.dados_formulario -> 'detalhes_selecionados') AS dia
    WHERE 
        s.solicitante_discord_id = :discord_id 
        AND s.status IN ('APROVADO', 'PENDENTE_APROVACAO_RESPONSAVEL')
    """
    try:
        results = await database.fetch_all(query, values={"discord_id": discord_id})
        return [row[0] for row in results]
    except Exception as e:
        logger.error(f"Erro ao buscar datas bloqueadas para {discord_id}: {e}", exc_info=True)
        return []
    
async def cancelar_solicitacao(solicitacao_id: int, solicitante_id: int) -> bool:
    """
    Atualiza o status de uma solicitação para 'CANCELADO'.
    A verificação do solicitante_id garante que apenas o próprio usuário possa cancelar.
    """
    try:
        query = update(solicitacoes_horas_extras).where(
            solicitacoes_horas_extras.c.id == solicitacao_id,
            solicitacoes_horas_extras.c.solicitante_discord_id == solicitante_id
        ).values(
            status='CANCELADO',
            data_decisao=datetime.now()
        )
        await database.execute(query)
        logger.info(f"Solicitação ID {solicitacao_id} cancelada pelo usuário {solicitante_id}.")
        return True
    except Exception as e:
        logger.error(f"Erro ao cancelar solicitação {solicitacao_id}: {e}", exc_info=True)
        return False