# Conexão e operações com o PostgreSQL

import asyncpg
import os
from dotenv import load_dotenv

load_dotenv() # Carrega variáveis de ambiente do arquivo.env

async def connect_db():
    return await asyncpg.create_pool(
        database=os.getenv("db_name"),
        user=os.getenv("db_user"),
        password=os.getenv("db_password"),
        host=os.getenv("db_host"),
        port=os.getenv("db_port"),
        min_size=1,
        max_size=100
    )