import os
import subprocess
import asyncio
import logging
import socket
from datetime import datetime, time, timedelta
from urllib.parse import urlparse, unquote
from pathlib import Path
from app.config import settings, BASE_DIR
from app.services.google_drive_service import google_drive_service

logger = logging.getLogger(__name__)

backup_task = None

def test_db_connection(host: str, port: int) -> bool:
    """Intenta abrir una conexión TCP básica para verificar si el host está activo."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def parse_database_url(db_url: str):
    """Parsea la URL de la base de datos para extraer los parámetros de conexión."""
    if db_url.startswith("mysql+pymysql://"):
        db_url = db_url.replace("mysql+pymysql://", "mysql://")
        
    parsed = urlparse(db_url)
    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    database = parsed.path.lstrip('/')
    
    return host, port, username, password, database

async def run_backup_flow() -> bool:
    """
    Ejecuta el flujo completo de backup:
    1. Genera la copia local con mysqldump.
    2. Sube el archivo a Google Drive.
    3. Elimina el archivo local temporal.
    """
    logger.info("Iniciando proceso de copia de seguridad de la base de datos...")
    
    db_url = settings.DATABASE_URL
    if not db_url:
        logger.error("DATABASE_URL no está configurada en settings.")
        return False
        
    try:
        host, port, username, password, database = parse_database_url(db_url)
    except Exception as e:
        logger.error(f"Error al parsear DATABASE_URL: {e}")
        return False
        
    # Verificar conectividad con el host de BD y aplicar fallback si es necesario
    if host == "bull_db" and not test_db_connection(host, port):
        logger.info("El host 'bull_db' no es accesible (probable ejecución fuera del contenedor Docker). Intentando fallback local...")
        if test_db_connection("127.0.0.1", port):
            host = "127.0.0.1"
            logger.info("Se usará host fallback: 127.0.0.1")
        elif test_db_connection("localhost", port):
            host = "localhost"
            logger.info("Se usará host fallback: localhost")
        else:
            logger.error("No se pudo establecer conexión con bull_db, 127.0.0.1 ni localhost en el puerto 3306.")
            return False

    # Generar el nombre de archivo según lo solicitado: bakup-dd-mm-yy.sql
    filename = datetime.now().strftime("bakup-%d-%m-%y.sql")
    
    # Crear directorio temporal para guardar el dump
    temp_dir = BASE_DIR / "backups_temp"
    os.makedirs(temp_dir, exist_ok=True)
    local_filepath = temp_dir / filename
    
    logger.info(f"Generando dump de la base de datos '{database}' en '{local_filepath}'...")
    
    # Configurar comando mysqldump
    env = os.environ.copy()
    env['MYSQL_PWD'] = password
    cmd = [
        'mysqldump',
        '-h', host,
        '-P', str(port),
        '-u', username,
        database
    ]
    
    try:
        # Ejecutar mysqldump y escribir salida en archivo
        with open(local_filepath, 'w', encoding='utf-8') as f:
            process = subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.PIPE, text=True)
            
        if process.returncode != 0:
            logger.error(f"Error al ejecutar mysqldump (código {process.returncode}): {process.stderr}")
            if os.path.exists(local_filepath):
                os.remove(local_filepath)
            return False
            
        logger.info(f"Dump generado con éxito ({os.path.getsize(local_filepath)} bytes).")
        
        # Subir a Google Drive
        drive_file_id = google_drive_service.upload_file(str(local_filepath), filename)
        
        if drive_file_id:
            logger.info(f"Backup '{filename}' respaldado exitosamente en Google Drive. ID: {drive_file_id}")
            return True
        else:
            logger.error("No se pudo respaldar el archivo en Google Drive.")
            return False
            
    except FileNotFoundError:
        logger.error("La herramienta 'mysqldump' no está instalada o no está disponible en el PATH del sistema.")
        return False
    except Exception as e:
        logger.error(f"Error durante el proceso de backup: {e}")
        return False
    finally:
        # Eliminar archivo temporal local
        if os.path.exists(local_filepath):
            try:
                os.remove(local_filepath)
                logger.info("Archivo de backup local temporal eliminado.")
            except Exception as e:
                logger.error(f"No se pudo eliminar el archivo local temporal: {e}")

async def backup_scheduler_loop():
    """Bucle que ejecuta el backup diariamente a las 10:20 AM."""
    logger.info("Iniciando bucle de programación diaria a las 10:20 AM...")
    while True:
        try:
            now = datetime.now()
            # Calcular tiempo hasta la próxima ejecución a las 10:20 AM (10:20:00)
            target_time = time(10, 20, 0)
            next_run = datetime.combine(now.date(), target_time)
            
            # Si ya pasó la hora hoy, programar para mañana
            if now >= next_run:
                next_run = datetime.combine(now.date() + timedelta(days=1), target_time)
                
            seconds_until_run = (next_run - now).total_seconds()
            
            logger.info(f"Próxima ejecución de backup programada para: {next_run} (en {seconds_until_run:.1f} segundos / {seconds_until_run/3600:.2f} horas)")
            
            # Dormir hasta la hora programada
            await asyncio.sleep(seconds_until_run)
            
            logger.info("Hora programada (10:20 AM) alcanzada. Iniciando ejecución automática de backup...")
            success = await run_backup_flow()
            if success:
                logger.info("Backup automático diario completado con éxito.")
            else:
                logger.error("La ejecución del backup automático diario falló.")
                
        except asyncio.CancelledError:
            logger.info("La tarea del programador de backups fue cancelada.")
            break
        except Exception as e:
            logger.error(f"Excepción en el programador de backups: {e}")
            # Esperar 10 minutos ante un error para evitar bucles infinitos descontrolados
            await asyncio.sleep(600)

async def start_backup_scheduler():
    """Inicia el programador de backups en segundo plano."""
    global backup_task
    if backup_task is None or backup_task.done():
        backup_task = asyncio.create_task(backup_scheduler_loop())
        logger.info("Programador de backups de base de datos activado.")
    else:
        logger.warning("El programador de backups ya está en ejecución.")

def stop_backup_scheduler():
    """Detiene el programador de backups en segundo plano."""
    global backup_task
    if backup_task and not backup_task.done():
        backup_task.cancel()
        logger.info("Programador de backups de base de datos desactivado.")
