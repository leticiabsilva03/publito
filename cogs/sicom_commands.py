# cogs/sicom_commands.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
import unidecode
import re

# Importando da camada de Modelo (database)
from database.queries import (
    fetch_municipio_autocomplete, 
    fetch_credenciais_por_id,
    fetch_administracao_autocomplete,
    busca_entidade_id,
    update_credenciais,
    insert_municipio,
    create_municipio_administracao_link,
    check_credencial,
    insert_credencial
)
# Importando da camada de Visão
from views.sicom_views import create_credentials_embed

logger = logging.getLogger(__name__)

class SicomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _formatar_e_validar_nome(self, nome: str) -> str:
        nome_sem_acento = unidecode.unidecode(nome)
        if not re.match(r"^[A-Za-z\s]+$", nome_sem_acento):
    
        # Adiciona .strip() para remover espaços no início e no fim
        nome_limpo = nome_sem_acento.strip()
    
        if not re.match(r"^[A-Za-z\s]+$", nome_limpo):
            raise ValueError("O nome do município deve conter apenas letras e espaços.")
        return nome_sem_acento.title()
        
        return nome_limpo.title()

    # --- AUTOCOMPLETES ---
    async def municipio_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        municipios = await fetch_municipio_autocomplete(current)
        return [app_commands.Choice(name=mun["nom_municipio"], value=str(mun["cod_municipio"])) for mun in municipios]

    async def administracao_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        administracoes = await fetch_administracao_autocomplete(current)
        return [app_commands.Choice(name=f'{adm["sigla_administracao"]} - {adm["des_administracao"] or "Sem descrição"}', value=str(adm["cod_administracao"])) for adm in administracoes]

    # --- COMANDO /sicom ---
    @app_commands.command(name="sicom", description="Consulta as credenciais de um município.")
    @app_commands.autocomplete(municipio=municipio_autocomplete)
    @app_commands.describe(municipio="Comece a digitar o nome do município para ver as opções.")
    async def sicom(self, interaction: discord.Interaction, municipio: str):
        await interaction.response.defer(ephemeral=True)
        
        municipio_id = int(municipio)
        results = await fetch_credenciais_por_id(municipio_id)

        if not results:
            await interaction.followup.send("Nenhuma credencial encontrada para este município.", ephemeral=True)
            return
        
        # Chama a função da camada de Visão para criar o embed
        embed = create_credentials_embed(results)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    # --- COMANDO /atualizasicom ---
    @app_commands.command(name="atualizasicom", description="Atualiza as credenciais de uma entidade.")
    @app_commands.checks.has_role("Administrador SICOM")
    @app_commands.autocomplete(municipio=municipio_autocomplete, administracao=administracao_autocomplete)
    @app_commands.describe(
        municipio="O município da credencial a ser atualizada.",
        administracao="A administração (PM, CM, etc.) da credencial.",
        novo_cpf="O novo CPF do usuário (11 dígitos, sem pontos ou traços).",
        nova_senha="A nova senha de acesso.",
        nova_validade="O novo status de validade da credencial (True ou False)."
    )
    async def atualizasicom(
        self, interaction: discord.Interaction, municipio: str, administracao: str,
        novo_cpf: Optional[str] = None, nova_senha: Optional[str] = None, nova_validade: Optional[bool] = None
    ):
        await interaction.response.defer(ephemeral=True)

        if all(arg is None for arg in [novo_cpf, nova_senha, nova_validade]):
            await interaction.followup.send("❌ Você precisa fornecer pelo menos um campo para atualizar.", ephemeral=True)
            return
        if novo_cpf and (not novo_cpf.isdigit() or len(novo_cpf) != 11):
            await interaction.followup.send("❌ O CPF deve conter exatamente 11 dígitos numéricos.", ephemeral=True)
            return

        municipio_id = int(municipio)
        administracao_id = int(administracao)
        entity_id = await busca_entidade_id(municipio_id, administracao_id)
        
        if not entity_id:
            await interaction.followup.send("❌ Não foi encontrada uma entidade para a combinação informada.", ephemeral=True)
            return
            
        updates_to_perform = {k: v for k, v in {"cpf_usuario": novo_cpf, "senha": nova_senha, "status_validade": nova_validade}.items() if v is not None}
        
        success = await update_credenciais(entity_id, updates_to_perform)
        
        if success:
            embed = discord.Embed(title="✅ Sucesso!", description="As credenciais foram atualizadas.", color=discord.Color.green())
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("❌ Ocorreu um erro ao atualizar as credenciais.", ephemeral=True)

    # --- Outros comandos (/registramunicipio, /registrasicom) continuariam aqui... ---
    # O código deles já está bem alinhado com o padrão, pois já chamam a camada de queries.
    # Por brevidade, o restante do código é omitido, mas a estrutura permanece.


async def setup(bot: commands.Bot):
    await bot.add_cog(SicomCommands(bot))
    logger.info("Cog 'SicomCommands' carregado com sucesso.")