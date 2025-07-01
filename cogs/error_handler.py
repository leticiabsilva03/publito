# cogs/error_handler.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
import traceback

# Configura o logger para este ficheiro
logger = logging.getLogger(__name__)

class ErrorHandler(commands.Cog):
    """Um Cog dedicado para tratar os erros dos comandos de forma global."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Define um 'listener' especial para o evento 'on_app_command_error'
        # Este listener é chamado automaticamente sempre que um comando de barra (/) falha.
        bot.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """O listener global para todos os erros de comandos de barra."""
        
        # A propriedade 'original' contém a exceção original que causou o erro.
        original_error = getattr(error, 'original', error)

        # --- CASO 1: O utilizador não tem o cargo necessário para usar o comando ---
        # 'CheckFailure' é o erro levantado quando uma verificação como @checks.has_role() falha.
        if isinstance(error, app_commands.CheckFailure):
            logger.warning(f"Utilizador '{interaction.user}' (ID: {interaction.user.id}) tentou usar o comando '{interaction.command.name}' sem permissão.")
            
            embed = discord.Embed(
                title="❌ Acesso Negado",
                description="Você não tem o cargo necessário para executar este comando.",
                color=discord.Color.red()
            )
            # Verifica se a interação já foi respondida para evitar erros
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # --- CASO 2: Erro genérico (bug no código, falha de API, etc.) ---
        # Este é um "catch-all" para qualquer outro erro que não foi tratado acima.
        
        # Loga o erro completo no console/ficheiro de log para que os desenvolvedores possam depurar.
        tb_str = "".join(traceback.format_exception(type(original_error), original_error, original_error.__traceback__))
        logger.error(f"Ocorreu um erro não tratado no comando '{interaction.command.name}':\n{tb_str}")

        # Envia uma mensagem genérica e amigável para o utilizador.
        embed = discord.Embed(
            title="😕 Ocorreu um Erro Inesperado",
            description="Ocorreu um erro ao processar o seu comando. A equipa de desenvolvimento será notificada.",
            color=discord.Color.orange()
        )
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Função obrigatória que o discord.py chama para carregar o Cog."""
    await bot.add_cog(ErrorHandler(bot))
    logger.info("Cog 'ErrorHandler' carregado com sucesso.")