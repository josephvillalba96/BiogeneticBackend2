import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conexión directa a MySQL para evitar problemas de importación
DB_USER = 'root'
DB_PASSWORD = 'emi0731'
DB_HOST = 'localhost'
DB_PORT = 3306
DB_NAME = 'biogenetic'

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_races():
    """Inicializar razas"""
    conn = engine.connect()
    races = [
        (1, "Holstein", "Raza lechera de origen holandés", "HOL"),
        (2, "Jersey", "Raza lechera de tamaño pequeño", "JER"),
        (3, "Angus", "Raza de carne de origen escocés", "ANG"),
        (4, "Brahman", "Raza de carne de origen indio", "BRH"),
        (5, "Simmental", "Raza de doble propósito de origen suizo", "SIM")
    ]
    
    for race in races:
        try:
            conn.execute(
                "INSERT INTO races (id, name, description, code) VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE name=VALUES(name), description=VALUES(description)",
                race
            )
            logger.info(f"Raza {race[1]} insertada o actualizada")
        except Exception as e:
            logger.error(f"Error al insertar raza {race[1]}: {e}")
    
    conn.close()

def init_sexes():
    """Inicializar sexos"""
    conn = engine.connect()
    sexes = [
        (1, "Macho", 1),
        (2, "Hembra", 2)
    ]
    
    for sex in sexes:
        try:
            conn.execute(
                "INSERT INTO sexes (id, name, code) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE name=VALUES(name)",
                sex
            )
            logger.info(f"Sexo {sex[1]} insertado o actualizado")
        except Exception as e:
            logger.error(f"Error al insertar sexo {sex[1]}: {e}")
    
    conn.close()

def main():
    try:
        logger.info("Inicializando la base de datos...")
        init_races()
        init_sexes()
        logger.info("Inicialización completada con éxito")
    except Exception as e:
        logger.error(f"Error durante la inicialización: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 