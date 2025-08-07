# services/pdf_service.py
# NOTA DE DEPENDÊNCIA: Para que a reportlab possa processar imagens PNG/JPG,
# a biblioteca 'Pillow' deve estar instalada no ambiente.
import io
import os
import logging
from typing import Dict, List
from datetime import date, datetime, timedelta

# Libs para geração de PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

# Lib para manipulação de PDFs existentes
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

def formatar_timedelta(td: timedelta) -> str:
    """Formata um objeto timedelta em uma string legível 'HH:MM'."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"

def _add_cabecalho(canvas, doc):
    """
    Função que será chamada em cada página para desenhar o cabeçalho com o logo.
    """
    canvas.saveState()
    try:
        # Constrói o caminho para a pasta 'assets' a partir da raiz do projeto
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        logo_path = os.path.join(project_root, "assets", "logo.png")

        # Verificação explícita se o arquivo existe antes de tentar desenhá-lo
        if os.path.exists(logo_path):
            image_width = 5 * cm # Largura da imagem em centímetros
            # Calcula a posição X para que a imagem fique no centro da página
            x_centered = (doc.pagesize[0] - image_width) / 2
            # Posiciona a imagem a 2cm do topo da página
            y_pos = doc.pagesize[1] - 14 * cm ##28.35 pontos/cm
            
            # Desenha a imagem no topo da página e centralizada
            canvas.drawImage(logo_path, x_centered, y_pos,
                             width=image_width, preserveAspectRatio=True, anchor='n',
                             mask='auto')
            logger.info(f"Logo desenhado com sucesso. y_pos: {y_pos}, x_centered: {x_centered}")
        else:
            # Loga um aviso mais claro se o arquivo não for encontrado no caminho esperado
            logger.warning(f"Arquivo do logo não encontrado no caminho verificado: {logo_path}")

    except Exception as e:
        logger.error(f"Erro inesperado ao desenhar o logo: {e}", exc_info=True)
    canvas.restoreState()

def _add_rodape(canvas, doc):
    """Função de callback para desenhar o rodapé com imagem em cada página."""
    canvas.saveState()
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        rodape_path = os.path.join(project_root, "assets", "rodape.png")

        if os.path.exists(rodape_path):
            image_width = 10 * cm 
            x_centered = (doc.pagesize[0] - image_width) / 2
            y_pos = 1.5 * cm
            
            canvas.drawImage(rodape_path, x_centered, y_pos,
                             width=image_width, preserveAspectRatio=True, anchor='s',
                             mask='auto')
        else:
            logger.warning(f"Arquivo do rodapé não encontrado: {rodape_path}")

    except Exception as e:
        logger.error(f"Erro ao desenhar o rodapé: {e}", exc_info=True)
    canvas.restoreState()

def gerar_pdf_horas_extras(dados_formulario: Dict) -> io.BytesIO:
    """
    Gera o arquivo PDF inicial (sem assinatura) com os dados completos do formulário.
    """
    file_stream = io.BytesIO()

    dados_colaborador = dados_formulario.get("dados_colaborador", {})
    detalhes_selecionados = dados_formulario.get("detalhes_selecionados", [])
    tipo_compensacao = dados_formulario.get("tipo_compensacao", "N/A")
    justificativa = dados_formulario.get("justificativa", "")
    atividades = dados_formulario.get("atividades", "")
    
    nome_colaborador = dados_colaborador.get('nome', 'N/A')
    
    doc = SimpleDocTemplate(file_stream, pagesize=A4, 
                            leftMargin=2*cm, rightMargin=2*cm, 
                            topMargin=4*cm, bottomMargin=3*cm) # Margem superior maior para o cabeçalho
    
    styles = getSampleStyleSheet()
    elements = []

    styles.add(ParagraphStyle(name='CenterH2', alignment=1, parent=styles['h2'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='h2_custom', parent=styles['h2'], fontName='Helvetica-Bold', spaceAfter=6))
    styles.add(ParagraphStyle(name='CenterText', alignment=1, parent=styles['Normal']))

    elements.append(Paragraph("Solicitação Para Realização de Horas Extras", styles['CenterH2']))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph("De acordo com a proposta de jornada de trabalho abaixo, solicito a autorização para realização de horas extras.", styles['CenterText']))
    elements.append(Spacer(1, 0.5*cm))

    p_nome = Paragraph(f"<b>NOME:</b> {nome_colaborador}", styles['Normal'])
    p_depto = Paragraph(f"<b>DEPARTAMENTO:</b> {dados_colaborador.get('nome_departamento', 'N/A')}", styles['Normal'])
    p_cargo = Paragraph(f"<b>CARGO:</b> {dados_colaborador.get('nome_cargo', 'N/A')}", styles['Normal'])
    p_coord = Paragraph(f"<b>RESPONSÁVEL:</b> {dados_colaborador.get('nome_responsavel', 'N/A')}", styles['Normal'])
    
    id_data = [[p_nome, p_depto], [p_cargo, p_coord]]
    id_table = Table(id_data, colWidths=[doc.width/2.0, doc.width/2.0])
    id_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 6)]))
    elements.append(id_table)
    elements.append(Spacer(1, 0.4*cm))
    
    elements.append(Paragraph("Justificativa para a realização de Horas Extras", styles['h2_custom']))
    elements.append(Paragraph(justificativa.replace('\n', '<br/>'), styles['Normal']))
    elements.append(Spacer(1, 0.4*cm))
    
    elements.append(Paragraph("Atividades Desenvolvidas", styles['h2_custom']))
    elements.append(Paragraph(atividades.replace('\n', '<br/>'), styles['Normal']))
    elements.append(Spacer(1, 0.4*cm))

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
        ('SPAN', (0, -1), (1, -1)), ('ALIGN', (0, -1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#EAEAEA'))
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.8*cm))
    
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

    doc.build(elements, onFirstPage=lambda c, d: (_add_cabecalho(c, d), _add_rodape(c, d)),
                      onLaterPages=lambda c, d: (_add_cabecalho(c, d), _add_rodape(c, d)))
    
    file_stream.seek(0)
    return file_stream

def assinar_pdf(pdf_original_bytes: io.BytesIO, dados_aprovador: Dict) -> io.BytesIO:
    """Adiciona um carimbo de assinatura digital a um PDF existente."""
    try:
        carimbo_stream = io.BytesIO()
        c = canvas.Canvas(carimbo_stream, pagesize=A4)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='SignatureStyle', parent=styles['Normal'], fontSize=8, leading=10))
        
        texto_assinatura = [
            Paragraph(f"<b>Aprovado Digitalmente por: </b>{dados_aprovador['nome']}", styles['SignatureStyle']),
            Paragraph(f"<b>ID Discord:</b> {dados_aprovador['id_discord']}", styles['SignatureStyle']),
            Paragraph(f"<b>Data/Hora:</b> {dados_aprovador['data_hora']}", styles['SignatureStyle'])
        ]
        
        tabela_assinatura = Table([[texto_assinatura[0]],[texto_assinatura[1]],[texto_assinatura[2]]], colWidths=[7*cm])
        tabela_assinatura.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.green), ('PADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FFF0')), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        
        # --- COORDENADAS AJUSTADAS ---
        # Margens do documento: 2cm de cada lado. Largura total da página A4: 21cm.
        # Área útil (width) = 21 - 2 - 2 = 17cm.
        # A tabela de assinaturas tem duas colunas de 8.5cm cada.
        # A segunda coluna (do responsável) começa em 2cm (margem) + 8.5cm (coluna 1) = 10.5cm.
        
        largura_carimbo = 7*cm
        largura_coluna_responsavel = (21*cm - 4*cm) / 2 # 8.5cm
        
        # Posição X (horizontal): Início da coluna do responsável + espaço para centralizar o carimbo.
        x_pos = (2*cm + largura_coluna_responsavel) + (largura_coluna_responsavel - largura_carimbo) / 2
        
        # Posição Y (vertical): 4.8 cm da borda inferior. Posição ajustada para ficar
        # logo acima da linha de assinatura, considerando o rodapé e a tabela de compensação.
        y_pos = 4.8 * cm
        
        tabela_assinatura.wrapOn(c, 0, 0)
        tabela_assinatura.drawOn(c, x_pos, y_pos)
        
        c.save()
        carimbo_stream.seek(0)

        pdf_original_reader = PdfReader(pdf_original_bytes)
        pdf_carimbo_reader = PdfReader(carimbo_stream)
        writer = PdfWriter()
        
        primeira_pagina_original = pdf_original_reader.pages[0]
        pagina_carimbo = pdf_carimbo_reader.pages[0]
        
        primeira_pagina_original.merge_page(pagina_carimbo)
        writer.add_page(primeira_pagina_original)
        
        for i in range(1, len(pdf_original_reader.pages)):
            writer.add_page(pdf_original_reader.pages[i])
            
        pdf_assinado_stream = io.BytesIO()
        writer.write(pdf_assinado_stream)
        pdf_assinado_stream.seek(0)
        
        logger.info(f"PDF assinado com sucesso por {dados_aprovador['nome']}.")
        return pdf_assinado_stream
        
    except Exception as e:
        logger.error(f"Falha ao assinar o PDF: {e}", exc_info=True)
        pdf_original_bytes.seek(0)
        return pdf_original_bytes
