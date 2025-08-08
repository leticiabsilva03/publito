# services/pdf_service.py

import io
import os
import logging
from typing import Dict
from datetime import date, timedelta

# Libs para geração de PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

logger = logging.getLogger(__name__)


def formatar_timedelta(td: timedelta) -> str:
    """Formata um objeto timedelta em uma string legível 'HH:MM'."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"


def _add_cabecalho(canvas, doc):
    """Desenha o cabeçalho com logo."""
    canvas.saveState()
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        logo_path = os.path.join(project_root, "assets", "logo.png")
        if os.path.exists(logo_path):
            image_width = 5 * cm
            x_centered = (doc.pagesize[0] - image_width) / 2
            y_pos = doc.pagesize[1] - 14 * cm
            canvas.drawImage(
                logo_path, x_centered, y_pos,
                width=image_width, preserveAspectRatio=True, anchor='n',
                mask='auto'
            )
        else:
            logger.warning(f"Logo não encontrado: {logo_path}")
    except Exception as e:
        logger.error(f"Erro ao desenhar o logo: {e}", exc_info=True)
    canvas.restoreState()


def _add_rodape(canvas, doc):
    """Desenha o rodapé com imagem."""
    canvas.saveState()
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        rodape_path = os.path.join(project_root, "assets", "rodape.png")
        if os.path.exists(rodape_path):
            image_width = 10 * cm
            x_centered = (doc.pagesize[0] - image_width) / 2
            y_pos = 1.5 * cm
            canvas.drawImage(
                rodape_path, x_centered, y_pos,
                width=image_width, preserveAspectRatio=True, anchor='s',
                mask='auto'
            )
        else:
            logger.warning(f"Rodapé não encontrado: {rodape_path}")
    except Exception as e:
        logger.error(f"Erro ao desenhar o rodapé: {e}", exc_info=True)
    canvas.restoreState()


def gerar_pdf_horas_extras(dados_formulario: Dict) -> io.BytesIO:
    """
    Gera o PDF com dados do formulário e, se houver, a assinatura digital.
    """
    file_stream = io.BytesIO()

    dados_colaborador = dados_formulario.get("dados_colaborador", {})
    detalhes_selecionados = dados_formulario.get("detalhes_selecionados", [])
    justificativa = dados_formulario.get("justificativa", "")
    atividades = dados_formulario.get("atividades", "")
    dados_aprovador = dados_formulario.get("dados_aprovador")  # Pode ser None

    nome_colaborador = dados_colaborador.get('nome', 'N/A')

    doc = SimpleDocTemplate(
        file_stream, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=4*cm, bottomMargin=3*cm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CenterH2', alignment=1, parent=styles['h2'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='h2_custom', parent=styles['h2'], fontName='Helvetica-Bold', spaceAfter=6))
    styles.add(ParagraphStyle(name='CenterText', alignment=1, parent=styles['Normal']))

    elements = []

    # Título
    elements.append(Paragraph("Solicitação Para Realização de Horas Extras", styles['CenterH2']))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(
        "De acordo com a proposta de jornada de trabalho abaixo, solicito a autorização para realização de horas extras.",
        styles['CenterText']
    ))
    elements.append(Spacer(1, 0.5*cm))

    # Dados colaborador
    p_nome = Paragraph(f"<b>NOME:</b> {nome_colaborador}", styles['Normal'])
    p_depto = Paragraph(f"<b>DEPARTAMENTO:</b> {dados_colaborador.get('nome_departamento', 'N/A')}", styles['Normal'])
    p_cargo = Paragraph(f"<b>CARGO:</b> {dados_colaborador.get('nome_cargo', 'N/A')}", styles['Normal'])
    p_coord = Paragraph(f"<b>RESPONSÁVEL:</b> {dados_colaborador.get('nome_responsavel', 'N/A')}", styles['Normal'])

    id_data = [[p_nome, p_depto], [p_cargo, p_coord]]
    id_table = Table(id_data, colWidths=[doc.width/2.0, doc.width/2.0])
    id_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(id_table)
    elements.append(Spacer(1, 0.4*cm))

    # Justificativa
    elements.append(Paragraph("Justificativa para a realização de Horas Extras", styles['h2_custom']))
    elements.append(Paragraph(justificativa.replace('\n', '<br/>'), styles['Normal']))
    elements.append(Spacer(1, 0.4*cm))

    # Atividades
    elements.append(Paragraph("Atividades Desenvolvidas", styles['h2_custom']))
    elements.append(Paragraph(atividades.replace('\n', '<br/>'), styles['Normal']))
    elements.append(Spacer(1, 0.4*cm))

    # Tabela de dias
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
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('SPAN', (0, -1), (1, -1)), ('ALIGN', (0, -1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#EAEAEA'))
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.8*cm))

    # Assinaturas padrão
    current_date_str = date.today().strftime('%d / %m / %Y')
    signatures_data = [
        [f"DATA: {current_date_str}", f"DATA: {current_date_str}"],
        ["\n\n____________________________", "\n\n____________________________"],
        ["ASSINATURA DO COLABORADOR", "ASSINATURA DO RESPONSÁVEL"]
    ]
    signatures_table = Table(signatures_data, colWidths=[doc.width/2.0, doc.width/2.0])
    signatures_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM')
    ]))
    elements.append(signatures_table)

    # Assinatura digital (se houver)
    if dados_aprovador:
        styles.add(ParagraphStyle(name='SignatureStyle', parent=styles['Normal'], fontSize=8, leading=10))
        assinatura_data = [
            [Paragraph(f"<b>Aprovado Digitalmente por:</b> {dados_aprovador['nome']}", styles['SignatureStyle'])],
            [Paragraph(f"<b>ID Discord:</b> {dados_aprovador['id_discord']}", styles['SignatureStyle'])],
            [Paragraph(f"<b>Data/Hora:</b> {dados_aprovador['data_hora']}", styles['SignatureStyle'])]
        ]
        assinatura_table = Table(assinatura_data, colWidths=[7*cm])
        assinatura_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.green),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FFF0'))
        ]))
        elements.append(Spacer(1, 0.4*cm))
        elements.append(assinatura_table)

    # Monta PDF
    doc.build(elements,
              onFirstPage=lambda c, d: (_add_cabecalho(c, d), _add_rodape(c, d)),
              onLaterPages=lambda c, d: (_add_cabecalho(c, d), _add_rodape(c, d)))

    file_stream.seek(0)
    return file_stream
