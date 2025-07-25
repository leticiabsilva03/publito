# cogs/news_cog.py
import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

# Importando das outras camadas
from services.comunicados_service import fetch_ultimos_comunicados
from views.comunicado_sicom_view import insere_comunicado_embed
from database.queries import verifica_comunicado_postado , marcar_comunicado_postado

logger = logging.getLogger(__name__)

# Horários para a tarefa ser executada (no fuso horário do servidor)
FUSO_SAO_PAULO = ZoneInfo("America/Sao_Paulo")
# Carrega os horários do .env, com um valor padrão caso não esteja definido
# Exemplo: "09:00,14:00" para verificar às 9h e 14h
horarios_str = os.getenv("COMUNICADOS_HORARIOS", "09:00,14:00")
VERIFICA_HORARIOS = []

try:
    # Separa a string por vírgulas, ex: "09:00,14:00" -> ["09:00", "14:00"]
    times_str_list = [t.strip() for t in horarios_str.split(',') if t.strip()]
    for t_str in times_str_list:
        # Separa cada horário por dois pontos, ex: "09:00" -> [9, 0]
        h, m = map(int, t_str.split(':'))
        VERIFICA_HORARIOS.append(time(hour=h, minute=m, tzinfo=FUSO_SAO_PAULO))
    
    if not VERIFICA_HORARIOS:
        raise ValueError("A variável de horários está vazia.")

    logger.info(f"Tarefa de comunicados agendada para os seguintes horários (America/Sao_Paulo): {times_str_list}")

except Exception as e:
    logger.error(f"Formato inválido para COMUNICADOS_HORARIOS ('{horarios_str}'). Usando horários padrão (09:00/14:00). Erro: {e}")
    # Se houver qualquer erro no formato, usa um horário padrão seguro.
    VERIFICA_HORARIOS = [
        time(hour=9, minute=0, tzinfo=FUSO_SAO_PAULO),
        time(hour=14, minute=00, tzinfo=FUSO_SAO_PAULO)
    ]

class ComunicadoSicom(commands.Cog):
    """Cog para gerenciar comunicados do SICOM."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = int(os.getenv("COMUNICADOS_SICOM_ID", "0"))
        if not self.channel_id:
            logger.error("NEWS_CHANNEL_ID não está configurado no .env! A tarefa de notícias não será iniciada.")
        else:
            self.verifica_comunicados.start()

    def cog_unload(self):
        """Função chamada quando o Cog é descarregado, para parar a tarefa."""
        self.verifica_comunicados.cancel()

    @tasks.loop(time=VERIFICA_HORARIOS)
    async def verifica_comunicados(self):
        """Tarefa que verifica por novos comunicados do SICOM."""
        logger.info("Executando a tarefa de verificação de comunicados do SICOM...")
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            logger.error("Não foi possível encontrar o canal de notícias com ID %s.", self.channel_id)
            return

        # Busca apenas os 2 comunicados mais recentes para a verificação diária
        ultimos_comunicados = await fetch_ultimos_comunicados(limit=2)
        if not ultimos_comunicados:
            logger.warning("Não foi possível buscar comunicados do SICOM na tarefa agendada.")
            return

        # Itera sobre os comunicados encontrados para verificar se são novos
        for comunicados in ultimos_comunicados:
            is_posted = await verifica_comunicado_postado(comunicados['link'])

            if not is_posted:
                logger.info("Novo comunicado encontrado: %s", comunicados['titulo_comunicado'])
                embed = insere_comunicado_embed(comunicados)

                try:
                    await channel.send(content="@everyone, um novo comunicado do SICOM foi publicado!", embed=embed)
                    await marcar_comunicado_postado(comunicados['link'], comunicados['titulo_comunicado'], comunicados['data_comunicado'])
                    logger.info("Novo comunicado '%s' enviado com sucesso para o Discord.", comunicados['titulo_comunicado'])
                except discord.Forbidden:
                    logger.error("Permissão negada para enviar mensagem no canal %s.", channel.name)
                except Exception as e:
                    logger.error("Erro ao enviar novo comunicado: %s", e, exc_info=True)
            else:
                logger.info("O comunicado '%s' já foi postado. Ignorando.", comunicados['titulo_comunicado'])

    @verifica_comunicados.before_loop
    async def before_verifica_comunicados(self):
        """Espera até que o bot esteja pronto antes de iniciar o loop."""
        await self.bot.wait_until_ready()

    @app_commands.command(name="comunicados", description="Exibe os 5 últimos comunicados do SICOM.")
    async def get_ultimos_comunicados(self, interaction: discord.Interaction):
        """Comando que busca e exibe os últimos 5 comunicados."""
        await interaction.response.defer(ephemeral=True)
        
        comunicados = await fetch_ultimos_comunicados(limit=5)
        
        if not comunicados:
            await interaction.followup.send("❌ Não foi possível buscar os comunicados no momento. Tente novamente mais tarde.", ephemeral=True)
            return

        embeds = [insere_comunicado_embed(com) for com in comunicados]

        await interaction.followup.send("Aqui estão os últimos 5 comunicados do SICOM:", embeds=embeds, ephemeral=True)

async def setup(bot: commands.Bot):
    """Função de setup para carregar o Cog."""
    logger.info("Carregando o Cog 'ComunicadoSicom'...")
    await bot.add_cog(ComunicadoSicom(bot))
    logger.info("Cog 'ComunicadoSicom' carregado com sucesso.")
