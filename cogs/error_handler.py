# cogs/error_handler.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
import traceback

logger = logging.getLogger(__name__)

class ErrorHandler(commands.Cog):
    """Um Cog dedicado para tratar os erros dos comandos de forma global."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Listener global para todos os erros de comandos de barra."""
        
        original_error = getattr(error, 'original', error)

        # --- Caso 1: Falta de permissão ---
        if isinstance(error, app_commands.CheckFailure):
            logger.warning(
                f"Utilizador '{interaction.user}' (ID: {interaction.user.id}) tentou usar o comando '{interaction.command.name}' sem permissão."
            )
            embed = discord.Embed(
                title="❌ Acesso Negado",
                description="Você não tem o cargo necessário para executar este comando.",
                color=discord.Color.red()
            )

            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # --- Caso 2: Erro genérico ---
        tb_str = "".join(traceback.format_exception(type(original_error), original_error, original_error.__traceback__))
        logger.error(f"Ocorreu um erro não tratado no comando '{interaction.command.name}':\n{tb_str}")

        embed = discord.Embed(
            title="😕 Ocorreu um Erro Inesperado",
            description="Ocorreu um erro ao processar o seu comando. A equipa de desenvolvimento será notificada.",
            color=discord.Color.orange()
        )

        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))
    logger.info("Cog 'ErrorHandler' carregado com sucesso.")
