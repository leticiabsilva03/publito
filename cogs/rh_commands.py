# cogs/rh_comandos.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
from views.rh_view import BotoesSelecaoTipoView # Importa a nova view inicial

logger = logging.getLogger(__name__)

class RHCommands(commands.Cog):
    """Controlador para os comandos de Recursos Humanos."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bancohoras", description="Inicia o preenchimento do formulário de horas extras.")
    async def bancohoras(self, interaction: discord.Interaction):
        """Inicia o fluxo interativo para solicitação de horas extras."""
        try:
            # Cria e envia a primeira view com os botões de seleção
            view = BotoesSelecaoTipoView()
            await interaction.response.send_message(
                "Por favor, selecione a modalidade das horas extras:",
                view=view,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Erro ao iniciar o comando /bancohoras: {e}", exc_info=True)
            await interaction.response.send_message("❌ Ocorreu um erro inesperado. Tente novamente mais tarde.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(RHCommands(bot))
    logger.info("Cog 'RHCommands' carregado com sucesso.")