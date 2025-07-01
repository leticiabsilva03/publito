# cogs/hr_commands.py
import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import List, Dict, Optional
import io
import re
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import asyncio

# Lib para geração de arquivos PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger(__name__)

# --- FUNÇÕES AUXILIARES ---

def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """Converte uma string de tempo (ex: "2h", "2:30", "90m") para minutos."""
    # Limpa e normaliza a string de entrada primeiro
    s = time_str.strip().lower()

    # Tenta o formato HH:MM primeiro, pois é inequívoco
    match_colon = re.fullmatch(r'(\d+):(\d{1,2})', s)
    if match_colon:
        return int(match_colon.group(1)) * 60 + int(match_colon.group(2))

    # Tenta o formato de número simples (considerado horas)
    if s.isdigit():
        return int(s) * 60

    # Tenta o formato com h e/ou m.
    # Esta regex é mais estrita e não permite espaços entre o número e a letra (ex: '1 h' é inválido).
    # Permite um espaço opcional entre a parte das horas e a parte dos minutos (ex: '1h 30m' é válido).
    match_hm = re.fullmatch(r'^(?:(\d+)h)?\s*(?:(\d+)m)?$', s)
    
    # Verifica se a regex correspondeu à string inteira e se capturou algum grupo.
    if match_hm and any(match_hm.groups()):
        # Verifica se a string original não é apenas "h" ou "m" ou vazia
        if s in ('h', 'm', ''):
            return None
        
        hours = int(match_hm.group(1) or 0)
        minutes = int(match_hm.group(2) or 0)
        return hours * 60 + minutes
        
    return None # Retorna None para qualquer outro formato inválido.

def send_email_with_attachment(user_data: Dict, pdf_stream: io.BytesIO):
    """Envia o e-mail com o PDF em anexo. Esta é uma função SÍNCRONA."""
    try:
        from_email = os.getenv("EMAIL_USER")
        password = os.getenv("EMAIL_PASSWORD")
        to_email = os.getenv("EMAIL_RECIPIENT")
        host = os.getenv("EMAIL_HOST")
        port = int(os.getenv("EMAIL_PORT"))
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = f"Solicitação de Banco de Horas - {user_data['nome']}"
        
        body = f"Olá,\n\nSegue em anexo o formulário de solicitação de banco de horas preenchido por {user_data['nome']}.\n\nAtenciosamente,\n{user_data['nome']}"
        msg.attach(MIMEText(body, 'plain'))
        
        pdf_stream.seek(0)
        attachment = MIMEApplication(pdf_stream.read(), _subtype="pdf")
        attachment.add_header('Content-Disposition', 'attachment', filename=f"Banco_de_Horas_{user_data['nome'].replace(' ', '_')}.pdf")
        msg.attach(attachment)
        
        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            server.login(from_email, password)
            server.send_message(msg)
            
        logger.info(f"E-mail de banco de horas para {user_data['nome']} enviado com sucesso para {to_email}.")
        return True
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail: {e}", exc_info=True)
        return False

# --- MODAIS E VIEWS ---
class OvertimeEntryModal(discord.ui.Modal, title="Detalhes do Dia de Hora Extra"):
    data = discord.ui.TextInput(label="Data", placeholder="Ex: 23/06/2025")
    local = discord.ui.TextInput(label="Local", placeholder="Ex: Home Office")
    horario = discord.ui.TextInput(label="Horário", placeholder="Ex: 08:00-12:00 e 13:00-18:00", style=discord.TextStyle.paragraph)
    num_horas = discord.ui.TextInput(label="Nº de Horas", placeholder="Formatos: 2h, 2:30, 90m")
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        
    async def on_submit(self, interaction: discord.Interaction):
        minutes = parse_time_to_minutes(self.num_horas.value)
        if minutes is None:
            await interaction.response.send_message(f"❌ Formato inválido para 'Nº de Horas'.", ephemeral=True)
            return
        entry = {"data": self.data.value, "local": self.local.value, "horario": self.horario.value, "num_horas": self.num_horas.value, "minutes": minutes}
        self.parent_view.entries.append(entry)
        
        # --- MELHORIA APLICADA ---
        # Envia uma mensagem de confirmação que se apaga após 5 segundos.
        await interaction.response.send_message(f"✅ Dia **{self.data.value}** adicionado!", ephemeral=True, delete_after=5)

class OvertimeMainModal(discord.ui.Modal, title="Solicitação de Banco de Horas"):
    cargo = discord.ui.TextInput(label="Cargo")
    coordenador = discord.ui.TextInput(label="Coordenador Responsável")
    justificativa = discord.ui.TextInput(label="Justificativa para a Realização", style=discord.TextStyle.paragraph)
    atividades = discord.ui.TextInput(label="Atividades a Serem Desenvolvidas", style=discord.TextStyle.paragraph)
    
    def __init__(self, parent_view=None):
        super().__init__()
        self.parent_view = parent_view
        if parent_view and parent_view.user_data:
            self.cargo.default, self.coordenador.default, self.justificativa.default, self.atividades.default = [parent_view.user_data.get(k) for k in ["cargo", "coordenador", "justificativa", "atividades"]]

    async def on_submit(self, interaction: discord.Interaction):
        user_data = {
            "nome": interaction.user.display_name,
            "cargo": self.cargo.value, 
            "departamento": "Service Desk",
            "coordenador": self.coordenador.value, 
            "justificativa": self.justificativa.value,
            "atividades": self.atividades.value,
        }
        if self.parent_view:
            self.parent_view.user_data = user_data
            await interaction.response.send_message("✅ Informações corrigidas.", ephemeral=True, delete_after=5)
            return

        view = OvertimeControlView(author=interaction.user, user_data=user_data)
        await interaction.response.send_message("📝 Informações preenchidas. Use os botões para continuar.", view=view, ephemeral=True)
        view.message = await interaction.original_response()

class EmailConfirmationView(discord.ui.View):
    def __init__(self, user_data: Dict, pdf_stream: io.BytesIO):
        super().__init__(timeout=300.0)
        self.user_data = user_data
        self.pdf_stream = pdf_stream

    @discord.ui.button(label="Enviar para o RH", style=discord.ButtonStyle.primary, emoji="📨")
    async def send_email_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(
            None, send_email_with_attachment, self.user_data, self.pdf_stream
        )
        if success:
            await interaction.edit_original_response(content="✅ E-mail enviado com sucesso para o RH!", view=None)
        else:
            await interaction.edit_original_response(content="❌ Falha ao enviar o e-mail. Por favor, contate um administrador.", view=None)
        self.stop()

class OvertimeControlView(discord.ui.View):
    def __init__(self, author: discord.Member, user_data: Dict):
        super().__init__(timeout=600.0)
        self.author = author
        self.user_data = user_data
        self.entries: List[Dict] = []
        self.message = None

    def calculate_total_time(self) -> str:
        total_minutes = sum(entry.get('minutes', 0) for entry in self.entries)
        if total_minutes == 0: return "00hs 00min"
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}hs {minutes:02d}min"

    @discord.ui.button(label="Adicionar Dia", style=discord.ButtonStyle.secondary, emoji="➕")
    async def add_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OvertimeEntryModal(parent_view=self))

    @discord.ui.button(label="Corrigir Informações", style=discord.ButtonStyle.secondary, emoji="📝")
    async def correct_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OvertimeMainModal(parent_view=self))

    @discord.ui.button(label="Finalizar e Gerar PDF", style=discord.ButtonStyle.success, emoji="📄")
    async def finalize_and_generate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.entries:
            await interaction.response.send_message("❌ Adicione pelo menos um dia antes de finalizar.", ephemeral=True, delete_after=10)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        pdf_file_object, pdf_stream_for_email = self.generate_pdf_file()
        
        try:
            dm_channel = await self.author.create_dm()
            email_view = EmailConfirmationView(user_data=self.user_data, pdf_stream=pdf_stream_for_email)
            await dm_channel.send(
                "Olá! Seu formulário está pronto. Após revisar o PDF, clique abaixo para enviá-lo ao RH.",
                file=pdf_file_object,
                view=email_view
            )
            # --- MELHORIA APLICADA ---
            # A mensagem final no canal também se apaga após 10 segundos.
            await interaction.followup.send("✅ PDF gerado! Verifique suas mensagens diretas (DM) para o próximo passo.", ephemeral=True, delete_after=10)
        except discord.Forbidden:
            await interaction.followup.send("❌ Não consegui enviar o arquivo para sua DM. Verifique suas configurações de privacidade.", ephemeral=True)
        
        for item in self.children: item.disabled = True
        await interaction.edit_original_response(view=self)
        self.stop()

    def generate_pdf_file(self) -> tuple[discord.File, io.BytesIO]:
        file_stream = io.BytesIO()
        filename = f"Banco_de_Horas_{self.user_data['nome'].replace(' ', '_')}.pdf"
        total_time_str = self.calculate_total_time()
        
        doc = SimpleDocTemplate(file_stream, pagesize=letter, leftMargin=72, rightMargin=72, topMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()
        elements = []
        
        styles.add(ParagraphStyle(name='h2_custom', parent=styles['h2'], spaceAfter=6))
        
        elements.append(Paragraph("Solicitação Prévia Para Realização de Horas Extras", styles['h1']))
        elements.append(Spacer(1, 24))
        
        elements.append(Paragraph("Identificação do Servidor", styles['h2_custom']))
        elements.append(Paragraph(f"<b>NOME:</b> {self.user_data['nome']}", styles['Normal']))
        elements.append(Paragraph(f"<b>DEPARTAMENTO:</b> {self.user_data['departamento']}", styles['Normal']))
        elements.append(Paragraph(f"<b>CARGO:</b> {self.user_data['cargo']}", styles['Normal']))
        elements.append(Paragraph(f"<b>COORDENADOR:</b> {self.user_data['coordenador']}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("Justificativa para a realização de Horas Extras", styles['h2_custom']))
        elements.append(Paragraph(self.user_data['justificativa'], styles['Normal']))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("Atividades a Serem Desenvolvidas", styles['h2_custom']))
        elements.append(Paragraph(self.user_data['atividades'], styles['Normal']))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("Detalhamento", styles['h2_custom']))
        
        table_data = [['DATA', 'LOCAL', 'HORÁRIO', 'Nº DE HORAS']] + [[e['data'], e['local'], e['horario'], e['num_horas']] for e in self.entries]
        table_data.append(['', '', 'Total', total_time_str])
        
        col_widths = [doc.width*0.15, doc.width*0.25, doc.width*0.40, doc.width*0.20]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F0F0F0')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black), ('SPAN', (0, -1), (2, -1)),
            ('ALIGN', (0, -1), (2, -1), 'RIGHT'), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
        ]))
        elements.append(table)
        
        doc.build(elements)
        
        file_stream.seek(0)
        file_for_discord = discord.File(io.BytesIO(file_stream.read()), filename=filename)
        file_stream.seek(0)
        return file_for_discord, file_stream

# --- CLASSE COG PRINCIPAL ---
class RHCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bancohoras", description="Inicia o preenchimento do formulário de banco de horas.")
    async def bancohoras(self, interaction: discord.Interaction):
        await interaction.response.send_modal(OvertimeMainModal())

async def setup(bot: commands.Bot):
    await bot.add_cog(RHCommands(bot))