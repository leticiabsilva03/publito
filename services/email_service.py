# services/email_service.py
import os
import io
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Dict

logger = logging.getLogger(__name__)

def send_email_with_attachment(user_data: Dict, pdf_stream: io.BytesIO) -> bool:
    """
    Envia o e-mail com o PDF em anexo. Esta é uma função SÍNCRONA.
    """
    try:
        from_email = os.getenv("EMAIL_USER")
        password = os.getenv("EMAIL_PASSWORD")
        to_email = os.getenv("EMAIL_RECIPIENT")
        host = os.getenv("EMAIL_HOST")
        port = int(os.getenv("EMAIL_PORT"))

        if not all([from_email, password, to_email, host, port]):
            logger.error("Credenciais de e-mail não configuradas no arquivo .env.")
            return False

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = f"Solicitação de Banco de Horas - {user_data['nome']}"

        body = (f"Olá,\n\nSegue em anexo o formulário de solicitação de banco de horas preenchido por {user_data['nome']}.\n\nAtenciosamente,\n{user_data['nome']}")
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