# 🤖 Publito 🤖

## 🎯 Visão Geral

Bot do Discord para gestão de credenciais do SICOM, com foco em envio de credenciais via DM, registro de histórico de alterações e integração com banco de dados PostgreSQL.

## 🚀 Recursos Principais

* **Consulta Segura de Credenciais:** Transmissão de acessos via DM
* **Atualização e Inserção de Credenciais:** Administração dos dados no banco
* **Histórico de Alterações:** Log de modificações de credenciais
* **Comandos Modulares:** Estrutura em Cogs para fácil expansão
* **Banco de Dados:** Gerenciamento com PostgreSQL e SQLAlchemy

## 🛠️ Tecnologias

* **Python 3.11+**
* **discord.py**
* **asyncpg**
* **python-dotenv**
* **SQLAlchemy**
* **Unidecode**
* **PostgreSQL**

## 📁 Estrutura do Projeto

```
publito/
├── cogs/
│   ├── sicom_commands.py     # Comandos principais
│   └── error_handler.py      # Tratamento de erros
├── database/
│   ├── db_manager.py         # Conexão e sessão
│   ├── init_db.py            # Inicialização do esquema
│   ├── insert_schema.sql     # Dados iniciais
│   ├── models.py             # Definição de tabelas
│   ├── queries.py            # Consultas SQL
│   └── schema.sql            # Esquema inicial
├── logs/
│   └── bot.log               # Arquivo de logs
├── .env                      # Variáveis de ambiente
├── main.py                   # Ponto de entrada
├── requirements.txt          # Dependências
└── README.md                 # Documentação
```

## ⚙️ Configuração

1. Clone o repositório:

   ```bash
   git clone https://github.com/leticiabsilva03/publito.git
   cd publito
   ```
2. Crie e ative um ambiente virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .\.venv\Scripts\activate   # Windows
   ```
3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```
4. Defina as variáveis de ambiente no arquivo `.env`:

   ```dotenv
   DISCORD_TOKEN=SEU_TOKEN_DO_DISCORD
   DATABASE_URL=postgres://USUARIO:SENHA@HOST:PORTA/DB_NAME
   GUILD_ID=ID_DO_SERVIDOR
   ```

## ▶️ Uso

Inicie o bot:

```bash
python main.py
```

Aguarde as mensagens de log confirmando a conexão ao Discord e ao banco.

## 🤝 Contribuição

1. Faça um fork deste repositório
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Realize commits claros e atômicos
4. Envie um Pull Request descrevendo sua alteração

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
