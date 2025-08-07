# cogs/rh_commands.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
from views.rh_view import BotoesSelecaoTipoView 
from database.portal_service import PortalDatabaseService

logger = logging.getLogger(__name__)

class RHCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Criamos uma instância do serviço para ser usada pelo cog
        self.portal_db = PortalDatabaseService()

    @app_commands.command(name="bancohoras", description="Inicia o preenchimento do formulário de horas extras.")
    async def bancohoras(self, interaction: discord.Interaction):
        """Verifica o registro e busca os dados completos do colaborador antes de iniciar o fluxo."""
        
        dados_completos_colaborador = await self.portal_db.buscar_dados_completos_colaborador(interaction.user.id)
        
        if not dados_completos_colaborador:
            embed = discord.Embed(
                title="⚠️ Registro Necessário",
                description="Sua conta do Discord não está vinculada a um cadastro. Por favor, use o comando `/registrar`.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            view = BotoesSelecaoTipoView(dados_colaborador=dados_completos_colaborador)
            await interaction.response.send_message(
                f"Olá, {dados_completos_colaborador['nome']}! Selecione a modalidade das horas extras:",
                view=view,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Erro ao iniciar o comando /bancohoras: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Ocorreu um erro.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(RHCommands(bot))