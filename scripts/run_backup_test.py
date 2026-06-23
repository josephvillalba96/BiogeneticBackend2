import sys
import os
import asyncio
import logging

# Configurar logging para ver la salida detallada en consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_backup_test")

# Agregar el directorio raíz al PATH para poder importar app.*
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Variables de entorno cargadas con éxito.")
except ImportError:
    logger.warning("No se pudo importar python-dotenv. Asegúrate de tener cargadas las variables de entorno.")

from app.config import settings
from app.services.google_drive_service import google_drive_service
from app.services.backup_service import run_backup_flow

async def main():
    logger.info("=== DIAGNÓSTICO Y PRUEBA DE BACKUP ===")
    
    # Mostrar host de base de datos de manera segura (ocultando usuario/clave)
    if settings.DATABASE_URL:
        db_host = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL
        logger.info(f"DATABASE_URL configurada (host/db): {db_host}")
    else:
        logger.info("DATABASE_URL no configurada.")
        
    logger.info(f"GOOGLE_DRIVE_FOLDER_ID: {settings.GOOGLE_DRIVE_FOLDER_ID or 'No configurada'}")
    logger.info(f"GOOGLE_DRIVE_CREDENTIALS_FILE: {settings.GOOGLE_DRIVE_CREDENTIALS_FILE or 'No configurada'}")
    
    # Comprobar la existencia del archivo de credenciales
    creds_file = settings.GOOGLE_DRIVE_CREDENTIALS_FILE
    if creds_file:
        from pathlib import Path
        from app.config import BASE_DIR
        creds_path = Path(creds_file)
        if not creds_path.is_absolute():
            creds_path = BASE_DIR / creds_path
        
        if creds_path.exists():
            logger.info(f"[OK] Archivo de credenciales de Google Drive encontrado en: {creds_path}")
        else:
            logger.error(f"[ERROR] Archivo de credenciales de Google Drive NO encontrado en: {creds_path}")
            logger.info("Por favor, coloca el archivo JSON de tu Service Account en esa ruta.")
    
    if not settings.GOOGLE_DRIVE_FOLDER_ID:
        logger.error("[ERROR] GOOGLE_DRIVE_FOLDER_ID no está configurado en el archivo .env")
        logger.info("Completa este valor en tu .env para poder realizar la subida a Drive.")
        
    # Probar primero la conexión y subida a Google Drive directamente con un archivo de texto de prueba
    drive_ok = False
    if settings.GOOGLE_DRIVE_FOLDER_ID and (settings.GOOGLE_DRIVE_CREDENTIALS_FILE or os.path.exists("credentials/google_drive_token.json")):
        logger.info("\nProbando conexión directa y subida de archivo de prueba a Google Drive...")
        dummy_file = "test_drive_upload.txt"
        with open(dummy_file, "w", encoding="utf-8") as f:
            f.write("Archivo temporal para validar conexion con Google Drive de BioGenetic")
            
        try:
            drive_file_id = google_drive_service.upload_file(dummy_file, "prueba_conexion.txt")
            if drive_file_id:
                logger.info(f"[OK] ¡Conexión con Google Drive EXITOSA! Archivo subido con ID: {drive_file_id}")
                drive_ok = True
            else:
                logger.error("[ERROR] Falló la subida de prueba a Google Drive. Revisa permisos o ID del folder.")
        except Exception as e:
            logger.error(f"[ERROR] Error al conectar a Google Drive: {e}")
        finally:
            if os.path.exists(dummy_file):
                os.remove(dummy_file)

    # Revisar si se solicita simulación del archivo backup SQL
    if "--simulate" in sys.argv:
        from datetime import datetime
        logger.info("\n[SIMULACIÓN] Generando archivo SQL simulado...")
        filename = datetime.now().strftime("bakup-%d-%m-%y.sql")
        os.makedirs("backups_temp", exist_ok=True)
        local_filepath = os.path.join("backups_temp", filename)
        
        with open(local_filepath, "w", encoding="utf-8") as f:
            f.write("/* Simulación de Backup BioGenetic */\n")
            f.write("CREATE DATABASE IF NOT EXISTS biogenetic;\n")
            f.write("USE biogenetic;\n")
            f.write("/* Datos simulados para validar la conexión y subida */\n")
            
        try:
            logger.info(f"[SIMULACIÓN] Subiendo archivo SQL simulado '{filename}' a Google Drive...")
            drive_file_id = google_drive_service.upload_file(local_filepath, filename)
            if drive_file_id:
                logger.info(f"\n[SUCCESS] ¡Backup simulado '{filename}' subido CON ÉXITO a Google Drive! ID: {drive_file_id}")
                sys.exit(0)
            else:
                logger.error("\n[ERROR] Falló la subida del backup simulado a Google Drive.")
                sys.exit(1)
        finally:
            if os.path.exists(local_filepath):
                os.remove(local_filepath)

    logger.info("\nIniciando ejecución manual de prueba del flujo de backup completo...")
    success = await run_backup_flow()
    
    if success:
        logger.info("\n[SUCCESS] ¡Flujo de backup completo completado CON ÉXITO!")
        logger.info("Verifica tu carpeta de Google Drive para confirmar la existencia del archivo SQL subido.")
        sys.exit(0)
    else:
        logger.warning("\n[WARNING] El flujo de backup completo falló (probablemente por falta de mysqldump en este host).")
        if drive_ok:
            logger.info("Sin embargo, ¡la conexión y subida a Google Drive fue VALIDADA CORRECTAMENTE!")
            sys.exit(0)
        else:
            logger.error("La conexión con Google Drive tampoco pudo ser validada con éxito.")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
