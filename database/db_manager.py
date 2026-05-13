import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Captura as variáveis
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "1234") # Ajuste conforme seu ambiente
DB_NAME = os.getenv("DB_NAME")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

# Validação básica
if not all([DB_USER, DB_NAME]):
    raise ValueError("Variáveis de banco de dados incompletas no arquivo .env")

# Codificação para URL (trata caracteres especiais na senha e user)
encoded_user = quote_plus(DB_USER)
encoded_password = quote_plus(DB_PASSWORD)
encoded_driver = quote_plus(DB_DRIVER)

# Montagem da URL usando aioodbc para suporte assíncrono
DATABASE_URL = f"mssql+aioodbc://{encoded_user}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?driver={encoded_driver}&TrustServerCertificate=yes&Encrypt=no"

class DatabaseAdapter:
    """
    Adaptador para emular o comportamento da biblioteca 'databases'
    usando SQLAlchemy 2.0 assíncrono.
    """
    def __init__(self, url):
        self.engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
        )
        self.session_factory = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def connect(self):
        # Mantido para compatibilidade de interface, o SQLAlchemy gerencia o pool automaticamente
        pass

    async def disconnect(self):
        await self.engine.dispose()

    async def fetch_all(self, query, values=None):
        async with self.engine.connect() as conn:
            # Se a query não for uma string (for um objeto select), 
            # o execute() do SQLAlchemy já sabe lidar, mas o text() não deve ser usado.
            if isinstance(query, str):
                query = text(query)
                
            result = await conn.execute(query, values or {})
            return [dict(row._mapping) for row in result]

    async def fetch_one(self, query, values=None):
        async with self.engine.connect() as conn:
            # Se for uma string pura, envolvemos em text()
            # Se for um objeto select(), o SQLAlchemy executa diretamente
            if isinstance(query, str):
                query = text(query)
            
            result = await conn.execute(query, values or {})
            row = result.first()
            
            # Retorna um dicionário (como a biblioteca 'databases' fazia)
            return dict(row._mapping) if row else None

    async def execute(self, query, values=None):
        # Usamos engine.begin() para garantir o commit automático ao final do bloco
        async with self.engine.begin() as conn:
            if isinstance(query, str):
                query = text(query)
            
            await conn.execute(query, values or {})

# Cria a instância global que será importada pelo resto do projeto
# O nome da variável continua sendo 'database' para não quebrar seus outros arquivos
database = DatabaseAdapter(DATABASE_URL)