# Publito

## Visão Geral

Bot do Discord para gestão de credenciais do SICOM, com foco em envio de senhas via DM, registro de histórico de alterações e integração com banco de dados PostgreSQL.

## Tecnologias Utilizadas

* Python 3.11+
* discord.py
* asyncpg
* python-dotenv
* PostgreSQL

## Estrutura

```
sicom_bot/
├── cogs/
│   ├── sicom_commands.py
│   └── error_handler.py
├── database/
│   ├── db_manager.py
│   ├── schema.sql
├── logs/
│   └── bot.log
├── .env
├── main.py
├── requirements.txt
└── README.md
```

## Licença

MIT
