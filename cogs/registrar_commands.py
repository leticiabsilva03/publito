import discord
from discord import app_commands
from discord.ext import commands
import logging
from database import bot_queries
from services.portal_service import PortalDatabaseService

logger = logging.getLogger(__name__)

class RegistroColaboradorModal(discord.ui.Modal, title="Quem é que tá aí? 🧐"):
    cpf = discord.ui.TextInput(
        label="Não te conheço... Qual seu CPF?",
        placeholder="CPF (sem pontos ou traços) para vincular ao seu Discord ID",
        required=True,
        max_length=11,
        min_length=11       
    )

    def __init__(self, user: discord.Member):
        super().__init__()
        self.user = user
        self.portal = PortalDatabaseService()

    async def on_submit(self, interaction: discord.Interaction):
        cpf_str = str(self.cpf.value).strip()

        try:
            # 1️⃣ Verifica no banco do bot
            colaborador_bot = await bot_queries.buscar_colaborador_mapeado(self.user.id)
            if colaborador_bot:
                await interaction.response.send_message(
                    f"⚠️ Ué, esqueceu que já nos conhecemos? Ou vc não é {colaborador_bot.get('nome')}? 😵‍💫\n\n"
                    f"Se não for vc... NÃO ENTRE EM PÂNICO!!! Um administrador pode te ajudar (eu espero).",
                    ephemeral=True
                )
                return

            # 2️⃣ Busca no portal corporativo
            colaborador_portal = self.portal.buscar_colaborador_por_cpf(cpf_str)
            if not colaborador_portal:
                await interaction.response.send_message(
                    "❌ CPF não encontrado no portal corporativo. Verifique e tente novamente.",
                    ephemeral=True
                )
                return

            # 3️⃣ Registra no banco do bot
            await bot_queries.salvar_mapeamento(
                discord_id=self.user.id,
                colaborador_id=colaborador_portal["colaborador_id"],
                matricula=colaborador_portal["matricula"],
                nome = colaborador_portal["nome"]
            )

            # Primeira resposta é aqui ✅
            await interaction.response.send_message(
                f"✅ Ah, então era vc?! Prontinho! CPF **{cpf_str}** vinculado ao seu Discord. Não vou me esquecer agora. ♾️",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Erro ao registrar colaborador: {e}", exc_info=True)
            # se deu erro depois da primeira resposta, usa followup
            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ Ocorreu um erro ao finalizar seu registro. Contate o administrador.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Ocorreu um erro ao processar seu registro. Contate o administrador.",
                    ephemeral=True
                )


class RegistrarCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="registrar", description="Vincula seu CPF ao seu usuário do Discord.")
    async def registrar(self, interaction: discord.Interaction):
        modal = RegistroColaboradorModal(user=interaction.user)
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(RegistrarCommands(bot))
    logger.info("Cog 'RegistrarCommands' carregado com sucesso.")
