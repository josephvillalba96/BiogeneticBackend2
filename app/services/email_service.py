from typing import Dict, Any
from fastapi import BackgroundTasks
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import os
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Servicio para envío de emails"""
    
    def __init__(self):
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.from_email = getattr(settings, 'FROM_EMAIL', 'noreply@biogenetic.com')
        self.from_name = getattr(settings, 'FROM_NAME', 'BioGenetic')
        
        # Configurar Jinja2 para templates
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "emails")
        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True
        )
    
    async def send_email(self, to_email: str, subject: str, template_name: str, context: Dict[str, Any]):
        """
        Enviar email usando template HTML
        """
        try:
            # Renderizar template
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(**context)
            
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Crear versión HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Enviar email
            await self._send_smtp_email(msg, to_email)
            
            logger.info(f"Email enviado exitosamente a {to_email}")
            
        except Exception as e:
            logger.error(f"Error al enviar email a {to_email}: {str(e)}")
            raise ValueError(f"Error al enviar email: {str(e)}")
    
    async def _send_smtp_email(self, msg: MIMEMultipart, to_email: str):
        """Enviar email vía SMTP"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
        except Exception as e:
            logger.error(f"Error SMTP: {str(e)}")
            raise e
    
    async def send_simple_email(self, to_email: str, subject: str, message: str):
        """
        Enviar email simple sin template
        """
        try:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            await self._send_smtp_email(msg, to_email)
            
        except Exception as e:
            logger.error(f"Error al enviar email simple: {str(e)}")
            raise e
