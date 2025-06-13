"""Initializes the database schema for the Publito application."""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def run_schema_script():
    """Executa o script de criação do schema no banco de dados."""
    # Conecta ao banco usando asyncpg
    conn = await asyncpg.connect(dsn=DATABASE_URL)

    # Lê e executa o conteúdo do arquivo schema.sql
    with open("./database/schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()
        await conn.execute(schema_sql)

    await conn.close()
    print("Schema criado com sucesso.")

if __name__ == "__main__":
    asyncio.run(run_schema_script())
