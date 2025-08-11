# db_manager.py

import os
from databases import Database
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Pega a URL de conexão do ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

# Verifica se a URL foi encontrada. Se não, o programa não deve continuar.
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não foi encontrada no arquivo .env")

# Cria uma instância global do objeto Database.
# Esta é a única instância que será usada em todo o projeto.
# Outros arquivos (como queries.py e main.py) irão importar esta variável 'database'.
database = Database(DATABASE_URL)