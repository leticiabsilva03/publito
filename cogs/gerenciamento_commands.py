# cogs/gerenciamento_commands.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import List
from services.portal_service import PortalDatabaseService
from database.bot_queries import definir_responsavel, remover_responsavel, listar_todos_responsaveis

logger = logging.getLogger(__name__)

class GerenciamentoCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.portal_db = PortalDatabaseService()

    # --- Autocomplete para o nome da equipe ---
    async def equipe_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        equipes = self.portal_db.buscar_equipes_autocomplete(current)
        return [app_commands.Choice(name=equipe['descricao'], value=str(equipe['id'])) for equipe in equipes][:25]

    # === COMANDOS DE ADMIN ===
    @app_commands.command(name="definir-responsavel", description="[Admin] Define o responsável por uma equipe.")
    @app_commands.autocomplete(equipe=equipe_autocomplete)
    @app_commands.checks.has_role("ADM") # <-- Defina o cargo de admin aqui
    async def definir_responsavel(self, interaction: discord.Interaction, equipe: str, responsavel: discord.Member):
        equipe_id = int(equipe)
        success = await definir_responsavel(equipe_id, responsavel.id)
        if success:
            await interaction.response.send_message(f"✅ {responsavel.mention} foi definido como responsável pela equipe selecionada.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erro ao definir responsável.", ephemeral=True)

    @app_commands.command(name="remover-responsavel", description="[Admin] Remove o responsável de uma equipe.")
    @app_commands.autocomplete(equipe=equipe_autocomplete)
    @app_commands.checks.has_role("ADM")
    async def remover_responsavel(self, interaction: discord.Interaction, equipe: str):
        equipe_id = int(equipe)
        success = await remover_responsavel(equipe_id)
        if success:
            await interaction.response.send_message(f"✅ Responsável da equipe selecionada foi removido.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erro ao remover responsável.", ephemeral=True)

    @app_commands.command(name="listar-responsaveis", description="[Admin] Lista equipes com e sem responsável definido.")
    @app_commands.checks.has_role("ADM")
    async def listar_responsaveis(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Busca os mapeamentos do nosso banco e as equipes do banco corporativo
        mapeamentos = await listar_todos_responsaveis()
        todas_as_equipes = self.portal_db.buscar_todas_equipes()

        mapa_responsaveis = {map['equipe_id']: map['responsavel_discord_id'] for map in mapeamentos}
        
        equipes_mapeadas = []
        equipes_sem_responsavel = []

        for equipe in todas_as_equipes:
            if equipe['id'] in mapa_responsaveis:
                responsavel_id = mapa_responsaveis[equipe['id']]
                equipes_mapeadas.append(f"**{equipe['descricao']}**: <@{responsavel_id}>")
            else:
                equipes_sem_responsavel.append(f"• {equipe['descricao']} (ID: {equipe['id']})")
        
        embed = discord.Embed(title="Mapeamento de Responsáveis por Equipe", color=discord.Color.blue())
        
        if equipes_mapeadas:
            embed.add_field(name="✅ Equipes com Responsável Definido", value="\n".join(equipes_mapeadas), inline=False)
        else:
            embed.add_field(name="✅ Equipes com Responsável Definido", value="Nenhuma equipe mapeada.", inline=False)
            
        if equipes_sem_responsavel:
            embed.add_field(name="⚠️ Equipes SEM Responsável (Pendentes)", value="\n".join(equipes_sem_responsavel), inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GerenciamentoCommands(bot))
    logger.info("Cog 'GerenciamentoCommands' carregado com sucesso.")