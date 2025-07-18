# views/comunicado_sicom_views.py
import discord
from typing import Dict

def insere_comunicado_embed(comunicado: Dict) -> discord.Embed:
    """Cria um embed do Discord para um único comunicado."""

    # O título agora é o link, e o rodapé contém a data.
    embed = discord.Embed(
        title=f"📢 {comunicado['titulo_comunicado']}",
        url=comunicado['link'],
        description=comunicado['resumo'], # A descrição contém apenas o resumo
        color=discord.Color.blue()
    )
    # A data de publicação foi movida para o rodapé para um visual mais limpo.
    embed.set_footer(text=f"Publicado em: {comunicado['data_comunicado']}")
    return embed
