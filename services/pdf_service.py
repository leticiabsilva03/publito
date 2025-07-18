# services/pdf_service.py
import io
import os
import discord
import logging
from typing import Dict, List
from datetime import date

# --- Libs para geração de PDF ---
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)

def _calculate_total_time(entries: List[Dict]) -> str:
    """Função auxiliar para calcular o tempo total a partir das entradas."""
    total_minutes = sum(entry.get('minutes', 0) for entry in entries)
    if total_minutes == 0:
        return "00hs 00min"
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}hs {minutes:02d}min"

def _add_header(canvas, doc):
    """
    Função que será chamada em cada página para desenhar o cabeçalho.
    """
    canvas.saveState()
    # --- MELHORIA APLICADA: Caminho Absoluto e Robusto para o Logo ---
    # Constrói um caminho absoluto para a pasta 'assets', garantindo que o ficheiro
    # seja encontrado independentemente de onde o script é executado.
    try:
        # __file__ é o caminho deste ficheiro (pdf_service.py)
        # os.path.dirname(__file__) é a pasta onde ele está (services/)
        # os.path.join(..., '..') sobe um nível para a raiz do projeto
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        logo_path = os.path.join(project_root, "assets", "logo.png")

        # Desenha a imagem numa posição fixa no topo da página.
        canvas.drawImage(logo_path, doc.leftMargin, 750, 
                         width=2.5*inch, preserveAspectRatio=True, anchor='n')
    except FileNotFoundError:
        logger.warning(f"FICHEIRO DO LOGO NÃO ENCONTRADO EM: {logo_path}. Verifique se a pasta 'assets' e o ficheiro 'logo.png' existem na raiz do projeto.")
    except Exception as e:
        logger.error(f"Erro inesperado ao desenhar o logo: {e}")
    canvas.restoreState()


def generate_pdf_file(user_data: Dict, entries: List[Dict]) -> tuple[discord.File, io.BytesIO]:
    """Gera o arquivo PDF com os dados do formulário e retorna o objeto de arquivo e o stream."""
    file_stream = io.BytesIO()
    filename = f"Banco_de_Horas_{user_data['nome'].replace(' ', '_')}.pdf"
    total_time_str = _calculate_total_time(entries)

    # Definimos as margens do documento
    doc = SimpleDocTemplate(file_stream, pagesize=letter, leftMargin=72, rightMargin=72, topMargin=100, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    elements = []

    # --- Estilos Personalizados ---
    styles.add(ParagraphStyle(name='CenterNormal', alignment=1, parent=styles['Normal']))
    styles.add(ParagraphStyle(name='CenterH2', alignment=1, parent=styles['h2'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='h2_custom', parent=styles['h2'], fontName='Helvetica-Bold', spaceAfter=6))
    styles.add(ParagraphStyle(name='TableHeader', alignment=1, parent=styles['h3'], fontName='Helvetica-Bold'))

    # O logo já não é adicionado aqui, pois será desenhado pela função de cabeçalho
    
    # --- Conteúdo do PDF ---
    elements.append(Paragraph("Solicitação Prévia Para Realização de Horas Extras", styles['CenterH2']))
    elements.append(Spacer(1, 18))
    elements.append(Paragraph("De acordo com a proposta de jornada de trabalho abaixo, solicito a autorização para realização de horas extras.", styles['CenterNormal']))
    elements.append(Spacer(1, 18))

    # --- Tabela de Identificação do Servidor ---
    id_header_data = [[Paragraph("Identificação do Servidor", styles['TableHeader'])]]
    id_header_table = Table(id_header_data, colWidths=[doc.width])
    id_header_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EAEAEA')), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
    elements.append(id_header_table)
    
    p_nome = Paragraph(f"<b>NOME:</b> {user_data['nome']}", styles['Normal'])
    p_depto = Paragraph(f"<b>DEPARTAMENTO:</b> {user_data['departamento']}", styles['Normal'])
    p_cargo = Paragraph(f"<b>CARGO:</b> {user_data['cargo']}", styles['Normal'])
    p_coord = Paragraph(f"<b>COORDENADOR:</b> {user_data['coordenador']}", styles['Normal'])

    id_data = [[p_nome, p_depto], [p_cargo, p_coord]]
    id_table = Table(id_data, colWidths=[doc.width/2.0, doc.width/2.0])
    id_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 6)]))
    elements.append(id_table)
    elements.append(Spacer(1, 12))

    # --- Restante do documento ---
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
    elements.append(Spacer(1, 24))

    # --- Secção de Autorização e Compensação ---
    auth_header_data = [[Paragraph("Solicitação de Autorização", styles['TableHeader'])]]
    auth_header_table = Table(auth_header_data, colWidths=[doc.width])
    # Removemos a moldura da tabela de cabeçalho
    auth_header_table.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0)]))
    elements.append(auth_header_table)
    
    current_date_str = date.today().strftime('%d / %m / %Y')
    signatures_data = [[f"DATA: {current_date_str}", f"DATA: {current_date_str}"],["\n\n____________________________", "\n\n____________________________"],["COORDENADOR", "GERENTE"]]
    signatures_table = Table(signatures_data, colWidths=[doc.width/2.0, doc.width/2.0])
    signatures_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'BOTTOM')]))
    elements.append(signatures_table)
    
    choice = user_data.get("tipo_compensacao")
    pagamento_text = "(x) Pagamento de Horas" if choice == "pagamento" else "( ) Pagamento de Horas"
    compensadas_text = "(x) Horas a serem compensadas" if choice == "compensacao" else "( ) Horas a serem compensadas"
    banco_text = "(x) Banco de Horas" if choice == "banco" else "( ) Banco de Horas"

    compensation_data = [[pagamento_text, compensadas_text], [banco_text, ""]]
    compensation_table = Table(compensation_data, colWidths=[doc.width/2.0, doc.width/2.0])
    compensation_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (0,0), (-1,-1), 20), ('TOPPADDING', (0,0), (-1,-1), 12)]))
    elements.append(compensation_table)

    # Usa a função de cabeçalho ao construir o documento
    doc.build(elements, onFirstPage=_add_header, onLaterPages=_add_header)
    
    file_stream.seek(0)
    file_for_discord = discord.File(io.BytesIO(file_stream.read()), filename=filename)
    file_stream.seek(0)
    return file_for_discord, file_stream
