import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging
from app.utils.security import get_password_hash

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear el motor de la base de datos
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Crear una clase de sesión para la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_roles(db):
    """Insertar roles básicos para la aplicación"""
    from app.models.user import Role
    
    roles = [
        {"name": "Admin"},
        {"name": "Veterinario"},
        {"name": "Client"}
    ]
    
    for role_data in roles:
        # Verificar si ya existe
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            role = Role(**role_data)
            db.add(role)
            logger.info(f"Agregado rol: {role_data['name']}")
        else:
            logger.info(f"El rol {role_data['name']} ya existe")
    
    db.commit()

def seed_races(db):
    """Insertar razas de prueba"""
    from app.models.bull import Race
    
    races = [
        {"name": "Holstein", "description": "Raza lechera de origen holandés", "code": "HOL"},
        {"name": "Jersey", "description": "Raza lechera de tamaño pequeño", "code": "JER"},
        {"name": "Angus", "description": "Raza de carne de origen escocés", "code": "ANG"},
        {"name": "Brahman", "description": "Raza de carne de origen indio", "code": "BRH"},
        {"name": "Simmental", "description": "Raza de doble propósito de origen suizo", "code": "SIM"}
    ]
    
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

def seed_sexes(db):
    """Insertar sexos de prueba"""
    from app.models.bull import Sex
    
    sexes = [
        {"name": "SX", "code": 1},
        {"name": "CV", "code": 2}
    ]
    
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

def seed_admin_user(db):
    """Crear un usuario administrador por defecto si no existe"""
    from app.models.user import User
    
    admin_data = {
        "number_document": "1234567890",
        "specialty": "Administrador",
        "email": "admin@biogenetic.com",
        "phone": "1234567890",
        "full_name": "Administrador",
        "type_document": "identity_card",
        "pass_hash": get_password_hash("admin123")
    }
    
    # Verificar si ya existe
    existing_user = db.query(User).filter(User.email == admin_data["email"]).first()
    if not existing_user:
        # Crear el usuario
        admin_user = User(**admin_data)
        db.add(admin_user)
        db.commit()
        logger.info(f"Creado usuario administrador: {admin_data['email']}")
    else:
        logger.info(f"El usuario administrador {admin_data['email']} ya existe")

def seed_regular_user(db):
    """Crear un usuario regular por defecto si no existe"""
    from app.models.user import User
    
    user_data = {
        "number_document": "9876543210",
        "specialty": "Veterinario",
        "email": "user@biogenetic.com",
        "phone": "9876543210",
        "full_name": "Usuario Normal",
        "type_document": "identity_card",
        "pass_hash": get_password_hash("user123")
    }
    
    # Verificar si ya existe
    existing_user = db.query(User).filter(User.email == user_data["email"]).first()
    if not existing_user:
        # Crear el usuario
        regular_user = User(**user_data)
        db.add(regular_user)
        db.commit()
        logger.info(f"Creado usuario regular: {user_data['email']}")
    else:
        logger.info(f"El usuario regular {user_data['email']} ya existe")

def seed_client_user(db):
    """Crear un usuario cliente por defecto si no existe"""
    from app.models.user import User
    
    client_data = {
        "number_document": "5678901234",
        "specialty": "Ganadero",
        "email": "client@biogenetic.com",
        "phone": "5678901234",
        "full_name": "Cliente Regular",
        "type_document": "identity_card",
        "pass_hash": get_password_hash("client123")
    }
    
    # Verificar si ya existe
    existing_user = db.query(User).filter(User.email == client_data["email"]).first()
    if not existing_user:
        # Crear el usuario
        client_user = User(**client_data)
        db.add(client_user)
        db.commit()
        logger.info(f"Creado usuario cliente: {client_data['email']}")
    else:
        logger.info(f"El usuario cliente {client_data['email']} ya existe")

def main():
    """Función principal para insertar datos"""
    # Crear conexión a la base de datos
    db = SessionLocal()
    try:
        logger.info("Iniciando inserción de datos de prueba...")
        
        # Primero creamos los roles
        seed_roles(db)
        
        # Luego creamos otras entidades
        seed_races(db)
        seed_sexes(db)
        
        # Finalmente creamos los usuarios
        seed_admin_user(db)
        seed_regular_user(db)
        seed_client_user(db)
        
        logger.info("Inserción completada con éxito")
    except Exception as e:
        logger.error(f"Error al insertar datos: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    main() 