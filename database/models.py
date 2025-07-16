# database/models.py
import sqlalchemy

# O 'metadata' é um objeto que armazena todas as informações sobre as nossas tabelas.
metadata = sqlalchemy.MetaData()

# Definição da tabela 'municipios', especificando o schema 'sicom'.
municipios = sqlalchemy.Table(
    "municipios",
    metadata,
    sqlalchemy.Column("cod_municipio", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("nom_municipio", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("cnpj_municipio", sqlalchemy.String(14), nullable=False, unique=True),
    schema="sicom"
)

# Definição da tabela 'administracoes'
administracoes = sqlalchemy.Table(
    "administracoes",
    metadata,
    sqlalchemy.Column("cod_administracao", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("sigla_administracao", sqlalchemy.String(10), nullable=False, unique=True),
    sqlalchemy.Column("des_administracao", sqlalchemy.Text),
    schema="sicom"
)

# Definição da tabela de junção 'municipios_administracoes'
municipios_administracoes = sqlalchemy.Table(
    "municipios_administracoes",
    metadata,
    sqlalchemy.Column("cod_entidade", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("cod_municipio", sqlalchemy.Integer, sqlalchemy.ForeignKey("sicom.municipios.cod_municipio"), nullable=False),
    sqlalchemy.Column("cod_administracao", sqlalchemy.Integer, sqlalchemy.ForeignKey("sicom.administracoes.cod_administracao"), nullable=False),
    schema="sicom"
)

# Definição da tabela 'credenciais'
credenciais = sqlalchemy.Table(
    "credenciais",
    metadata,
    sqlalchemy.Column("cod_credencial", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("cod_entidade", sqlalchemy.Integer, sqlalchemy.ForeignKey("sicom.municipios_administracoes.cod_entidade"), nullable=False),
    sqlalchemy.Column("cpf_usuario", sqlalchemy.String(11)),
    sqlalchemy.Column("senha", sqlalchemy.String),
    sqlalchemy.Column("data_atualizacao", sqlalchemy.Date, nullable=False),
    sqlalchemy.Column("status_validade", sqlalchemy.Boolean, nullable=False, default=False),
    schema="sicom"
)

comunicados = sqlalchemy.Table(
    "comunicados",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("url", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("titulo_comunicado", sqlalchemy.String),
    sqlalchemy.Column("data_postagem", sqlalchemy.DateTime),
    sqlalchemy.Column("data_postagem_discord", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
    schema="sicom"
)
