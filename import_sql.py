import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import pymysql
from pymysql.constants import CLIENT

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Intentar cargar la configuración
try:
    from app.config import settings
    DATABASE_URL = settings.DATABASE_URL
    print(f"Configuración cargada desde app.config. DATABASE_URL: {DATABASE_URL}")
except Exception as e:
    print(f"No se pudo cargar la configuración de app.config: {e}")
    # Intento de cargar desde el archivo .env directamente
    try:
        from decouple import config
        DATABASE_URL = config("DATABASE_URL", default=None)
        print(f"DATABASE_URL cargada desde .env directamente: {DATABASE_URL}")
    except Exception as e2:
        DATABASE_URL = None

if not DATABASE_URL:
    print("Error: DATABASE_URL no encontrada en la configuración o en el archivo .env")
    sys.exit(1)

def try_connect(db_url):
    try:
        engine = create_engine(db_url, connect_args={"client_flag": CLIENT.MULTI_STATEMENTS})
        with engine.connect() as conn:
            # Probar una consulta básica
            conn.execute(text("SELECT 1"))
        return engine, db_url
    except OperationalError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)

# Intentar conectar con la URL original
print(f"Intentando conectar a la base de datos...")
engine, err_msg = try_connect(DATABASE_URL)

# Fallback si falla y el host es bull_db (que suele ser el nombre del contenedor Docker)
if not engine and "bull_db" in DATABASE_URL:
    print("No se pudo conectar usando 'bull_db'. Probando fallback local con '127.0.0.1'...")
    fallback_url = DATABASE_URL.replace("@bull_db", "@127.0.0.1")
    engine, err_msg = try_connect(fallback_url)
    if engine:
        print(f"Conexión exitosa a la base de datos local usando fallback: {fallback_url}")
    else:
        print("Probando fallback local con 'localhost'...")
        fallback_url = DATABASE_URL.replace("@bull_db", "@localhost")
        engine, err_msg = try_connect(fallback_url)
        if engine:
            print(f"Conexión exitosa a la base de datos local usando fallback: {fallback_url}")

if not engine:
    print(f"\nError crítico: No se pudo establecer conexión con la base de datos.")
    print(f"Detalles del error: {err_msg}")
    print("\nPor favor, verifica que tu servidor de base de datos MySQL esté activo y accesible.")
    sys.exit(1)

# Obtener la ruta del archivo SQL
sql_file = sys.argv[1] if len(sys.argv) > 1 else "dump-biogenetic-biogenetic-202512171027.sql"
if not os.path.exists(sql_file):
    print(f"Error: El archivo SQL '{sql_file}' no existe en esta ruta.")
    sys.exit(1)

print(f"Leyendo archivo SQL: {sql_file}...")
try:
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
except Exception as e:
    print(f"Error al leer el archivo SQL: {e}")
    sys.exit(1)

print("Inyectando SQL a la base de datos (esto puede tomar unos segundos)...")
try:
    # Usamos begin() para ejecutar en una transacción única
    with engine.begin() as conn:
        conn.execute(text(sql_content))
    print("¡SQL inyectado con éxito!")
except Exception as e:
    print(f"\nError al ejecutar e inyectar el SQL: {e}")
    sys.exit(1)
