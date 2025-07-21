# views/rh_view.py
import discord
import asyncio
import logging
from typing import Dict, List, Any
from datetime import timedelta, datetime
import io
import os

# Importando os serviços e helpers
from database.portal_service import PortalDatabaseService
from services.pdf_service import gerar_pdf_horas_extras
from services.email_service import enviar_email_com_anexo # Renomeado para consistência
from utils.helpers import parse_time_to_minutes # Supondo que o helper foi movido

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

# --- NOVA VIEW DE APROVAÇÃO DO GESTOR ---
class ManagerApprovalView(discord.ui.View):
    """View enviada ao gestor para aprovar ou rejeitar a solicitação."""
    def __init__(self, original_author: discord.Member, dados_formulario: Dict):
        super().__init__(timeout=86400) # Timeout de 24 horas para a aprovação
        self.original_author = original_author
        self.dados_formulario = dados_formulario

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, emoji="✔️")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=False, thinking=True) # Resposta visível no canal de DM

        # 1. Prepara os dados da assinatura eletrônica
        horas_aprovadas = {
            "name": interaction.user.display_name,
            "email": str(interaction.user), # Formato Nome#1234
            "timestamp": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }

        # 2. Gera o NOVO PDF, agora com a assinatura
        signed_pdf_stream = gerar_pdf_horas_extras(
            dados_formulario=self.dados_formulario, 
            resp_aprovacao=horas_aprovadas
        )

        # 3. Envia o PDF assinado para o RH
        loop = asyncio.get_running_loop()
        email_success = await loop.run_in_executor(
            None, enviar_email_com_anexo, self.dados_formulario, signed_pdf_stream
        )

        # 4. Desabilita os botões e atualiza a mensagem do gestor
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(content=f"Solicitação de {self.original_author.display_name} **aprovada** por você.", view=self)

        # 5. Notifica o colaborador
        if email_success:
            await self.original_author.send(f"✅ Sua solicitação de banco de horas foi **aprovada** por {interaction.user.display_name} e enviada ao RH.")
        else:
            await self.original_author.send(f"⚠️ Sua solicitação de banco de horas foi **aprovada**, mas ocorreu um erro no envio para o RH. Fale com um administrador.")
        
        self.stop()

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.danger, emoji="✖️")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=False)

        # Desabilita os botões e atualiza a mensagem do gestor
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(content=f"Solicitação de {self.original_author.display_name} **rejeitada** por você.", view=self)

        # Notifica o colaborador
        await self.original_author.send(f"❌ Sua solicitação de banco de horas foi **rejeitada** por {interaction.user.display_name}.")
        
        self.stop()

# --- ETAPA 3: Formulário Final (Modal com lógica de aprovação) ---
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
        await interaction.response.defer(thinking=True, ephemeral=True) 

        self.dados_formulario["justificativa"] = self.justificativa.value
        self.dados_formulario["atividades"] = self.atividades.value

        try:
            # 1. Gera o PDF inicial (sem assinatura) para revisão do gestor
            pdf_stream = gerar_pdf_horas_extras(self.dados_formulario)
            nome_colaborador = self.dados_formulario['dados_colaborador']['nome'].replace(' ', '')
            nome_arquivo = f"Solicitacao_{nome_colaborador}.pdf"
            pdf_file = discord.File(pdf_stream, filename=nome_arquivo)

            # 2. Encontra o gestor a partir do .env
            manager_id_str = os.getenv("MANAGER_USER_ID")
            if not manager_id_str:
                await interaction.followup.send("❌ Erro de configuração: O ID do gestor não foi definido.", ephemeral=True)
                return
            
            manager = await interaction.client.fetch_user(int(manager_id_str))
            
            # 3. Envia o PDF e a View de aprovação para o gestor
            approval_view = ManagerApprovalView(
                original_author=interaction.user,
                dados_formulario=self.dados_formulario
            )
            await manager.send(
                f"Olá! O colaborador **{interaction.user.display_name}** enviou uma solicitação de banco de horas para sua aprovação.",
                file=pdf_file,
                view=approval_view
            )

            # 4. Confirma ao colaborador que foi enviado para aprovação
            await interaction.followup.send("✅ Formulário finalizado e enviado para aprovação do seu gestor! Você será notificado(a) da decisão por DM.", ephemeral=True)

        except (discord.NotFound, ValueError):
            await interaction.followup.send("❌ Erro de configuração: O ID do gestor é inválido.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"❌ Não consegui enviar a DM para o gestor ({manager.name}).", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao enviar para aprovação: {e}", exc_info=True)
            await interaction.followup.send("❌ Ocorreu um erro crítico ao enviar seu formulário para aprovação.", ephemeral=True)

# --- ETAPA 2: View com Menu de Seleção de Dias ---
class DiasSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(placeholder="Selecione os dias que deseja incluir...", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.dias_selecionados_cache = self.values
        await interaction.response.defer()

class SelecaoDiasView(discord.ui.View):
    def __init__(self, id_discord: int, tipo_compensacao: str):
        super().__init__(timeout=300.0)
        self.id_discord = id_discord
        self.tipo_compensacao = tipo_compensacao
        self.db_service = PortalDatabaseService()
        self.dias_detalhados_cache: List[Dict] = []
        self.dias_selecionados_cache: List[str] = []

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
        if not self.dias_selecionados_cache:
            await interaction.response.send_message("❌ Você precisa selecionar pelo menos um dia no menu acima.", ephemeral=True)
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
