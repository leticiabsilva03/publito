import discord
from discord import app_commands
from discord.ext import commands
import logging

# Importa as funções de query atualizadas
from database.queries import fetch_municipio_autocomplete, fetch_credenciais_por_id

logger = logging.getLogger(__name__)

class SicomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Função de autocomplete para a opção 'municipio' do comando /sicom
    async def municipio_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        municipio = await fetch_municipio_autocomplete(current)
        # Usa as colunas corretas ('nom_municipio', 'cod_municipio') retornadas pela query
        return [
            app_commands.Choice(name=mun["nom_municipio"], value=str(mun["cod_municipio"]))
            for mun in municipio
        ]

    @app_commands.command(name="sicom", description="Consulta as credenciais de um município.")
    @app_commands.autocomplete(municipio=municipio_autocomplete)
    @app_commands.describe(municipio="Comece a digitar o nome do município para ver as opções.")
    async def sicom(self, interaction: discord.Interaction, municipio: str):
        try:
            await interaction.response.defer(ephemeral=True)
            municipio_id = int(municipio)
            results = await fetch_credenciais_por_id (municipio_id)

            if not results:
                await interaction.followup.send("Nenhuma credencial encontrada para este município.", ephemeral=True)
                return
            
            # Usa os nomes de colunas corretos retornados pela query
            municipio_nome = results[0]["municipio_nome"]
            embed = discord.Embed(
                title=f"🔑 Credenciais de {municipio_nome}",
                description=f"Encontradas {len(results)} credencial(is).",
                color=discord.Color.blue()
            )

            for cred in results:
                # Usa as colunas corretas: cpf_usuario e senha
                field_value = (
                    f"**Usuário (CPF):** `{cred['cpf_usuario'] or 'Não informado'}`\n"
                    f"**Senha:** `{cred['senha'] or 'Não informada'}`"
                )
                # Usa a sigla e a descrição da administração para o nome do campo
                field_name = f"🏢 {cred['adm_sigla']} ({cred['adm_descricao'] or 'Sem descrição'})"
                embed.add_field(
                    name=field_name,
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text="Informação confidencial. Use com responsabilidade.")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Erro inesperado no comando /sicom: {e}", exc_info=True)
            await interaction.followup.send("Ocorreu um erro ao processar sua solicitação.", ephemeral=True)

# Função obrigatória que o bot chama para registrar o Cog
async def setup(bot: commands.Bot):
    await bot.add_cog(SicomCommands(bot))
    logger.info("Cog 'SicomCommands' carregado com sucesso.")
