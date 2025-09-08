from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear el motor de la base de datos
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Crear una clase de sesión para la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_races():
    """Insertar razas de prueba"""
    from app.models.bull import Race
    
    races = [
        {"name": "Holstein", "description": "Raza lechera de origen holandés", "code": "HOL"},
        {"name": "Jersey", "description": "Raza lechera de tamaño pequeño", "code": "JER"},
        {"name": "Angus", "description": "Raza de carne de origen escocés", "code": "ANG"},
        {"name": "Brahman", "description": "Raza de carne de origen indio", "code": "BRH"},
        {"name": "Simmental", "description": "Raza de doble propósito de origen suizo", "code": "SIM"}
    ]
    
    db = SessionLocal()
    try:
        for race_data in races:
            # Verificar si ya existe
            existing_race = db.query(Race).filter(Race.code == race_data["code"]).first()
            if not existing_race:
                race = Race(**race_data)
                db.add(race)
                logger.info(f"Agregada raza: {race_data['name']}")
            else:
                logger.info(f"La raza {race_data['name']} ya existe")
        
        db.commit()
        logger.info("Razas insertadas correctamente")
    except Exception as e:
        logger.error(f"Error al insertar razas: {e}")
        db.rollback()
    finally:
        db.close()

def seed_sexes():
    """Insertar sexos de prueba"""
    from app.models.bull import Sex
    
    sexes = [
        {"name": "Macho", "code": 1},
        {"name": "Hembra", "code": 2}
    ]
    
    db = SessionLocal()
    try:
        for sex_data in sexes:
            # Verificar si ya existe
            existing_sex = db.query(Sex).filter(Sex.code == sex_data["code"]).first()
            if not existing_sex:
                sex = Sex(**sex_data)
                db.add(sex)
                logger.info(f"Agregado sexo: {sex_data['name']}")
            else:
                logger.info(f"El sexo {sex_data['name']} ya existe")
        
        db.commit()
        logger.info("Sexos insertados correctamente")
    except Exception as e:
        logger.error(f"Error al insertar sexos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_races()
    seed_sexes() 