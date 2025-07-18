import discord
import asyncio
import logging
from typing import Dict, List, Any
import locale
from datetime import timedelta, datetime
import io

# Importando os serviços
from database.portal_service import PortalDatabaseService
from services.pdf_service import gerar_pdf_horas_extras
from services.email_service import enviar_email_com_anexo

logger = logging.getLogger(__name__)

# --- Dicionário e Funções Auxiliares ---
DIAS_SEMANA_PT_BR = {
    'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
    'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
}

def formatar_data_em_portugues(data_obj):
    """Formata uma data para o padrão 'dd/mm/yyyy - DiaDaSemana' em português."""
    dia_ingles = data_obj.strftime('%A')
    dia_portugues = DIAS_SEMANA_PT_BR.get(dia_ingles, dia_ingles)
    return f"{data_obj.strftime('%d/%m/%Y')} - {dia_portugues}"

def formatar_timedelta(td: timedelta) -> str:
    """Formata um timedelta em uma string 'HH:MM'."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"

# --- ETAPA 5: View de Confirmação na DM (COM A LÓGICA DE LIMPEZA) ---
class ConfirmacaoEnvioEmailView(discord.ui.View):
    def __init__(self, dados_formulario: Dict, pdf_stream: io.BytesIO):
        super().__init__(timeout=3600.0) # Timeout de 1 hora
        self.dados_formulario = dados_formulario
        self.pdf_stream = pdf_stream

    @discord.ui.button(label="Enviar para o RH", style=discord.ButtonStyle.primary, emoji="📨")
    async def enviar_email_rh(self, interaction: discord.Interaction, button: discord.ui.Button):
        # A primeira resposta à interação é para dar um feedback imediato ao usuário.
        await interaction.response.edit_message(
            content="🔄 Enviando e-mail para o RH, por favor aguarde...",
            view=None # Remove os botões imediatamente
        )

        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(
            None,
            enviar_email_com_anexo,
            self.dados_formulario,
            self.pdf_stream
        )

        # Usamos followup.edit_message para editar a mensagem de "Enviando..."
        if success:
            await interaction.edit_original_response(
                content="✅ E-mail enviado com sucesso para o RH!"
            )
        else:
            await interaction.edit_original_response(
                content="❌ Falha ao enviar o e-mail. Verifique os logs ou contate um administrador."
            )
        
        self.stop() # Encerra a view após a ação

# --- ETAPA 4: View de Revisão Final ("Wizard") ---
class RevisaoFinalView(discord.ui.View):
    def __init__(self, dados_formulario: Dict):
        super().__init__(timeout=600.0)
        self.dados_formulario = dados_formulario

    @discord.ui.button(label="Confirmar e Gerar PDF", style=discord.ButtonStyle.success, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="🔄 Processando sua solicitação... O PDF será enviado para sua DM.",
            embed=None, view=None
        )
        try:
            loop = asyncio.get_running_loop()
            
            # 1. Gera o PDF em memória. O cursor está no final do stream.
            pdf_stream = await loop.run_in_executor(None, gerar_pdf_horas_extras, self.dados_formulario)
            
            # --- CORREÇÃO APLICADA AQUI ---
            
            # 2. Prepara o arquivo para a DM:
            #    a. Move o cursor para o INÍCIO do stream.
            pdf_stream.seek(0)
            #    b. Formata o nome do arquivo.
            nome_colaborador = self.dados_formulario['dados_colaborador']['nome'].replace(' ', '')
            data_hoje = datetime.now().strftime('%d%m%Y')
            nome_arquivo = f"{nome_colaborador}{data_hoje}.pdf"
            #    c. Cria o objeto discord.File. Ele agora lerá o stream desde o início.
            pdf_file_for_discord = discord.File(pdf_stream, filename=nome_arquivo)

            # 3. Prepara o stream para o E-MAIL:
            #    a. Move o cursor para o INÍCIO NOVAMENTE para garantir a leitura completa.
            pdf_stream.seek(0)
            #    b. Cria uma cópia em memória para o anexo do e-mail.
            pdf_stream_for_email = io.BytesIO(pdf_stream.read())

            # ------------------------------------

            view_confirmacao_email = ConfirmacaoEnvioEmailView(self.dados_formulario, pdf_stream_for_email)

            try:
                dm_channel = await interaction.user.create_dm()
                await dm_channel.send("Seu formulário está pronto. Revise o PDF e clique abaixo para enviá-lo ao RH.", file=pdf_file_for_discord, view=view_confirmacao_email)
                await interaction.edit_original_response(content="✅ Formulário gerado! Verifique sua DM para revisar e enviar.")
            except discord.Forbidden:
                await interaction.edit_original_response(content="❌ Não consegui enviar o formulário na sua DM.")
        except Exception as e:
            logger.error(f"Erro ao gerar o PDF ou enviar para a DM: {e}", exc_info=True)
            await interaction.edit_original_response(content="❌ Ocorreu um erro crítico ao gerar seu formulário.")
        
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Solicitação cancelada.", embed=None, view=None)
        self.stop()

# --- ETAPA 3: Formulário Final (Modal) ---
class FormularioJustificativaModal(discord.ui.Modal, title="Justificativa e Atividades"):
    justificativa = discord.ui.TextInput(
        label="Justificativa das Horas Extras",
        style=discord.TextStyle.paragraph,
        placeholder="Ex: Demanda urgente no projeto X para atender ao prazo do cliente Y."
    )
    atividades = discord.ui.TextInput(
        label="Atividades Desenvolvidas",
        style=discord.TextStyle.paragraph,
        placeholder="Ex: Correção do bug #123, desenvolvimento da funcionalidade Z..."
    )

    def __init__(self, dados_formulario: Dict):
        super().__init__(timeout=600.0)
        self.dados_formulario = dados_formulario

    async def on_submit(self, interaction: discord.Interaction):
        # A linha abaixo foi removida da versão final do "Wizard", mas mantendo no seu código:
        await interaction.response.defer(thinking=True, ephemeral=True) 

        self.dados_formulario["justificativa"] = self.justificativa.value
        self.dados_formulario["atividades"] = self.atividades.value

        try:
            loop = asyncio.get_running_loop()
            
            # 1. Gera o PDF em background
            pdf_stream = await loop.run_in_executor(None, gerar_pdf_horas_extras, self.dados_formulario)
            
            # --- CORREÇÃO APLICADA AQUI ---

            # a. Lê o conteúdo COMPLETO do stream para uma variável de bytes.
            #    O .getvalue() pega tudo, independentemente da posição do cursor.
            pdf_bytes = pdf_stream.getvalue()

            # b. Formata o nome do arquivo
            nome_colaborador = self.dados_formulario['dados_colaborador'].get('nome', 'Colaborador')
            data_atual_str = datetime.now().strftime("%d%m%Y")
            nome_arquivo_formatado = f"{nome_colaborador.replace(' ', '')}{data_atual_str}.pdf"
            
            # c. Cria um NOVO stream de memória para a DM usando os bytes.
            pdf_stream_for_discord = io.BytesIO(pdf_bytes)
            pdf_file_for_discord = discord.File(pdf_stream_for_discord, filename=nome_arquivo_formatado)

            # d. Cria um SEGUNDO NOVO stream de memória para o e-mail, usando os mesmos bytes.
            pdf_stream_for_email = io.BytesIO(pdf_bytes)
            
            # ------------------------------------

            # Agora temos duas cópias independentes e o resto do fluxo funcionará.
            view_confirmacao = ConfirmacaoEnvioEmailView(self.dados_formulario, pdf_stream_for_email)

            try:
                dm_channel = await interaction.user.create_dm()
                await dm_channel.send(
                    "Seu formulário está pronto. Revise o PDF e clique abaixo para enviá-lo ao RH.",
                    file=pdf_file_for_discord,
                    view=view_confirmacao
                )
                await interaction.followup.send("✅ Formulário gerado! Verifique sua DM para revisar e enviar.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("❌ Não consegui enviar o formulário na sua DM. Verifique se você permite mensagens diretas de membros do servidor.", ephemeral=True)

        except Exception as e:
            logger.error(f"Erro ao gerar o PDF ou enviar para a DM: {e}", exc_info=True)
            await interaction.followup.send("❌ Ocorreu um erro crítico ao gerar seu formulário.", ephemeral=True)


# --- ETAPA 2: View com Menu de Seleção de Dias (COM AS MUDANÇAS PRINCIPAIS) ---

class DiasSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(placeholder="Selecione os dias que deseja incluir no formulário...", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        # --- LÓGICA ALTERADA ---
        # Agora, o callback do menu apenas salva as escolhas na view-pai
        # e responde à interação para que o Discord não mostre um erro.
        self.view.dias_selecionados_cache = self.values
        await interaction.response.defer() # Apenas confirma o recebimento da seleção

class SelecaoDiasView(discord.ui.View):
    def __init__(self, id_discord: int, tipo_compensacao: str):
        super().__init__(timeout=300.0)
        self.id_discord = id_discord
        self.tipo_compensacao = tipo_compensacao
        self.db_service = PortalDatabaseService()
        self.dias_detalhados_cache: List[Dict] = []
        self.dias_selecionados_cache: List[str] = [] # Novo: para guardar as seleções

    async def preparar_view(self):
        try:
            self.dias_detalhados_cache = self.db_service.buscar_detalhes_ponto_recente(self.id_discord)
            
            if not self.dias_detalhados_cache:
                self.add_item(discord.ui.Button(label="Nenhuma hora extra encontrada na última semana.", disabled=True))
                return

            opcoes = [
                discord.SelectOption(
                    label=f"{formatar_data_em_portugues(dia['data'])} | {formatar_timedelta(dia['horas_extras_timedelta'])}h extras",
                    value=dia['data'].strftime('%Y-%m-%d'),
                    description=f"Batidas: {dia['batidas_str']}"
                ) for dia in self.dias_detalhados_cache
            ]
            self.add_item(DiasSelect(opcoes))
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes de ponto: {e}", exc_info=True)
            self.clear_items()
            self.add_item(discord.ui.Button(label="❌ Erro ao buscar dados do ponto.", disabled=True))

    @discord.ui.button(label="Confirmar Seleção", style=discord.ButtonStyle.success, emoji="✔️", row=1)
    async def confirmar_selecao(self, interaction: discord.Interaction, button: discord.ui.Button):
        # --- LÓGICA MOVIDA PARA CÁ ---
        if not self.dias_selecionados_cache:
            await interaction.response.send_message("❌ Você precisa selecionar pelo menos um dia no menu acima antes de confirmar.", ephemeral=True)
            return

        try:
            dados_colaborador = self.db_service.buscar_dados_colaborador(self.id_discord)
            if not dados_colaborador:
                await interaction.response.send_message("❌ Não foi possível encontrar seus dados cadastrais.", ephemeral=True)
                return

            detalhes_selecionados = [
                dia for dia in self.dias_detalhados_cache 
                if dia['data'].strftime('%Y-%m-%d') in self.dias_selecionados_cache
            ]

            dados_formulario = {
                "dados_colaborador": dados_colaborador,
                "detalhes_selecionados": detalhes_selecionados,
                "tipo_compensacao": self.tipo_compensacao
            }
            
            await interaction.response.send_modal(FormularioJustificativaModal(dados_formulario))
            
            # Edita a mensagem original para desabilitar os componentes após a confirmação
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

        except Exception as e:
            logger.error(f"Erro ao processar confirmação: {e}", exc_info=True)
            await interaction.response.send_message("❌ Ocorreu um erro ao processar sua confirmação.", ephemeral=True)

# --- ETAPA 1: View com Botões de Tipo de Compensação ---
class BotoesSelecaoTipoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180.0)

    async def _responder_e_iniciar_proxima_etapa(self, interaction: discord.Interaction, button: discord.ui.Button, tipo: str):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"Você selecionou: **{button.label}**.\nBuscando seus dias trabalhados...", view=self)
        
        id_discord = interaction.user.id
        
        view_selecao_dias = SelecaoDiasView(id_discord=id_discord, tipo_compensacao=tipo)
        await view_selecao_dias.preparar_view()
        
        await interaction.followup.send(content="Por favor, selecione os dias que deseja incluir no seu formulário:", view=view_selecao_dias, ephemeral=True)

    @discord.ui.button(label="Pagamento de Horas", style=discord.ButtonStyle.primary, custom_id="pagamento")
    async def pagamento_horas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._responder_e_iniciar_proxima_etapa(interaction, button, button.custom_id)
        
    @discord.ui.button(label="Horas a Compensar", style=discord.ButtonStyle.primary, custom_id="compensacao")
    async def horas_compensar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._responder_e_iniciar_proxima_etapa(interaction, button, button.custom_id)

    @discord.ui.button(label="Banco de Horas", style=discord.ButtonStyle.primary, custom_id="banco")
    async def banco_horas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._responder_e_iniciar_proxima_etapa(interaction, button, button.custom_id)