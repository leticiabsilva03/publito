# 🤖 Publito 🤖

## 🎯 Visão Geral

O Publito é um assistente virtual multifuncional para Discord, projetado para otimizar e automatizar processos internos de uma empresa. A aplicação visa centralizar operações críticas, como a gestão de credenciais de sistemas (SICOM) e processos de Recursos Humanos (Banco de Horas), numa plataforma segura, auditável e de fácil acesso para os colaboradores.

O projeto resolve o problema da descentralização de informações e da falta de padronização em processos manuais, oferecendo uma interface de utilizador moderna e intuitiva através de comandos de barra (/) e componentes interativos do Discord.

## 🚀 Recursos Principais

* **Gestão de Credenciais SICOM:**

  * Consulta, atualização e histórico de credenciais por município
  * Controle de acesso baseado em **cargos** do Discord

* **Formulário de Banco de Horas:**

  * Fluxo completo para submissão de horas extras
  * Geração de relatório em **PDF** e envio por **e-mail**

* **Arquitetura Modular (MVC):**

  * Estrutura baseada em Model-View-Controller para facilitar manutenção e expansão

* **Segurança:**

  * Permissões por cargo, logging e tratamento robusto de erros

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
/publito/
├── cogs/                 # CONTROLLERS: Lógica dos comandos e orquestração do fluxo.
│   ├── sicom_commands.py
│   ├── hr_commands.py
│   └── error_handler.py
├── database/             # MODEL: Tudo relacionado à persistência e acesso aos dados.
│   ├── carga_dados.py
│   ├── db_manager.py
│   ├── init_db.py
│   ├── insert_schema.sql
│   ├── models.py
│   ├── queries.py
│   └── schema.sql
├── services/             # SERVICES: Lógica de negócio complexa e isolada.
│   ├── email_service.py
│   └── pdf_service.py
├── utils/                # UTILS: Funções auxiliares puras e reutilizáveis.
│   └── helpers.py
├── views/                # VIEWS: Componentes de interface do Discord (Modais, Botões, Embeds).
│   ├── hr_views.py
│   └── sicom_views.py
├── tests/                # SUÍTE DE TESTES: Testes unitários e de integração.
│   ├── test_unit/
│   └── test_integration/
├── .env                  # Configurações de ambiente e segredos.
├── main.py               # Ponto de entrada e orquestrador da aplicação.
├── requirements.txt      # Dependências do projeto.
└── README.md             # Documentação.
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
4. Configurar o Banco de Dados

   ```sql
   CREATE DATABASE publito;
   \c publito
   CREATE SCHEMA sicom;
   ```
5. Defina as variáveis de ambiente no arquivo `.env`:

   ```dotenv
   DISCORD_TOKEN=SEU_TOKEN_DO_DISCORD
   DATABASE_URL=postgres://USUARIO:SENHA@HOST:PORTA/DB_NAME
   GUILD_ID=ID_DO_SERVIDOR

   EMAIL_HOST=smtp
   EMAIL_PORT=port
   EMAIL_USER=seu_email@empresa.com
   EMAIL_PASSWORD="sua#senha#aqui"
   EMAIL_RECIPIENT=rh@empresa.com
   ```

## ▶️ Uso

Inicie o bot:

```bash
python main.py
```

Aguarde as mensagens de log confirmando a conexão ao Discord e ao banco.

## 🤝 Contribuição

Atualmente, o projeto é mantido por uma equipa interna. Para contribuir, por favor, siga as diretrizes abaixo:

1. Faça um fork deste repositório
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Realize commits claros e atômicos
4. Envie um Pull Request descrevendo sua alteração

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

## 🚪 Contato e Suporte

Para dúvidas, sugestões ou bugs, contate a equipe de desenvolvimento via canais internos da empresa.

---

> Desenvolvido com ❤ por Letícia B. Silva e Pedro Ventura.
