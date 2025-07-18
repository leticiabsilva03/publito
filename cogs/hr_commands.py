# cogs/hr_commands.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
from views.hr_views import OvertimeMainModal

logger = logging.getLogger(__name__)

class RHCommands(commands.Cog):
    """Controlador para os comandos de Recursos Humanos."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bancohoras", description="Inicia o preenchimento do formulário de banco de horas.")
    @app_commands.describe(tipo_compensacao="Selecione a modalidade das horas extras.")
    @app_commands.choices(tipo_compensacao=[
        app_commands.Choice(name="Pagamento de Horas", value="pagamento"),
        app_commands.Choice(name="Horas a serem compensadas", value="compensacao"),
        app_commands.Choice(name="Banco de Horas", value="banco"),
    ])
    async def bancohoras(self, interaction: discord.Interaction, tipo_compensacao: app_commands.Choice[str]):
        """Inicia o fluxo e delega a lógica para as Views, passando a escolha do utilizador."""
        await interaction.response.send_modal(OvertimeMainModal(compensation_choice=tipo_compensacao.value))

async def setup(bot: commands.Bot):
    await bot.add_cog(RHCommands(bot))
    logger.info("Cog 'RHCommands' carregado com sucesso.")