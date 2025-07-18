# views/hr_views.py
import discord
import asyncio
import io
import logging
from typing import List, Dict

from utils.helpers import parse_time_to_minutes
from services.pdf_service import generate_pdf_file
from services.email_service import send_email_with_attachment

logger = logging.getLogger(__name__)

class OvertimeEntryModal(discord.ui.Modal, title="Detalhes do Dia de Hora Extra"):
    data = discord.ui.TextInput(label="Data", placeholder="Ex: 09/07/2025")
    local = discord.ui.TextInput(label="Local", placeholder="Ex: Home Office")
    horario = discord.ui.TextInput(label="Horário", placeholder="Ex: 08:00-12:00", style=discord.TextStyle.paragraph)
    num_horas = discord.ui.TextInput(label="Nº de Horas", placeholder="Formatos: 2h, 2:30, 90m")
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
    async def on_submit(self, interaction: discord.Interaction):
        minutes = parse_time_to_minutes(self.num_horas.value)
        if minutes is None:
            await interaction.response.send_message("❌ Formato inválido para 'Nº de Horas'.", ephemeral=True, delete_after=10)
            return
            
        entry = {"data": self.data.value, "local": self.local.value, "horario": self.horario.value, "num_horas": self.num_horas.value, "minutes": minutes}
        self.parent_view.entries.append(entry)
        await interaction.response.send_message(f"✅ Dia **{self.data.value}** adicionado!", ephemeral=True, delete_after=5)

class OvertimeMainModal(discord.ui.Modal, title="Solicitação de Banco de Horas"):
    cargo = discord.ui.TextInput(label="Cargo")
    coordenador = discord.ui.TextInput(label="Coordenador Responsável")
    justificativa = discord.ui.TextInput(label="Justificativa", style=discord.TextStyle.paragraph)
    atividades = discord.ui.TextInput(label="Atividades Desenvolvidas", style=discord.TextStyle.paragraph)
    
    def __init__(self, compensation_choice: str, parent_view=None):
        super().__init__()
        self.parent_view = parent_view
        self.compensation_choice = compensation_choice
        if parent_view and parent_view.user_data:
            self.cargo.default, self.coordenador.default, self.justificativa.default, self.atividades.default = [parent_view.user_data.get(k) for k in ["cargo", "coordenador", "justificativa", "atividades"]]

    async def on_submit(self, interaction: discord.Interaction):
        user_data = {
            "nome": interaction.user.display_name,
            "cargo": self.cargo.value, "departamento": "Service Desk",
            "coordenador": self.coordenador.value, "justificativa": self.justificativa.value,
            "atividades": self.atividades.value,
            "tipo_compensacao": self.compensation_choice
        }
        if self.parent_view:
            self.parent_view.user_data = user_data
            await interaction.response.send_message("✅ Informações corrigidas.", ephemeral=True, delete_after=5)
            return

        view = OvertimeControlView(author=interaction.user, user_data=user_data)
        await interaction.response.send_message("📝 Informações preenchidas. Use os botões abaixo para continuar.", view=view, ephemeral=True)
        view.message = await interaction.original_response()

class EmailConfirmationView(discord.ui.View):
    def __init__(self, user_data: Dict, pdf_stream: io.BytesIO):
        super().__init__(timeout=300.0)
        self.user_data = user_data
        self.pdf_stream = pdf_stream

    @discord.ui.button(label="Enviar para o RH", style=discord.ButtonStyle.primary, emoji="📨")
    async def send_email_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, send_email_with_attachment, self.user_data, self.pdf_stream)
        
        if success:
            await interaction.followup.send("✅ E-mail enviado com sucesso para o RH!", ephemeral=True)
            await interaction.message.edit(content="Este formulário foi enviado.", view=None)
        else:
            await interaction.followup.send("❌ Falha ao enviar o e-mail.", ephemeral=True)
        self.stop()

class OvertimeControlView(discord.ui.View):
    def __init__(self, author: discord.Member, user_data: Dict):
        super().__init__(timeout=600.0)
        self.author = author
        self.user_data = user_data
        self.entries: List[Dict] = []
        self.message = None

    @discord.ui.button(label="Adicionar Dia", style=discord.ButtonStyle.secondary, emoji="➕")
    async def add_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OvertimeEntryModal(parent_view=self))

    @discord.ui.button(label="Corrigir Informações", style=discord.ButtonStyle.secondary, emoji="📝")
    async def correct_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OvertimeMainModal(compensation_choice=self.user_data['tipo_compensacao'], parent_view=self))

    @discord.ui.button(label="Finalizar e Gerar PDF", style=discord.ButtonStyle.success, emoji="📄")
    async def finalize_and_generate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.entries:
            await interaction.response.send_message("❌ Adicione pelo menos um dia.", ephemeral=True, delete_after=10)
            return

        await interaction.response.defer()
        
        loop = asyncio.get_running_loop()
        pdf_file_object, pdf_stream_for_email = await loop.run_in_executor(None, generate_pdf_file, self.user_data, self.entries)
        
        try:
            dm_channel = await self.author.create_dm()
            email_view = EmailConfirmationView(user_data=self.user_data, pdf_stream=pdf_stream_for_email)
            await dm_channel.send("Seu formulário está pronto. Revise o PDF e clique abaixo para enviá-lo ao RH.", file=pdf_file_object, view=email_view)
            await interaction.edit_original_response(content="✅ PDF gerado! Verifique suas DMs.", view=None)
        except discord.Forbidden:
            await interaction.edit_original_response(content="❌ Não consegui enviar para sua DM.", view=None)
        self.stop()