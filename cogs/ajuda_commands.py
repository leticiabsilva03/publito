import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import List

logger = logging.getLogger(__name__)

# --- Ícones por categoria ---
CATEGORY_ICONS = {
    "comunicados": "📰",
    "rh": "👥",
    "gerenciamento": "🛠",
    "sicom": "🏛",
    "outros": "📌"
}

# --- Links para o fórum ---
FORUM_LINKS = {
    # Comunicados
    #"comunicados": "https://discord.com/channels/<server_id>/<forum_id>/<topic_id_comunicados>",

    # RH
    #"bancohoras": "https://discord.com/channels/<server_id>/<forum_id>/<topic_id_bancohoras>",

    # Gerenciamento
    #"definir-responsavel": "https://discord.com/channels/<server_id>/<forum_id>/<topic_id_definir_responsavel>",
    #"remover-responsavel": "https://discord.com/channels/<server_id>/<forum_id>/<topic_id_remover_responsavel>",
    #"listar-responsaveis": "https://discord.com/channels/<server_id>/<forum_id>/<topic_id_listar_responsaveis>",

    # SICOM
    "sicom": "https://discord.com/channels/1381727746383679628/1404091914059251723",
    # "atualizasicom": "https://discord.com/channels/<server_id>/<forum_id>/<topic_id_atualizasicom>",
    # "registramunicipio": "https://discord.com/channels/<server_id>/<forum_id>/<topic_id_registramunicipio>",
    # "registrasicom": "https://discord.com/channels/<server_id>/<forum_id>/<topic_id_registrasicom>",

    # Utilidade
    # "ajuda": "https://discord.com/channels/<server_id>/<forum_id>/<topic_id_ajuda>"
}


class AjudaCommands(commands.Cog):
    """Comando /ajuda que mostra apenas comandos permitidos ao usuário."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def user_can_use_command(self, cmd: app_commands.Command, user: discord.Member) -> bool:
        """
        Checa se o usuário atende aos checks do comando.
        Suporta has_role e has_permissions nativos do discord.py.
        """
        for check in cmd.checks:
            qualname = getattr(check, "__qualname__", "").lower()

            # Check de cargo
            if "has_role" in qualname:
                required_role = check.__closure__[0].cell_contents
                if all(r.name != required_role for r in user.roles):
                    return False

            # Check de permissões
            elif "has_permissions" in qualname:
                required_perms = check.__closure__[0].cell_contents
                for perm, value in required_perms.items():
                    if getattr(user.guild_permissions, perm) != value:
                        return False

        return True

    @app_commands.command(name="ajuda", description="Exibe informações e links para tutoriais de comandos disponíveis para você.")
    async def ajuda(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        comandos = sorted(self.bot.tree.get_commands(), key=lambda c: c.name.lower())
        categorias = {}

        # Filtra comandos pelo que o usuário realmente pode usar
        for cmd in comandos:
            if await self.user_can_use_command(cmd, interaction.user):
                categoria = cmd.callback.__module__.split(".")[1] if "." in cmd.callback.__module__ else "outros"
                categorias.setdefault(categoria, []).append(cmd)

        # Envia um embed por categoria
        for categoria, cmds in categorias.items():
            icon = CATEGORY_ICONS.get(categoria.lower(), "📌")
            embed = discord.Embed(
                title=f"{icon} Ajuda - {categoria.capitalize()}",
                description="Lista de comandos desta categoria que você pode usar:",
                color=discord.Color.blurple()
            )

            view = discord.ui.View()

            for cmd in cmds:
                parametros = []
                if cmd._params:
                    for param in cmd._params:
                        parametros.append(f"<{param}>")
                else:
                    parametros = [""]
                parametros_str = " " + " ".join(parametros)

                
                exemplo = f"`/{cmd.name}` {parametros_str}" if parametros else f"`/{cmd.name}`"
                embed.add_field(
                    name=f"/{cmd.name}",
                    value=f"{cmd.description or 'Sem descrição'}\n**Exemplo:** {exemplo}",
                    inline=False
                )

                link = FORUM_LINKS.get(cmd.name)
                if link:
                    view.add_item(
                        discord.ui.Button(label=f"📖 {cmd.name}", url=link)
                    )

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AjudaCommands(bot))
    logger.info("Cog 'AjudaCommands' carregado com sucesso.")
