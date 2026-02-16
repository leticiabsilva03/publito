# cogs/rh_commands.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
from views.rh_view import BotoesSelecaoTipoView
from services.portal_service import PortalDatabaseService
from database import bot_queries

from cogs.registrar_commands import RegistroColaboradorModal

logger = logging.getLogger(__name__)

class RHCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.portal_db = PortalDatabaseService()

    @app_commands.command(name="bancohoras", description="Inicia o preenchimento do formulário de horas extras.")
    async def bancohoras(self, interaction: discord.Interaction):
        """Verifica o registro e busca os dados completos do colaborador antes de iniciar o fluxo."""

        try:
            # Verifica se já está registrado no banco do bot
            colaborador_check = await bot_queries.buscar_colaborador_mapeado(interaction.user.id)

            if not colaborador_check:
                # Usuário não registrado → abre modal diretamente
                modal = RegistroColaboradorModal(user=interaction.user)
                await interaction.response.send_modal(modal)
                return

            colaborador = await self.portal_db.buscar_dados_completos_colaborador(interaction.user.id)

            # Usuário já registrado segue esse fluxo
            await interaction.response.defer(ephemeral=True)

            embed = discord.Embed(
                title="📊 Banco de Horas",
                description=f"Registro de horas para {interaction.user.mention}",
                color=discord.Color.blue()
            )

            view = BotoesSelecaoTipoView(dados_colaborador=colaborador)
            await interaction.followup.send(
                f"Olá, {colaborador['nome']}! Selecione a modalidade das horas extras:",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Erro ao iniciar o comando /bancohoras: {e}", exc_info=True)

            # Só responde erro se a interaction ainda não foi respondida
            if interaction.response.is_done():
                await interaction.followup.send("❌ Ocorreu um erro ao final da interação.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ocorreu um erro durante a interação.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RHCommands(bot))
