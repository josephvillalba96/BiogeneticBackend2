import os
import sys
import time
import socket
from urllib.parse import urlparse

def wait_for_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL no está configurada. Omitiendo espera de la base de datos.")
        return

    try:
        url_to_parse = db_url
        if "://" in db_url:
            scheme, rest = db_url.split("://", 1)
            if "+" in scheme:
                scheme = scheme.split("+")[0]
            url_to_parse = f"{scheme}://{rest}"

        parsed = urlparse(url_to_parse)
        host = parsed.hostname
        port = parsed.port
        
        if not port:
            if parsed.scheme == "mysql":
                port = 3306
            elif parsed.scheme in ("postgres", "postgresql"):
                port = 5432
            else:
                port = 3306  # fallback a puerto MySQL

        if not host:
            print(f"No se pudo analizar el host de DATABASE_URL: {db_url}")
            return

        print(f"Esperando a la base de datos en {host}:{port}...")
        
        timeout = 60
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.create_connection((host, port), timeout=2):
                    print("¡Base de datos detectada y lista para conexiones!")
                    return
            except (socket.timeout, ConnectionRefusedError, OSError):
                time.sleep(2)
                
        print("Tiempo de espera agotado para la base de datos. Continuando de todos modos...")
    except Exception as e:
        print(f"Error al intentar verificar la base de datos: {e}")

if __name__ == "__main__":
    wait_for_db()
