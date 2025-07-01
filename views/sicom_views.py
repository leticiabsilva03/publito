
# views/sicom_views.py
import discord
from typing import List, Dict

def create_credentials_embed(results: List[Dict]) -> discord.Embed:
    """Cria e retorna o embed de credenciais para o comando /sicom."""
    if not results:
        # Embora o controlador já verifique, é uma boa prática ter um fallback.
        return discord.Embed(
            title="Nenhuma Credencial Encontrada",
            description="Não foram encontradas credenciais para o município selecionado.",
            color=discord.Color.orange()
        )

    municipio_nome = results[0]["municipio_nome"]
    embed = discord.Embed(
        title=f"🔑 Credenciais de {municipio_nome}",
        description=f"Encontradas {len(results)} credencial(is).",
        color=discord.Color.blue()
    )

    for cred in results:
        field_value = (
            f"**Usuário (CPF):** `{cred['cpf_usuario'] or 'Não informado'}`\n"
            f"**Senha:** `{cred['senha'] or 'Não informada'}`"
        )
        field_name = f"🏢 {cred['adm_sigla']} ({cred['adm_descricao'] or 'Sem descrição'})"
        embed.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
    
    embed.set_footer(text="Informação confidencial. Use com responsabilidade para não ser preso 👀.")
    return embed