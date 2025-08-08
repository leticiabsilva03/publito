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
        self.portal_db = PortalDatabaseService()

    @app_commands.command(name="bancohoras", description="Inicia o preenchimento do formulário de horas extras.")
    async def bancohoras(self, interaction: discord.Interaction):
        """Verifica o registro e busca os dados completos do colaborador antes de iniciar o fluxo."""

        # Deferimos a resposta para evitar timeout
        await interaction.response.defer(ephemeral=True)

        try:
            dados_completos_colaborador = await self.portal_db.buscar_dados_completos_colaborador(interaction.user.id)

            if not dados_completos_colaborador:
                embed = discord.Embed(
                    title="⚠️ Registro Necessário",
                    description="Sua conta do Discord não está vinculada a um cadastro. Por favor, use o comando `/registrar`.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            view = BotoesSelecaoTipoView(dados_colaborador=dados_completos_colaborador)
            await interaction.followup.send(
                f"Olá, {dados_completos_colaborador['nome']}! Selecione a modalidade das horas extras:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Erro ao iniciar o comando /bancohoras: {e}", exc_info=True)
            # Como já deferimos, usamos followup para enviar a mensagem de erro
            await interaction.followup.send("❌ Ocorreu um erro.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(RHCommands(bot))
