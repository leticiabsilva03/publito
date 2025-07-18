# services/email_service.py
import os
import io
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict, List

logger = logging.getLogger(__name__)

def enviar_email_com_anexo(dados_formulario: Dict, pdf_stream: io.BytesIO) -> bool:
    """Envia o e-mail com o PDF em anexo para o RH e para o colaborador."""
    try:
        dados_colaborador = dados_formulario["dados_colaborador"]
        nome_colaborador = dados_colaborador.get('nome', 'Colaborador')

        # --- Carrega as credenciais do ambiente ---
        from_email = os.getenv("EMAIL_USER")
        password = os.getenv("EMAIL_PASSWORD")
        host = os.getenv("EMAIL_HOST")
        port_str = os.getenv("EMAIL_PORT")
        email_rh = os.getenv("EMAIL_RH_RECIPIENT")

        if not all([from_email, password, host, port_str, email_rh]):
            logger.error("Credenciais de e-mail ou e-mail do RH não configuradas corretamente no arquivo .env.")
            return False
        port = int(port_str)

        # --- Monta a lista de destinatários ---
        email_colaborador = dados_colaborador.get("email")
        destinatarios: List[str] = [email_rh]
        if email_colaborador:
            destinatarios.append(email_colaborador)
        else:
            logger.warning(f"O e-mail do colaborador '{nome_colaborador}' não foi encontrado. O e-mail será enviado apenas para o RH.")

        # --- Cria a mensagem ---
        msg = MIMEMultipart()
        msg['From'] = f"Bot Publito <{from_email}>"
        msg['To'] = ", ".join(destinatarios)
        msg['Subject'] = f"Solicitação de Horas Extras - {nome_colaborador}"

        body = (
            f"Olá,\n\n"
            f"Segue em anexo o formulário de solicitação de horas extras preenchido por {nome_colaborador}.\n\n"
            f"Justificativa informada:\n"
            f"-------------------------------------\n"
            f"{dados_formulario['justificativa']}\n"
            f"-------------------------------------\n\n"
            f"Atenciosamente,\n"
            f"Bot de Automação Publito"
        )
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # --- Anexa o PDF ---
        pdf_stream.seek(0)
        attachment = MIMEApplication(pdf_stream.read(), _subtype="pdf")
        attachment.add_header('Content-Disposition', 'attachment', filename=f"Formulario_Horas_Extras_{nome_colaborador.replace(' ', '_')}.pdf")
        msg.attach(attachment)

        # --- Envia o e-mail ---
        # Para porta 465 (SSL)
        with smtplib.SMTP_SSL(host, port, timeout=15) as server:
            server.login(from_email, password)
            server.sendmail(from_email, destinatarios, msg.as_string())
            
        logger.info(f"E-mail de horas extras para '{nome_colaborador}' enviado com sucesso para: {destinatarios}.")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"Erro de SMTP ao enviar e-mail: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Falha inesperada ao enviar e-mail: {e}", exc_info=True)
        return False