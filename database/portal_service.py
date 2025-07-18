# database/portal_service.py
import os
import pyodbc
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

class PortalDatabaseService:
    """Serviço para consultas read-only ao banco de dados corporativo (SQL Server)."""

    def __init__(self):
        self.connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={os.getenv('CORP_DB_HOST')};"
            f"DATABASE={os.getenv('CORP_DB_NAME')};"
            f"UID={os.getenv('CORP_DB_USER')};"
            f"PWD={os.getenv('CORP_DB_PASSWORD')};"
            f"TrustServerCertificate=yes;"
        )
        self.connection = None

    def _conectar(self):
        """Estabelece uma conexão com o banco de dados."""
        try:
            self.connection = pyodbc.connect(self.connection_string, timeout=5)
        except Exception as e:
            logger.error(f"Falha ao conectar ao banco de dados corporativo: {e}", exc_info=True)
            raise

    def _fechar_conexao(self):
        """Fecha a conexão com o banco de dados."""
        if self.connection:
            self.connection.close()

    def buscar_dados_colaborador(self, id_discord: int) -> Optional[Dict]:
        """Busca os dados cadastrais de um colaborador e adiciona um nome de responsável fixo."""
        query = """
        SELECT
            c.nome, c.email, car.descricao as nome_cargo, dep.descricao as nome_departamento,
            'Calisson André Soares' as nome_responsavel
        FROM PortalCorporativo.portalrh.colaborador as c
        LEFT JOIN PortalCorporativo.portalrh.cargo as car ON c.id_cargo = car.id
        LEFT JOIN PortalCorporativo.portalrh.equipe as eq ON c.id_equipe = eq.id
        LEFT JOIN PortalCorporativo.portalrh.departamento as dep ON eq.id_departamento = dep.id
        WHERE c.id_discord = ? AND c.desligamento_data IS NULL;
        """
        try:
            self._conectar()
            cursor = self.connection.cursor()
            cursor.execute(query, id_discord)
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None
        finally:
            self._fechar_conexao()

    def buscar_detalhes_ponto_recente(self, id_discord: int) -> List[Dict]:
        """
        Busca todas as batidas de ponto dos últimos 7 dias e processa os dados
        para calcular o total trabalhado e as horas extras por dia.
        """
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=7)

        query = """
        SELECT pm.data, pm.hora
        FROM PortalCorporativo.portalrh.ponto_marcacao as pm
        JOIN PortalCorporativo.portalrh.colaborador as c ON pm.pis = c.pis_numero
        WHERE c.id_discord = ? AND pm.data BETWEEN ? AND ?
        ORDER BY pm.data, pm.hora;
        """
        marcacoes_por_dia = defaultdict(list)
        try:
            self._conectar()
            cursor = self.connection.cursor()
            cursor.execute(query, id_discord, data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d'))
            for row in cursor.fetchall():
                marcacoes_por_dia[row.data].append(datetime.strptime(row.hora, '%H:%M').time())
        finally:
            self._fechar_conexao()

        dias_detalhados = []
        for dia, batidas in marcacoes_por_dia.items():
            # Garante que temos um número par de batidas para calcular os períodos
            if len(batidas) % 2 != 0:
                logger.warning(f"Dia {dia} para id_discord {id_discord} tem um número ímpar de batidas. Ignorando.")
                continue

            total_trabalhado = timedelta()
            for i in range(0, len(batidas), 2):
                entrada = datetime.combine(dia, batidas[i])
                saida = datetime.combine(dia, batidas[i+1])
                total_trabalhado += (saida - entrada)
            
            jornada_padrao = timedelta(hours=8)
            horas_extras = total_trabalhado - jornada_padrao if total_trabalhado > jornada_padrao else timedelta(0)

            # Só mostra dias que tiveram horas extras
            if horas_extras > timedelta(0):
                dias_detalhados.append({
                    "data": dia,
                    "batidas_str": " - ".join([t.strftime('%H:%M') for t in batidas]),
                    "horas_extras_timedelta": horas_extras
                })
        
        return sorted(dias_detalhados, key=lambda x: x['data'], reverse=True)