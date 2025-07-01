# services/pdf_service.py
import io
import discord
import logging
from typing import Dict, List

# Libs para geração de PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger(__name__)

def _calculate_total_time(entries: List[Dict]) -> str:
    """Função auxiliar para calcular o tempo total a partir das entradas."""
    total_minutes = sum(entry.get('minutes', 0) for entry in entries)
    if total_minutes == 0:
        return "00hs 00min"
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}hs {minutes:02d}min"

def generate_pdf_file(user_data: Dict, entries: List[Dict]) -> tuple[discord.File, io.BytesIO]:
    """Gera o arquivo PDF com os dados do formulário e retorna o objeto de arquivo e o stream."""
    file_stream = io.BytesIO()
    filename = f"Banco_de_Horas_{user_data['nome'].replace(' ', '_')}.pdf"
    total_time_str = _calculate_total_time(entries)

    doc = SimpleDocTemplate(file_stream, pagesize=letter, leftMargin=72, rightMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    elements = []

    # Estilo customizado
    styles.add(ParagraphStyle(name='h2_custom', parent=styles['h2'], spaceAfter=6))

    # Conteúdo do PDF
    elements.append(Paragraph("Solicitação Prévia Para Realização de Horas Extras", styles['h1']))
    elements.append(Spacer(1, 24))

    elements.append(Paragraph("Identificação do Servidor", styles['h2_custom']))
    elements.append(Paragraph(f"<b>NOME:</b> {user_data['nome']}", styles['Normal']))
    elements.append(Paragraph(f"<b>DEPARTAMENTO:</b> {user_data['departamento']}", styles['Normal']))
    elements.append(Paragraph(f"<b>CARGO:</b> {user_data['cargo']}", styles['Normal']))
    elements.append(Paragraph(f"<b>COORDENADOR:</b> {user_data['coordenador']}", styles['Normal']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Justificativa para a realização de Horas Extras", styles['h2_custom']))
    elements.append(Paragraph(user_data['justificativa'], styles['Normal']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Atividades a Serem Desenvolvidas", styles['h2_custom']))
    elements.append(Paragraph(user_data['atividades'], styles['Normal']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Detalhamento", styles['h2_custom']))

    table_data = [['DATA', 'LOCAL', 'HORÁRIO', 'Nº DE HORAS']] + [[e['data'], e['local'], e['horario'], e['num_horas']] for e in entries]
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
    
    # Prepara os arquivos para retorno
    file_stream.seek(0)
    file_for_discord = discord.File(io.BytesIO(file_stream.read()), filename=filename)
    file_stream.seek(0) # Reseta o ponteiro para o stream poder ser usado novamente (para o e-mail)
    
    return file_for_discord, file_stream