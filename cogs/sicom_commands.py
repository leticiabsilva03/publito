# cogs/sicom_commands.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
import unidecode
import re

# Importando da camada de Modelo (database)
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
# Importando da camada de Visão
from views.sicom_view import create_credentials_embed

logger = logging.getLogger(__name__)

class SicomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

       # Adiciona .strip() para remover espaços no início e no fim
        nome_limpo = nome_sem_acento.strip()
    
        if not re.match(r"^[A-Za-z\s]+$", nome_limpo):
            raise ValueError("O nome do município deve conter apenas letras e espaços.")
        return nome_sem_acento.title()

    # --- AUTOCOMPLETES ---
    async def municipio_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        municipios = await fetch_municipio_autocomplete(current)
        return [app_commands.Choice(name=mun["nom_municipio"], value=str(mun["cod_municipio"])) for mun in municipios]

    async def administracao_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        administracoes = await fetch_administracao_autocomplete(current)
        return [app_commands.Choice(name=f'{adm["sigla_administracao"]} - {adm["des_administracao"] or "Sem descrição"}', value=str(adm["cod_administracao"])) for adm in administracoes]

    # --- COMANDO /sicom ---
    @app_commands.command(name="sicom", description="Consulta as credenciais de um município.")
    @app_commands.autocomplete(municipio=municipio_autocomplete)
    @app_commands.describe(municipio="Comece a digitar o nome do município para ver as opções.")
    async def sicom(self, interaction: discord.Interaction, municipio: str):
        await interaction.response.defer(ephemeral=True)
        
        municipio_id = int(municipio)
        results = await fetch_credenciais_por_id(municipio_id)

        if not results:
            await interaction.followup.send("Nenhuma credencial encontrada para este município.", ephemeral=True)
            return
        
        # Chama a função da camada de Visão para criar o embed
        embed = create_credentials_embed(results)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    # --- COMANDO /atualizasicom ---
    @app_commands.command(name="atualizasicom", description="Atualiza as credenciais de uma entidade.")
    @app_commands.checks.has_role("Administrador SICOM")
    @app_commands.autocomplete(municipio=municipio_autocomplete, administracao=administracao_autocomplete)
    @app_commands.describe(
        municipio="O município da credencial a ser atualizada.",
        administracao="A administração (PM, CM, etc.) da credencial.",
        novo_cpf="O novo CPF do usuário (11 dígitos, sem pontos ou traços).",
        nova_senha="A nova senha de acesso.",
        nova_validade="O novo status de validade da credencial (True ou False)."
    )
    async def atualizasicom(
        self, interaction: discord.Interaction, municipio: str, administracao: str,
        novo_cpf: Optional[str] = None, nova_senha: Optional[str] = None, nova_validade: Optional[bool] = None
    ):
        await interaction.response.defer(ephemeral=True)

        if all(arg is None for arg in [novo_cpf, nova_senha, nova_validade]):
            await interaction.followup.send("❌ Você precisa fornecer pelo menos um campo para atualizar.", ephemeral=True)
            return
        if novo_cpf and (not novo_cpf.isdigit() or len(novo_cpf) != 11):
            await interaction.followup.send("❌ O CPF deve conter exatamente 11 dígitos numéricos.", ephemeral=True)
            return

        municipio_id = int(municipio)
        administracao_id = int(administracao)
        entity_id = await busca_entidade_id(municipio_id, administracao_id)
        
        if not entity_id:
            await interaction.followup.send("❌ Não foi encontrada uma entidade para a combinação informada.", ephemeral=True)
            return
            
        updates_to_perform = {k: v for k, v in {"cpf_usuario": novo_cpf, "senha": nova_senha, "status_validade": nova_validade}.items() if v is not None}
        
        success = await update_credenciais(entity_id, updates_to_perform)
        
        if success:
            embed = discord.Embed(title="✅ Sucesso!", description="As credenciais foram atualizadas.", color=discord.Color.green())
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("❌ Ocorreu um erro ao atualizar as credenciais.", ephemeral=True)

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