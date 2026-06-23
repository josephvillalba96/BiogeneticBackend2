import os
import logging
from typing import Optional
from pathlib import Path
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from app.config import settings

logger = logging.getLogger(__name__)

class GoogleDriveService:
    def __init__(self):
        self.folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
        self.credentials_file = settings.GOOGLE_DRIVE_CREDENTIALS_FILE
        self._service = None

    def _get_service(self):
        """Inicializa y retorna el cliente de Google Drive."""
        if self._service:
            return self._service

        from app.config import BASE_DIR
        import json

        scopes = ['https://www.googleapis.com/auth/drive.file']
        creds = None
        loaded_from_env = False

        # 1. Intentar cargar credenciales OAuth 2.0 (Usuario)
        # A. Primero revisar si está en las variables de entorno (ideal para despliegue en la nube/Easypanel)
        google_drive_token_data = os.getenv("GOOGLE_DRIVE_TOKEN_DATA")
        if google_drive_token_data:
            try:
                info = json.loads(google_drive_token_data)
                creds = Credentials.from_authorized_user_info(info, scopes=scopes)
                loaded_from_env = True
                logger.info("Credenciales de Google Drive cargadas desde la variable de entorno GOOGLE_DRIVE_TOKEN_DATA.")
            except Exception as e:
                logger.warning(f"No se pudo cargar GOOGLE_DRIVE_TOKEN_DATA desde variables de entorno: {e}")

        # B. Si no está en env, intentar cargar desde el archivo físico google_drive_token.json
        if not creds:
            token_path = BASE_DIR / "credentials" / "google_drive_token.json"
            if token_path.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(token_path), scopes=scopes)
                    logger.info("Credenciales de Google Drive cargadas desde credentials/google_drive_token.json.")
                except Exception as e:
                    logger.warning(f"Error al cargar credentials/google_drive_token.json: {e}")

        # Si tenemos credenciales de usuario, verificar expiración y refrescar
        if creds:
            try:
                if creds.expired and creds.refresh_token:
                    logger.info("Refrescando token de acceso de Google Drive...")
                    creds.refresh(Request())
                    # Si se cargó desde archivo, actualizar el archivo
                    if not loaded_from_env:
                        token_path = BASE_DIR / "credentials" / "google_drive_token.json"
                        with open(token_path, 'w') as token_file:
                            token_file.write(creds.to_json())
                self._service = build('drive', 'v3', credentials=creds)
                return self._service
            except Exception as e:
                logger.error(f"Error al procesar/refrescar credenciales de usuario OAuth 2.0: {e}")
                creds = None  # Forzar fallback a Cuenta de Servicio si falla

        # 2. Caer en Cuenta de Servicio si no hay credenciales de usuario activas
        if not self.credentials_file:
            logger.error("GOOGLE_DRIVE_CREDENTIALS_FILE no está configurado.")
            return None

        creds_path = Path(self.credentials_file)
        if not creds_path.is_absolute():
            creds_path = BASE_DIR / creds_path

        if not creds_path.exists():
            logger.error(f"Archivo de credenciales de Google Drive no encontrado en: {creds_path}")
            return None

        try:
            scopes = ['https://www.googleapis.com/auth/drive.file']
            creds = service_account.Credentials.from_service_account_file(
                str(creds_path), scopes=scopes
            )
            self._service = build('drive', 'v3', credentials=creds)
            logger.info("Servicio de Google Drive inicializado con Cuenta de Servicio.")
            return self._service
        except Exception as e:
            logger.error(f"Error al inicializar el servicio de Google Drive con Cuenta de Servicio: {e}")
            return None

    def upload_file(self, filepath: str, filename: str) -> Optional[str]:
        """
        Sube un archivo local a la carpeta de Google Drive configurada.
        :param filepath: Ruta absoluta del archivo local.
        :param filename: Nombre con el que se guardará el archivo en Google Drive.
        :return: El ID del archivo creado en Drive, o None si falla.
        """
        service = self._get_service()
        if not service:
            logger.error("No se pudo iniciar el servicio de Google Drive. Subida abortada.")
            return None

        if not self.folder_id:
            logger.error("GOOGLE_DRIVE_FOLDER_ID no está configurado. Subida abortada.")
            return None

        if not os.path.exists(filepath):
            logger.error(f"El archivo local no existe: {filepath}")
            return None

        try:
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            # Mime type para SQL
            media = MediaFileUpload(filepath, mimetype='application/sql', resumable=True)
            
            logger.info(f"Subiendo '{filename}' a Google Drive (Folder ID: {self.folder_id})...")
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Archivo subido con éxito. ID en Google Drive: {file_id}")
            return file_id
        except HttpError as e:
            logger.error(f"Error del API de Google Drive al subir archivo: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al subir archivo a Google Drive: {e}")
            return None

google_drive_service = GoogleDriveService()
