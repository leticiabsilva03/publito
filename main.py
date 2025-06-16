# main.py
import os
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv

from database.db_manager import database

# --- Configuração de Logging ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Carregar Variáveis de Ambiente ---
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    logger.critical("TOKEN DO DISCORD NÃO ENCONTRADO! Verifique seu arquivo .env")
    exit()

# --- Definição do Bot ---
intents = discord.Intents.default()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        logger.info("--- Executando setup_hook ---")
        
        # 1. Conectar ao banco de dados
        try:
            await database.connect()
            logger.info("Conexão com o banco de dados estabelecida.")
        except Exception as e:
            logger.critical(f"Falha ao conectar ao banco de dados: {e}", exc_info=True)
            return
            
        # 2. Carregar Cogs (extensões com comandos)
        cogs_to_load = [
            'cogs.sicom_commands'
            #,'cogs.error_handler' 
        ]
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog '{cog}' carregado com sucesso.")
            except Exception as e:
                logger.error(f"Falha ao carregar o cog '{cog}': {e}", exc_info=True)
            
        # 3. Sincronizar comandos com o Discord
        try:
            synced = await self.tree.sync()
            logger.info(f"{len(synced)} comando(s) sincronizado(s) globalmente.")
        except Exception as e:
            logger.error(f"Falha ao sincronizar comandos: {e}", exc_info=True)

    async def on_ready(self):
        logger.info(f'Bot conectado como {self.user.name} (ID: {self.user.id})')

    async def close(self):
        logger.info("Fechando a conexão com o banco de dados...")
        await database.disconnect()
        await super().close()

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    bot = MyBot()
    bot.run(DISCORD_TOKEN)
