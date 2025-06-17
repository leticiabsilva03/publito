import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
import re
import unidecode

# Importa as funções de query atualizadas
from database.queries import (
    fetch_municipio_autocomplete, 
    fetch_credenciais_por_id,
    fetch_administracao_autocomplete,
    busca_entidade_id,
    update_credenciais,
    insert_municipio,
    create_municipio_administracao_link,
    check_credencial,
    insert_credencial
)

logger = logging.getLogger(__name__)

class SicomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- FUNÇÃO AUXILIAR DE FORMATAÇÃO ---
    def _formatar_e_validar_nome(self, nome: str) -> str:
        """
        Formata o nome do município e valida suas regras.
        - Remove acentos.
        - Converte para Title Case (Primeiras Letras Maiúsculas).
        - Verifica se contém números.
        Retorna o nome formatado ou levanta um ValueError se for inválido.
        """
        # Remove acentos (ex: "São Paulo" -> "Sao Paulo")
        nome_sem_acento = unidecode.unidecode(nome)
        
        # Verifica se o nome sem acento contém apenas letras e espaços
        if not re.match(r"^[A-Za-z\s]+$", nome_sem_acento):
            raise ValueError("O nome do município deve conter apenas letras e espaços.")
            
        # Converte para "Title Case" (ex: "sao paulo" -> "Sao Paulo")
        return nome_sem_acento.title()

    # Função de autocomplete para a opção 'municipio' do comando /sicom
    async def municipio_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        municipio = await fetch_municipio_autocomplete(current)
        # Usa as colunas corretas ('nom_municipio', 'cod_municipio') retornadas pela query
        return [
            app_commands.Choice(name=mun["nom_municipio"], value=str(mun["cod_municipio"]))
            for mun in municipio
        ]

    @app_commands.command(name="sicom", description="Consulta as credenciais de um município.")
    @app_commands.autocomplete(municipio=municipio_autocomplete)
    @app_commands.describe(municipio="Comece a digitar o nome do município para ver as opções.")
    async def sicom(self, interaction: discord.Interaction, municipio: str):
        try:
            await interaction.response.defer(ephemeral=True)
            municipio_id = int(municipio)
            results = await fetch_credenciais_por_id (municipio_id)

            if not results:
                await interaction.followup.send("Nenhuma credencial encontrada para este município.", ephemeral=True)
                return
            
            # Usa os nomes de colunas corretos retornados pela query
            municipio_nome = results[0]["municipio_nome"]
            embed = discord.Embed(
                title=f"🔑 Credenciais de {municipio_nome}",
                description=f"Encontradas {len(results)} credencial(is).",
                color=discord.Color.blue()
            )

            for cred in results:
                # Usa as colunas corretas: cpf_usuario e senha
                field_value = (
                    f"**Usuário (CPF):** `{cred['cpf_usuario'] or 'Não informado'}`\n"
                    f"**Senha:** `{cred['senha'] or 'Não informada'}`"
                )
                # Usa a sigla e a descrição da administração para o nome do campo
                field_name = f"🏢 {cred['adm_sigla']} ({cred['adm_descricao'] or 'Sem descrição'})"
                embed.add_field(
                    name=field_name,
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text="Informação confidencial. Use com responsabilidade para não ser preso 👀.")
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Erro inesperado no comando /sicom: {e}", exc_info=True)
            await interaction.followup.send("Ocorreu um erro ao processar sua solicitação.", ephemeral=True)

    # --- AUTOCOMPLETE PARA /atualizasicom ---
    async def administracao_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        administracoes = await fetch_administracao_autocomplete(current)
        # Formata a escolha para ser mais descritiva, mostrando a sigla e a descrição.
        return [
            app_commands.Choice(
                name=f'{adm["sigla_administracao"]} - {adm["des_administracao"] or "Sem descrição"}', 
                value=str(adm["cod_administracao"])
            )
            for adm in administracoes
        ]
        
    # --- COMANDO /atualizasicom ---
    @app_commands.command(name="atualizasicom", description="Atualiza as credenciais de uma entidade.")
    @app_commands.checks.has_role("Administrador SICOM") # Verificação de permissão
    @app_commands.autocomplete(municipio=municipio_autocomplete, administracao=administracao_autocomplete)
    @app_commands.describe(
        municipio="O município da credencial a ser atualizada.",
        administracao="A administração (PM, CM, etc.) da credencial.",
        novo_cpf="O novo CPF do usuário (11 dígitos, sem pontos ou traços).",
        nova_senha="A nova senha de acesso.",
        nova_validade="O novo status de validade da credencial (True ou False)."
    )
    async def atualizasicom(
        self, 
        interaction: discord.Interaction,
        municipio: str,
        administracao: str,
        novo_cpf: Optional[str] = None,
        nova_senha: Optional[str] = None,
        nova_validade: Optional[bool] = None
    ):
        await interaction.response.defer(ephemeral=True)

        # 1. Validar inputs
        if all(arg is None for arg in [novo_cpf, nova_senha, nova_validade]):
            await interaction.followup.send("❌ Você precisa fornecer pelo menos um campo para atualizar (novo_cpf, nova_senha ou nova_validade).", ephemeral=True)
            return
            
        if novo_cpf and (not novo_cpf.isdigit() or len(novo_cpf) != 11):
            await interaction.followup.send("❌ O CPF deve conter exatamente 11 dígitos numéricos.", ephemeral=True)
            return

        # 2. Encontrar a entidade no banco
        municipio_id = int(municipio)
        administracao_id = int(administracao)
        entity_id = await busca_entidade_id(municipio_id, administracao_id)
        
        if not entity_id:
            await interaction.followup.send("❌ Não foi encontrada uma entidade para a combinação de município e administração informada.", ephemeral=True)
            return
            
        # 3. Construir o dicionário de atualizações
        updates_to_perform = {}
        if novo_cpf is not None:
            updates_to_perform["cpf_usuario"] = novo_cpf
        if nova_senha is not None:
            updates_to_perform["senha"] = nova_senha
        if nova_validade is not None:
            updates_to_perform["status_validade"] = nova_validade
            
        # 4. Executar o UPDATE
        success = await update_credenciais(entity_id, updates_to_perform)
        
        # 5. Enviar feedback ao usuário
        if success:
            embed = discord.Embed(
                title="✅ Sucesso!",
                description=f"As credenciais para a entidade selecionada foram atualizadas.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("❌ Ocorreu um erro inesperado ao tentar atualizar as credenciais no banco de dados.", ephemeral=True)


    # --- COMANDO /registramunicipio ---
    @app_commands.command(name="registramunicipio", description="Registra um novo município no sistema.")
    @app_commands.checks.has_role("Administrador SICOM") # Protegido pelo cargo
    @app_commands.describe(
        nome="O nome oficial do município (sem números ou caracteres especiais).",
        cnpj="O CNPJ do município (apenas 14 dígitos numéricos)."
    )
    async def registramunicipio(self, interaction: discord.Interaction, nome: str, cnpj: str):
        await interaction.response.defer(ephemeral=True)

        # 1. Validação e Formatação do CNPJ
        if not cnpj.isdigit() or len(cnpj) != 14:
            await interaction.followup.send("❌ **Erro de Validação:** O CNPJ deve conter exatamente 14 dígitos numéricos.", ephemeral=True)
            return
            
        # 2. Validação e Formatação do Nome do Município
        try:
            nome_formatado = self._formatar_e_validar_nome(nome)
        except ValueError as e:
            await interaction.followup.send(f"❌ **Erro de Validação:** {e}", ephemeral=True)
            return
            
        # 3. Tentativa de Inserção no Banco de Dados
        resultado = await insert_municipio(nome=nome_formatado, cnpj=cnpj)
        
        # 4. Feedback para o Usuário
        if resultado["success"]:
            embed = discord.Embed(
                title="✅ Município Registrado com Sucesso!",
                description=f"O município **{nome_formatado}** foi adicionado ao sistema.",
                color=discord.Color.green()
            )
            embed.add_field(name="Nome Registrado", value=nome_formatado, inline=True)
            embed.add_field(name="CNPJ Registrado", value=cnpj, inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # Envia a mensagem de erro específica retornada pela função de query
            await interaction.followup.send(resultado["message"], ephemeral=True)

    # --- COMANDO /registrasicom ---
    @app_commands.command(name="registrasicom", description="Registra uma nova credencial no sistema.")
    @app_commands.checks.has_role("Administrador SICOM") # Protegido pelo cargo
    @app_commands.autocomplete(municipio=municipio_autocomplete, administracao=administracao_autocomplete)
    @app_commands.describe(
        municipio="O município ao qual a credencial pertence.",
        administracao="A administração (PM, CM, etc.) da credencial.",
        cpf_usuario="O CPF do usuário da credencial (11 dígitos numéricos).",
        senha="A senha de acesso.",
        status_validade="A credencial está ativa? (Padrão: Sim)"
    )
    async def registrasicom(
        self,
        interaction: discord.Interaction,
        municipio: str,
        administracao: str,
        cpf_usuario: str,
        senha: str,
        status_validade: bool = True
    ):
        await interaction.response.defer(ephemeral=True)

        # 1. Validação de formato do CPF
        if not cpf_usuario.isdigit() or len(cpf_usuario) != 11:
            await interaction.followup.send("❌ **Erro de Validação:** O CPF deve conter exatamente 11 dígitos numéricos.", ephemeral=True)
            return

        municipio_id = int(municipio)
        administracao_id = int(administracao)

        # 2. Busca (ou cria) o vínculo entre município e administração
        entity_id = await busca_entidade_id(municipio_id, administracao_id)
        if not entity_id:
            # Se não existe, cria o vínculo
            logger.info(f"Vínculo não encontrado para mun_id {municipio_id} e adm_id {administracao_id}. Criando novo...")
            entity_id = await create_municipio_administracao_link(municipio_id, administracao_id)
            if not entity_id:
                await interaction.followup.send("❌ Ocorreu um erro ao criar o vínculo entre o município e a administração.", ephemeral=True)
                return
        
        # 3. Verifica se já existe uma credencial para este vínculo
        if await check_credencial(entity_id):
            await interaction.followup.send("❌ **Erro:** Já existe uma credencial para esta combinação de município e administração. Use o comando `/atualizasicom` para modificá-la.", ephemeral=True)
            return
            
        # 4. Insere a nova credencial
        success = await insert_credencial(
            entity_id=entity_id,
            cpf_usuario=cpf_usuario,
            senha=senha,
            status_validade=status_validade
        )

        # 5. Feedback para o usuário
        if success:
            embed = discord.Embed(
                title="✅ Credencial Registrada com Sucesso!",
                description="Uma nova credencial foi adicionada ao sistema.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("❌ Ocorreu um erro inesperado ao tentar registrar a credencial no banco de dados.", ephemeral=True)


# Função obrigatória que o bot chama para registrar o Cog
async def setup(bot: commands.Bot):
    await bot.add_cog(SicomCommands(bot))
    logger.info("Cog 'SicomCommands' carregado com sucesso.")
