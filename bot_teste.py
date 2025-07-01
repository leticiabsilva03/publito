import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém o token da variável de ambiente 'DISCORD_BOT_TOKEN'
TOKEN = os.getenv('DISCORD_TOKEN')

# ID do servidor para testes rápidos
guild_id = os.getenv('DISCORD_GUILD_ID')
GUILD = discord.Object(id=guild_id)

# Define as intents
intents = discord.Intents.default()
intents.message_content = True

# Cria a instância do bot
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot logado como: {bot.user} (ID: {bot.user.id})')
    print('Conectado aos seguintes servidores:')
    for guild in bot.guilds:
        print(f'- {guild.name} (ID: {guild.id})')
    print('--- Conexão Básica Estabelecida! ---')
    print('Comandos de barra (slash commands) prontos para sincronização.')

# Comando de barra (slash) para responder com Pong!
@bot.tree.command(name="ping", description="Responde com Pong! e uma mensagem divertida.", guilds=[GUILD])
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! 🏓 O bot está online e respondendo, {interaction.user.mention}!")

# Comando para sincronizar os comandos de barra com o Discord
@bot.command()
@commands.is_owner()
async def sync(ctx: commands.Context):
    await bot.tree.sync(guild=GUILD)
    await ctx.send("Comandos de barra sincronizados com sucesso!")
    print("Comandos de barra sincronizados no servidor de teste!")

# Inicia o bot
bot.run(TOKEN)
