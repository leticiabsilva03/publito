# services/pdf_service.py
import io
import os
import logging
from typing import Dict, List
from datetime import date, datetime, timedelta

# Vamos precisar importar a função de formatação de tempo
# Supondo que ela esteja em um arquivo de utilidades ou na view
# Para evitar dependência circular, podemos duplicá-la aqui ou movê-la para um utils.py
def formatar_timedelta(td: timedelta) -> str:
    """Formata um timedelta em uma string 'HH:MM'."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)

def _add_cabecalho(canvas, doc):
    """
    Função que será chamada em cada página para desenhar o cabeçalho com o logo.
    """
    canvas.saveState()
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        logo_path = os.path.join(project_root, "assets", "logo.png")

        canvas.drawImage(logo_path, doc.leftMargin, 750,
                         width=2.0*inch, preserveAspectRatio=True, anchor='n')
    except FileNotFoundError:
        logger.warning(f"Arquivo do logo não encontrado em: {logo_path}. O cabeçalho não terá logo.")
    except Exception as e:
        logger.error(f"Erro inesperado ao desenhar o logo: {e}")
    canvas.restoreState()


def gerar_pdf_horas_extras(dados_formulario: Dict) -> io.BytesIO:
    """Gera o arquivo PDF com os dados completos do formulário e retorna o stream."""
    file_stream = io.BytesIO()

    # --- CORREÇÃO APLICADA AQUI ---
    # Extrai os dados usando a chave correta: 'detalhes_selecionados'
    dados_colaborador = dados_formulario["dados_colaborador"]
    detalhes_selecionados = dados_formulario["detalhes_selecionados"] # <-- Chave corrigida
    tipo_compensacao = dados_formulario["tipo_compensacao"]
    justificativa = dados_formulario["justificativa"]
    atividades = dados_formulario["atividades"]
    
    nome_colaborador = dados_colaborador.get('nome', 'N/A')
    
    doc = SimpleDocTemplate(file_stream, pagesize=letter, leftMargin=72, rightMargin=72, topMargin=100, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    elements = []

    # ... (Estilos personalizados) ...
    styles.add(ParagraphStyle(name='CenterH2', alignment=1, parent=styles['h2'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='h2_custom', parent=styles['h2'], fontName='Helvetica-Bold', spaceAfter=6))
    
    # ... (Conteúdo do cabeçalho do PDF) ...
    elements.append(Paragraph("Solicitação Para Realização de Horas Extras", styles['CenterH2']))
    elements.append(Spacer(1, 18))

    # --- Tabela de Identificação do Colaborador ---
    p_nome = Paragraph(f"<b>NOME:</b> {nome_colaborador}", styles['Normal'])
    p_depto = Paragraph(f"<b>DEPARTAMENTO:</b> {dados_colaborador.get('nome_departamento', 'N/A')}", styles['Normal'])
    p_cargo = Paragraph(f"<b>CARGO:</b> {dados_colaborador.get('nome_cargo', 'N/A')}", styles['Normal'])
    p_coord = Paragraph(f"<b>RESPONSÁVEL:</b> {dados_colaborador.get('nome_responsavel', 'N/A')}", styles['Normal'])
    # ... (código para montar a tabela de identificação) ...
    id_data = [[p_nome, p_depto], [p_cargo, p_coord]]
    id_table = Table(id_data, colWidths=[doc.width/2.0, doc.width/2.0])
    id_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 6)]))
    elements.append(id_table)
    elements.append(Spacer(1, 12))
    
    # --- Justificativa e Atividades ---
    elements.append(Paragraph("Justificativa para a realização de Horas Extras", styles['h2_custom']))
    elements.append(Paragraph(justificativa.replace('\n', '<br/>'), styles['Normal']))
    elements.append(Spacer(1, 12))
    
    elements.append(Paragraph("Atividades Desenvolvidas", styles['h2_custom']))
    elements.append(Paragraph(atividades.replace('\n', '<br/>'), styles['Normal']))
    elements.append(Spacer(1, 12))

    # --- Tabela de Detalhamento dos Dias ---
    elements.append(Paragraph("Detalhamento dos Dias Solicitados", styles['h2_custom']))
    
    table_data = [['DATA', 'BATIDAS DO PONTO', 'HORAS EXTRAS']]
    total_geral_extras = timedelta()

    for dia_detalhe in detalhes_selecionados:
        data_obj = dia_detalhe['data']
        horas_extras_td = dia_detalhe['horas_extras_timedelta']
        total_geral_extras += horas_extras_td
        
        table_data.append([
            data_obj.strftime('%d/%m/%Y'),
            dia_detalhe['batidas_str'],
            formatar_timedelta(horas_extras_td)
        ])
    
    table_data.append(['', 'TOTAL', formatar_timedelta(total_geral_extras)])

    col_widths = [doc.width*0.25, doc.width*0.50, doc.width*0.25]
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('SPAN', (0, -1), (1, -1)),
        ('ALIGN', (0, -1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#EAEAEA'))
    ]))
    elements.append(table)
    elements.append(Spacer(1, 24))
    
    # ... (Restante do documento: assinaturas e tipo de compensação) ...
    current_date_str = date.today().strftime('%d / %m / %Y')
    signatures_data = [
        [f"DATA: {current_date_str}", f"DATA: {current_date_str}"],
        ["\n\n____________________________", "\n\n____________________________"],
        ["ASSINATURA DO COLABORADOR", "ASSINATURA DO RESPONSÁVEL"]
    ]
    signatures_table = Table(signatures_data, colWidths=[doc.width/2.0, doc.width/2.0])
    signatures_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'BOTTOM')]))
    elements.append(signatures_table)
    
    pagamento_text = "(X) Pagamento de Horas" if tipo_compensacao == "pagamento" else "( ) Pagamento de Horas"
    compensadas_text = "(X) Horas a serem compensadas" if tipo_compensacao == "compensacao" else "( ) Horas a serem compensadas"
    banco_text = "(X) Banco de Horas" if tipo_compensacao == "banco" else "( ) Banco de Horas"

    compensation_data = [[pagamento_text, compensadas_text], [banco_text, ""]]
    compensation_table = Table(compensation_data, colWidths=[doc.width/2.0, doc.width/2.0])
    compensation_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 20), ('TOPPADDING', (0,0), (-1,-1), 12)]))
    elements.append(compensation_table)

    doc.build(elements, onFirstPage=_add_cabecalho, onLaterPages=_add_cabecalho)
    
    file_stream.seek(0)
    return file_stream