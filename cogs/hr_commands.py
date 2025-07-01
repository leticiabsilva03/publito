# cogs/hr_commands.py
import discord
from discord import app_commands
from discord.ext import commands
import logging

# Importa a Visão principal (modal) da camada de Visão
from views.hr_views import OvertimeMainModal

logger = logging.getLogger(__name__)

class RHCommands(commands.Cog):
    """Controlador para os comandos de Recursos Humanos."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bancohoras", description="Inicia o preenchimento do formulário de banco de horas.")
    async def bancohoras(self, interaction: discord.Interaction):
        """
        Este comando atua como um ponto de entrada.
        Ele delega toda a lógica de interação para as Views e Modals.
        """
        # A única responsabilidade do controlador é iniciar a Visão.
        await interaction.response.send_modal(OvertimeMainModal())

async def setup(bot: commands.Bot):
    await bot.add_cog(RHCommands(bot))
    logger.info("Cog 'RHCommands' carregado com sucesso.")