# views/rh_views.py
import discord
import asyncio
import logging
from typing import Dict, List, Any
from datetime import timedelta, datetime, date
import io
import json
from decimal import Decimal

# Importando os serviços e queries
from services.portal_service import PortalDatabaseService
from services.pdf_service import gerar_pdf_horas_extras
from services.email_service import enviar_email_com_anexo
from database.bot_queries import (
    criar_solicitacao, 
    atualizar_status_solicitacao, 
    buscar_datas_bloqueadas, 
    cancelar_solicitacao
)

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

def sanitizar_para_json(data: Any) -> Any:
    """Converte tipos de dados não serializáveis (Decimal, date, etc.) para tipos JSON."""
    if isinstance(data, dict):
        return {key: sanitizar_para_json(value) for key, value in data.items()}
    if isinstance(data, list):
        return [sanitizar_para_json(item) for item in data]
    if isinstance(data, Decimal):
        return float(data)
    if isinstance(data, timedelta):
        return data.total_seconds()
    if isinstance(data, (date, datetime)):
        return data.isoformat()
    return data

# --- Views do Fluxo de Aprovação em Etapas ---

# ETAPA 1: View com Botões de Tipo de Compensação
class BotoesSelecaoTipoView(discord.ui.View):
    def __init__(self, dados_colaborador: Dict):
        super().__init__(timeout=180.0)
        self.dados_colaborador = dados_colaborador

    async def _responder_e_iniciar_proxima_etapa(self, interaction: discord.Interaction, button: discord.ui.Button, tipo: str):
        await interaction.response.edit_message(content=f"Você selecionou: **{button.label}**.\nBuscando seus dias trabalhados...", view=None)
        
        view_selecao_dias = SelecaoDiasView(dados_colaborador=self.dados_colaborador, tipo_compensacao=tipo)
        await view_selecao_dias.preparar_view()
        
        embed_inicial = view_selecao_dias.criar_embed_resumo()
        await interaction.followup.send(embed=embed_inicial, view=view_selecao_dias, ephemeral=True)

    """
    -------Trecho não será utilizado por enquanto, mas mantido para referencia futuramente.-------

    @discord.ui.button(label="Pagamento de Horas", style=discord.ButtonStyle.primary, custom_id="pagamento")
    async def pagamento_horas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._responder_e_iniciar_proxima_etapa(interaction, button, button.custom_id)
        
    @discord.ui.button(label="Horas a Compensar", style=discord.ButtonStyle.primary, custom_id="compensacao")
    async def horas_compensar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._responder_e_iniciar_proxima_etapa(interaction, button, button.custom_id)
    """

    @discord.ui.button(label="Banco de Horas", style=discord.ButtonStyle.primary, custom_id="banco")
    async def banco_horas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._responder_e_iniciar_proxima_etapa(interaction, button, button.custom_id)

# ETAPA 2: View com Menu de Seleção de Dias
class DiasSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(placeholder="Selecione os dias que deseja incluir no formulário...", min_values=1, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.dias_selecionados_cache = self.values
        confirmar_button = next((item for item in self.view.children if isinstance(item, discord.ui.Button) and item.custom_id == "confirmar_selecao"), None)
        if confirmar_button:
            confirmar_button.disabled = not self.values
        novo_embed = self.view.criar_embed_resumo()
        await interaction.response.edit_message(embed=novo_embed, view=self.view)

class SelecaoDiasView(discord.ui.View):
    def __init__(self, dados_colaborador: Dict, tipo_compensacao: str):
        super().__init__(timeout=300.0)
        self.dados_colaborador = dados_colaborador
        self.id_discord = dados_colaborador['id_discord']
        self.tipo_compensacao = tipo_compensacao
        self.db_service = PortalDatabaseService()
        self.dias_detalhados_cache: List[Dict] = []
        self.dias_selecionados_cache: List[str] = []

    def criar_embed_resumo(self) -> discord.Embed:
        if not self.dias_selecionados_cache:
            return discord.Embed(title="Seleção de Dias para Justificativa", description="*Nenhum dia selecionado.*\n\nEscolha um ou mais dias no menu abaixo.", color=discord.Color.blue())
        
        embed = discord.Embed(title="Resumo da Seleção", color=discord.Color.green())
        descricao_itens = []
        for data_str in self.dias_selecionados_cache:
            dia_detalhe = next((dia for dia in self.dias_detalhados_cache if dia['data'].strftime('%Y-%m-%d') == data_str), None)
            if dia_detalhe:
                descricao_itens.append(f"**✅ {formatar_data_em_portugues(dia_detalhe['data'])}**\n"
                                     f"Horas Extras: `{formatar_timedelta(dia_detalhe['horas_extras_timedelta'])}` | Batidas: `{dia_detalhe['batidas_str']}`")
        embed.description = "\n\n".join(descricao_itens)
        embed.set_footer(text="Revise sua seleção. Quando terminar, clique em 'Confirmar Seleção'.")
        return embed

    async def preparar_view(self):
        try:
            dias_potenciais = self.db_service.buscar_detalhes_ponto_recente(self.id_discord)
            datas_ja_bloqueadas = await buscar_datas_bloqueadas(int(self.id_discord))
            set_datas_bloqueadas = set(datas_ja_bloqueadas)

            self.dias_detalhados_cache = [
                dia for dia in dias_potenciais if dia['data'] not in set_datas_bloqueadas
            ]
            
            if not self.dias_detalhados_cache:
                self.add_item(discord.ui.Button(label="Nenhuma hora extra disponível para lançamento.", disabled=True))
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

    @discord.ui.button(label="Confirmar Seleção", style=discord.ButtonStyle.success, emoji="✔️", row=1, custom_id="confirmar_selecao", disabled=True)
    async def confirmar_selecao(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.dias_selecionados_cache:
            await interaction.response.send_message("❌ Você precisa selecionar pelo menos um dia no menu acima antes de confirmar.", ephemeral=True)
            return
        try:
            detalhes_selecionados = [
                dia for dia in self.dias_detalhados_cache 
                if dia['data'].strftime('%Y-%m-%d') in self.dias_selecionados_cache
            ]
            dados_formulario = {
                "dados_colaborador": self.dados_colaborador, 
                "detalhes_selecionados": detalhes_selecionados, 
                "tipo_compensacao": self.tipo_compensacao
            }
            
            await interaction.response.send_modal(FormularioJustificativaModal(dados_formulario))
            
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)
        except Exception as e:
            logger.error(f"Erro ao processar confirmação: {e}", exc_info=True)
            await interaction.followup.send("❌ Ocorreu um erro ao processar sua confirmação.", ephemeral=True)

# ETAPA 3: Formulário Final (Modal)
class FormularioJustificativaModal(discord.ui.Modal, title="Justificativa e Atividades"):
    justificativa = discord.ui.TextInput(label="Justificativa das Horas Extras", style=discord.TextStyle.paragraph)
    atividades = discord.ui.TextInput(label="Atividades Desenvolvidas", style=discord.TextStyle.paragraph)

    def __init__(self, dados_formulario: Dict):
        super().__init__(timeout=600.0)
        self.dados_formulario = dados_formulario

    async def on_submit(self, interaction: discord.Interaction):
        self.dados_formulario["justificativa"] = self.justificativa.value
        self.dados_formulario["atividades"] = self.atividades.value

        embed = discord.Embed(title="🔍 Revisão do Formulário de Horas Extras", color=discord.Color.gold())
        dias_formatados = [
            f"• **{formatar_data_em_portugues(dia['data'])}** ({formatar_timedelta(dia['horas_extras_timedelta'])}h extras)"
            for dia in self.dados_formulario['detalhes_selecionados']
        ]
        embed.add_field(name="Dias Selecionados", value="\n".join(dias_formatados), inline=False)
        embed.add_field(name="Justificativa", value=self.justificativa.value, inline=False)
        embed.add_field(name="Atividades", value=self.atividades.value, inline=False)
        embed.set_footer(text="Revise as informações. Se estiver tudo correto, confirme para gerar o PDF.")
        await interaction.response.edit_message(content=None, embed=embed, view=RevisaoFinalView(self.dados_formulario))

# ETAPA 4: View de Revisão Final 
class RevisaoFinalView(discord.ui.View):
    def __init__(self, dados_formulario: Dict):
        super().__init__(timeout=600.0)
        self.dados_formulario = dados_formulario

    @discord.ui.button(label="Confirmar e Gerar PDF", style=discord.ButtonStyle.success, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔄 Gerando seu PDF para revisão...", embed=None, view=None)
        
        dados_serializaveis = sanitizar_para_json(self.dados_formulario)
        string_json = json.dumps(dados_serializaveis)
        solicitacao_id = await criar_solicitacao(interaction.user.id, string_json)
        if not solicitacao_id:
            await interaction.edit_original_response(content="❌ Erro ao registrar sua solicitação no banco de dados.")
            return

        try:
            pdf_stream = await asyncio.get_running_loop().run_in_executor(None, gerar_pdf_horas_extras, self.dados_formulario)
            pdf_bytes = pdf_stream.getvalue()
            
            nome_colaborador = self.dados_formulario['dados_colaborador']['nome'].replace(' ', '')
            data_hoje = datetime.now().strftime('%d%m%Y')
            nome_arquivo = f"{nome_colaborador}{data_hoje}.pdf"
            
            pdf_file_for_dm = discord.File(io.BytesIO(pdf_bytes), filename=nome_arquivo)
            view_encaminhar = EncaminharParaResponsavelView(solicitacao_id, self.dados_formulario, io.BytesIO(pdf_bytes))

            await interaction.user.send(
                "Seu formulário está pronto. Revise o PDF e, se estiver tudo certo, clique abaixo para enviá-lo ao seu responsável.",
                file=pdf_file_for_dm,
                view=view_encaminhar
            )
            await interaction.edit_original_response(content="✅ Formulário gerado! Verifique sua DM para revisar e encaminhar para aprovação.")
        except discord.Forbidden:
            await interaction.edit_original_response(content="❌ Não consegui enviar o formulário na sua DM.")
        except Exception as e:
            logger.error(f"Erro ao gerar o PDF ou enviar para a DM do colaborador: {e}", exc_info=True)
            await interaction.edit_original_response(content="❌ Ocorreu um erro crítico ao gerar seu formulário.")
        
        self.stop()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Solicitação cancelada.", embed=None, view=None)
        self.stop()

# ETAPA 4.5: View de Encaminhamento para o COLABORADOR 
class EncaminharParaResponsavelView(discord.ui.View):
    def __init__(self, solicitacao_id: int, dados_formulario: Dict, pdf_stream: io.BytesIO):
        super().__init__(timeout=3600.0) # Timeout de 1 hora para a ação
        self.solicitacao_id = solicitacao_id
        self.dados_formulario = dados_formulario
        self.pdf_stream = pdf_stream

    @discord.ui.button(label="Enviar para o Responsável", style=discord.ButtonStyle.primary, emoji="▶️", row=0)
    async def encaminhar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Desabilita todos os botões para evitar cliques duplos
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="🔄 Encaminhando para o seu responsável para aprovação...", view=self)
        
        responsavel_id_discord = self.dados_formulario['dados_colaborador'].get('responsavel_id_discord') ## MUDAR RESPNSAVEL AQUI
        if not responsavel_id_discord:
            await interaction.edit_original_response(content="❌ Não foi possível encontrar o Discord do seu responsável no sistema.")
            return

        nome_arquivo = f"Solicitacao_{self.dados_formulario['dados_colaborador']['nome'].replace(' ', '')}.pdf"
        self.pdf_stream.seek(0)
        pdf_file = discord.File(self.pdf_stream, filename=nome_arquivo)
        view_aprovacao = AprovacaoResponsavelView(self.solicitacao_id, self.dados_formulario, self.pdf_stream)

        try:
            responsavel = await interaction.client.fetch_user(int(responsavel_id_discord))
            await responsavel.send(
                f"Olá! Você recebeu uma nova solicitação de horas extras de **{self.dados_formulario['dados_colaborador']['nome']}** para aprovação.",
                file=pdf_file,
                view=view_aprovacao
            )
            await interaction.edit_original_response(content="✅ Formulário enviado com sucesso para o seu responsável!")
        except Exception as e:
            logger.error(f"Falha ao enviar DM para o responsável {responsavel_id_discord}: {e}")
            await interaction.edit_original_response(content="❌ Falha ao enviar a solicitação para o seu responsável.")
        
        self.stop()

    # --- BOTÃO NOVO ADICIONADO AQUI ---
    @discord.ui.button(label="Cancelar Solicitação", style=discord.ButtonStyle.danger, emoji="✖️", row=0)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Desabilita todos os botões
        for item in self.children:
            item.disabled = True
        
        # Atualiza o status no banco de dados
        success = await cancelar_solicitacao(self.solicitacao_id, interaction.user.id)
        
        if success:
            await interaction.response.edit_message(content="❌ Sua solicitação foi cancelada com sucesso.", view=self)
        else:
            await interaction.response.edit_message(content="⚠️ Ocorreu um erro ao tentar cancelar sua solicitação.", view=self)

        self.stop()

# ETAPA 5: View de Aprovação para o RESPONSÁVEL 
class AprovacaoResponsavelView(discord.ui.View):
    def __init__(self, solicitacao_id: int, dados_formulario: Dict, pdf_original_stream: io.BytesIO):
        super().__init__(timeout=86400)
        self.solicitacao_id = solicitacao_id
        self.dados_formulario = dados_formulario
        self.pdf_original_stream = pdf_original_stream

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success)
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="🔄 Processando aprovação e assinando o PDF...", view=None)
        
        dados_aprovador = {
            "nome": interaction.user.display_name,
            "id_discord": interaction.user.id,
            "data_hora": datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
        }
        
        dados_para_assinar = dict(self.dados_formulario)  # shallow copy
        dados_para_assinar["dados_aprovador"] = dados_aprovador


        loop = asyncio.get_running_loop()
        pdf_assinado_stream = await loop.run_in_executor(None, gerar_pdf_horas_extras, dados_para_assinar)
        success = await loop.run_in_executor(None, enviar_email_com_anexo, self.dados_formulario, pdf_assinado_stream)

        await atualizar_status_solicitacao(self.solicitacao_id, 'APROVADO', interaction.user.id)

        # Notifica o colaborador que fez a solicitação original.
        try:
            colaborador_id = int(self.dados_formulario['dados_colaborador']['id_discord'])
            colaborador = await interaction.client.fetch_user(colaborador_id)
            if colaborador:
                await colaborador.send(f"✅ Boas notícias! Sua solicitação de horas extras foi **aprovada** por {interaction.user.display_name}.")
        except Exception as e:
            logger.error(f"Falha ao notificar o colaborador {colaborador_id} sobre a aprovação: {e}")

        await interaction.edit_original_response(content=f"✅ Solicitação de {self.dados_formulario['dados_colaborador']['nome']} **aprovada** com sucesso!")
        self.stop()
        
    @discord.ui.button(label="Reprovar", style=discord.ButtonStyle.danger)
    async def reprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Solicitação reprovada.", view=None)
        await atualizar_status_solicitacao(self.solicitacao_id, 'REPROVADO', interaction.user.id)

        # --- MELHORIA APLICADA AQUI ---
        # Notifica o colaborador sobre a reprovação.
        try:
            colaborador_id = int(self.dados_formulario['dados_colaborador']['id_discord'])
            colaborador = await interaction.client.fetch_user(colaborador_id)
            if colaborador:
                await colaborador.send(f"❌ Sua solicitação de horas extras foi **reprovada** por {interaction.user.display_name}.")
        except Exception as e:
            logger.error(f"Falha ao notificar o colaborador {colaborador_id} sobre a reprovação: {e}")

        self.stop()
