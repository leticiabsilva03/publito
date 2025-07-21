# services/pdf_service.py
# NOTA DE DEPENDÊNCIA: Para que a reportlab possa processar imagens PNG/JPG,
# a biblioteca 'Pillow' deve estar instalada no ambiente.
# Execute: pip install Pillow
import io
import os
import logging
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta

# Libs para geração de PDF
from reportlab.lib.pagesizes import A4 # Alterado de letter para A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

logger = logging.getLogger(__name__)

def formatar_timedelta(td: timedelta) -> str:
    """Formata a  variação de tempo em uma string 'HH:MM'."""
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
    """
    Função que será chamada em cada página para desenhar o rodapé com imagem.
    """
    canvas.saveState()
    try:
        # Constrói o caminho para a imagem do rodapé
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        rodape_path = os.path.join(project_root, "assets", "rodape.png")

        if os.path.exists(rodape_path):
            # Define a largura da imagem do rodapé
            image_width = 10 * cm 
            # Calcula a posição X para centralizar a imagem
            x_centered = (doc.pagesize[0] - image_width) / 2
            # Define a posição Y para o rodapé (1.5 cm da parte de baixo)
            y = 1.5 * cm
            
            # Desenha a imagem do rodapé centralizada
            canvas.drawImage(rodape_path, x_centered, y,
                             width=image_width, preserveAspectRatio=True, anchor='s',
                             mask='auto')
        else:
            logger.warning(f"Arquivo do rodapé não encontrado no caminho verificado: {rodape_path}")

    except Exception as e:
        logger.error(f"Erro inesperado ao desenhar o rodapé: {e}", exc_info=True)
    canvas.restoreState()

def gerar_pdf_horas_extras(dados_formulario: Dict, resp_aprovacao: Optional[Dict] = None) -> io.BytesIO:
    """
    Gera o arquivo PDF com os dados completos do formulário e retorna o stream.
    Se 'horas_aprovadas' for fornecido, adiciona o bloco de assinatura eletrônica.
    """
    file_stream = io.BytesIO()

    # Extrai os dados do dicionário principal, conforme a estrutura original
    dados_colaborador = dados_formulario.get("dados_colaborador", {})
    detalhes_selecionados = dados_formulario.get("detalhes_selecionados", [])
    tipo_compensacao = dados_formulario.get("tipo_compensacao", "N/A")
    justificativa = dados_formulario.get("justificativa", "")
    atividades = dados_formulario.get("atividades", "")
    
    nome_colaborador = dados_colaborador.get('nome', 'N/A')
    
    # Define o documento com tamanho A4 e margens em centímetros
    doc = SimpleDocTemplate(file_stream, pagesize=A4, 
                            leftMargin=2*cm, rightMargin=2*cm, 
                            topMargin=3*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    elements = []

    # Estilos de parágrafo personalizados
    styles.add(ParagraphStyle(name='CenterH2', alignment=1, parent=styles['h2'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='h2_custom', parent=styles['h2'], fontName='Helvetica-Bold', spaceAfter=6))
    styles.add(ParagraphStyle(name='CenterText', alignment=1, parent=styles['Normal']))


    # Título do Documento
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Solicitação Para Realização de Horas Extras", styles['CenterH2']))
    elements.append(Spacer(1, 0.5*cm))

    # Subtítulo da solicitação
    elements.append(Paragraph("De acordo com a proposta de jornada de trabalho abaixo, solicito, a autorização para realização de horas extras.", styles['CenterText']))
    elements.append(Spacer(1, 0.5*cm))

    # Tabela de Identificação do Colaborador
    p_nome = Paragraph(f"<b>NOME:</b> {nome_colaborador}", styles['Normal'])
    p_depto = Paragraph(f"<b>DEPARTAMENTO:</b> {dados_colaborador.get('nome_departamento', 'N/A')}", styles['Normal'])
    p_cargo = Paragraph(f"<b>CARGO:</b> {dados_colaborador.get('nome_cargo', 'N/A')}", styles['Normal'])
    p_coord = Paragraph(f"<b>RESPONSÁVEL:</b> {dados_colaborador.get('nome_responsavel', 'N/A')}", styles['Normal'])
    
    id_data = [[p_nome, p_depto], [p_cargo, p_coord]]
    id_table = Table(id_data, colWidths=[doc.width/2.0, doc.width/2.0])
    id_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 6)]))
    elements.append(id_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # Justificativa e Atividades
    elements.append(Paragraph("Justificativa para a realização de Horas Extras", styles['h2_custom']))
    elements.append(Paragraph(justificativa.replace('\n', '<br/>'), styles['Normal']))
    elements.append(Spacer(1, 0.4*cm))
    
    elements.append(Paragraph("Atividades Desenvolvidas", styles['h2_custom']))
    elements.append(Paragraph(atividades.replace('\n', '<br/>'), styles['Normal']))
    elements.append(Spacer(1, 0.4*cm))

    # Tabela de Detalhamento dos Dias
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
    elements.append(Spacer(1, 0.8*cm))
    
    # Seção de Assinaturas
    current_date_str = date.today().strftime('%d / %m / %Y')
    
    if resp_aprovacao:
        # Se aprovado, substitui a linha de assinatura do responsável pelos dados da aprovação
        approval_text = f"""
            <b>Aprovado eletronicamente por:</b> {resp_aprovacao['name']} ({resp_aprovacao['email']})<br/>
            <b>Data/Hora da Aprovação:</b> {resp_aprovacao['timestamp']}
        """
        p_approval = Paragraph(approval_text, styles['Normal'])
        signatures_data = [
            [f"DATA: {current_date_str}", ""],
            ["\n\n____________________________", p_approval],
            ["ASSINATURA DO COLABORADOR", "ASSINATURA DO RESPONSÁVEL"]
        ]
    else:
        # Se ainda não foi aprovado, mantém o layout original com espaço para assinatura manual
        signatures_data = [
            [f"DATA: {current_date_str}", f"DATA: {current_date_str}"],
            ["\n\n____________________________", "\n\n____________________________"],
            ["ASSINATURA DO COLABORADOR", "ASSINATURA DO RESPONSÁVEL"]
        ]
    
    signatures_table = Table(signatures_data, colWidths=[doc.width/2.0, doc.width/2.0])
    signatures_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'BOTTOM')]))
    elements.append(signatures_table)

    # Seção de Tipo de Compensação
    pagamento_text = "(X) Pagamento de Horas" if tipo_compensacao == "pagamento" else "( ) Pagamento de Horas"
    compensadas_text = "(X) Horas a serem compensadas" if tipo_compensacao == "compensacao" else "( ) Horas a serem compensadas"
    banco_text = "(X) Banco de Horas" if tipo_compensacao == "banco" else "( ) Banco de Horas"

    compensation_data = [[pagamento_text, compensadas_text], [banco_text, ""]]
    compensation_table = Table(compensation_data, colWidths=[doc.width/2.0, doc.width/2.0])
    compensation_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 20), ('TOPPADDING', (0,0), (-1,-1), 12)]))
    elements.append(compensation_table)

    # Constrói o PDF, aplicando a função de cabeçalho em todas as páginas
    doc.build(elements, onFirstPage=lambda c, d: (_add_cabecalho(c, d), _add_rodape(c, d)),
                      onLaterPages=lambda c, d: (_add_cabecalho(c, d), _add_rodape(c, d)))
    
    file_stream.seek(0)
    return file_stream
